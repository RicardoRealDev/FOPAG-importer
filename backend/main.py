"""
Ponto de entrada HTTP (Google Cloud Functions / Cloud Run).

Endpoint único: recebe um PDF, devolve o que encontrou (modo "revisar")
ou gera um .xlsx preenchido pra download (qualquer outro modo). Fino de
propósito: toda a lógica de verdade mora em parser.py e xlsx_writer.py -
este arquivo só faz a "cola" HTTP (parse do request, CORS, resposta).
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
import xlsx_writer

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
    r4 = p.parse_irrf(pages)
    mes_ano_label = p.extrair_mes_ano(pages)

    achados = r1.achados + r2.achados + r3.achados + r4.achados
    avisos = r1.avisos + r2.avisos + r3.avisos + r4.avisos
    return {"achados": achados, "avisos": avisos, "mes_ano_label": mes_ano_label}


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

    modo = request.form.get("modo", "revisar")  # "revisar" | qualquer outro = gerar arquivo

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

    # modo == "gerar_arquivo": gera um .xlsx preenchido a partir do modelo,
    # em vez de escrever ao vivo via Google Sheets API - mais simples, sem
    # CORS/timeout de escrita.
    xlsx_bytes, total_aplicado, nao_encontrados = xlsx_writer.gerar_xlsx(
        achados, mes_ano_label=resultado.get("mes_ano_label")
    )
    baixa_confianca = [a for a in achados if a.confianca == "baixa"]

    headers = _cors_headers()
    headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    headers["Content-Disposition"] = 'attachment; filename="Planilha FOPAG preenchida.xlsx"'
    headers["X-Total-Aplicado"] = str(total_aplicado)
    headers["X-Nao-Encontrados"] = str(len(nao_encontrados))
    headers["X-Baixa-Confianca"] = str(len(baixa_confianca))
    headers["Access-Control-Expose-Headers"] = "X-Total-Aplicado, X-Nao-Encontrados, X-Baixa-Confianca"
    return xlsx_bytes, 200, headers