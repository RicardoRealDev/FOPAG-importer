"""
Ponto de entrada HTTP (Google Cloud Functions / Cloud Run).

Endpoint único: recebe um PDF, devolve o que encontrou (modo "revisar")
ou já grava na planilha (modo "aplicar"). Fino de propósito: toda a lógica
de verdade mora em parser.py e sheet_writer.py - este arquivo só faz a
"cola" HTTP (parse do request, CORS, resposta JSON).
"""
from __future__ import annotations

import json
import os

import functions_framework
from flask import Request, jsonify

import config
import parser as p
import pdf_extract
import sheet_writer

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def _ler_instituicoes(spreadsheet_id: str) -> dict[str, str]:
    """Lê ao vivo os nomes de instituição já cadastrados na aba Consignações
    (E14:E97), para o parser casar contra o que existe HOJE na planilha -
    não uma cópia estática que pode ficar desatualizada."""
    service = sheet_writer._get_service()
    resp = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{config.SHEET_CONSIGNACOES}'!E{config.CONSIGNACOES_ROW_START}:E{config.CONSIGNACOES_ROW_END}",
    ).execute()
    valores = resp.get("values", [])
    out = {}
    for i, row in enumerate(valores):
        if row and row[0].strip():
            out[str(config.CONSIGNACOES_ROW_START + i)] = row[0].strip()
    return out


def _processar(pdf_bytes: bytes, spreadsheet_id: str) -> dict:
    pages = pdf_extract.extract_pages(pdf_bytes)
    instituicoes = _ler_instituicoes(spreadsheet_id)

    r1 = p.parse_credito_bancario(pages)
    r2 = p.parse_consignacoes(pages, instituicoes)
    r3 = p.parse_encargos(pages)

    achados = r1.achados + r2.achados + r3.achados
    avisos = r1.avisos + r2.avisos + r3.avisos
    return {"achados": achados, "avisos": avisos}


@functions_framework.http
def importar_pdf(request: Request):
    if request.method == "OPTIONS":
        return ("", 204, _cors_headers())

    if request.method != "POST":
        return jsonify({"erro": "Use POST"}), 405, _cors_headers()

    if "pdf" not in request.files:
        return jsonify({"erro": "Envie o arquivo no campo 'pdf' (multipart/form-data)."}), 400, _cors_headers()

    spreadsheet_id = request.form.get("spreadsheet_id") or os.environ.get("DEFAULT_SPREADSHEET_ID")
    if not spreadsheet_id:
        return jsonify({"erro": "Informe spreadsheet_id."}), 400, _cors_headers()

    modo = request.form.get("modo", "revisar")  # "revisar" | "aplicar"

    pdf_bytes = request.files["pdf"].read()

    try:
        resultado = _processar(pdf_bytes, spreadsheet_id)
    except Exception as e:  # noqa: BLE001 - resposta de erro amigável pro usuario final
        return jsonify({"erro": f"Não consegui ler o PDF: {e}"}), 422, _cors_headers()

    achados = resultado["achados"]

    if modo == "revisar":
        return jsonify({
            "modo": "revisar",
            "total_encontrado": len(achados),
            "itens": [
                {"aba": a.sheet, "celula": a.cell, "valor": a.valor, "origem": a.origem, "confianca": a.confianca}
                for a in achados
            ],
            "avisos": resultado["avisos"],
        }), 200, _cors_headers()

    aplicados = sheet_writer.aplicar(spreadsheet_id, achados)
    baixa_confianca = [a for a in achados if a.confianca == "baixa"]

    return jsonify({
        "modo": "aplicar",
        "total_aplicado": len(aplicados),
        "itens": [
            {
                "aba": item.sheet, "celula": item.cell,
                "valor_novo": item.valor_novo, "valor_anterior": item.valor_anterior,
                "origem": item.origem, "confianca": item.confianca,
            }
            for item in aplicados
        ],
        "nao_aplicados_baixa_confianca": [
            {"aba": a.sheet, "celula": a.cell, "valor": a.valor, "origem": a.origem}
            for a in baixa_confianca
        ],
        "avisos": resultado["avisos"],
    }), 200, _cors_headers()
