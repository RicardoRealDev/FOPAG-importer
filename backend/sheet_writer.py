"""
Escreve os `Achado`s do parser na Planilha FOPAG via Google Sheets API.

Este módulo não sabe nada sobre PDF - só recebe uma lista de Achado (sheet,
cell, valor) e aplica. Isso permite testar o parser sem credencial nenhuma
(veja tests/test_parser_manual.py) e trocar a forma de escrita (ex: gravar
em lote, ou simular em modo "dry run") sem tocar no parser.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build

from parser import Achado

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@dataclass
class ItemAplicado:
    sheet: str
    cell: str
    valor_novo: float
    valor_anterior: float | None
    origem: str
    confianca: str


def _get_service():
    """Usa a identidade da própria Cloud Function (a conta de serviço com
    que ela foi implantada via --service-account) - não precisa de arquivo
    de chave. Isso é o que a Google chama de "Application Default
    Credentials": em produção, pega a identidade do ambiente automaticamente.

    Só usa GOOGLE_SERVICE_ACCOUNT_JSON (arquivo de chave) se essa variável
    estiver definida - útil para rodar/testar fora do Google Cloud, ex: no
    seu computador."""
    creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_path:
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    else:
        creds, _ = google.auth.default(scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def ler_valores_atuais(spreadsheet_id: str, achados: list[Achado]) -> dict[str, float | None]:
    """Lê o valor atual de cada célula alvo, para poder mostrar o "antes/depois"."""
    service = _get_service()
    ranges = [f"'{a.sheet}'!{a.cell}" for a in achados]
    if not ranges:
        return {}
    resp = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id, ranges=ranges
    ).execute()
    atuais = {}
    for a, vr in zip(achados, resp.get("valueRanges", [])):
        values = vr.get("values")
        atuais[f"{a.sheet}!{a.cell}"] = values[0][0] if values and values[0] else None
    return atuais


def aplicar(spreadsheet_id: str, achados: list[Achado], apenas_alta_e_media: bool = True) -> list[ItemAplicado]:
    """Escreve os achados na planilha. Acha de baixa confiança ficam de fora
    por padrão - devem ser aplicados manualmente após revisão."""
    service = _get_service()
    aplicaveis = [a for a in achados if (not apenas_alta_e_media or a.confianca in ("alta", "media"))]
    if not aplicaveis:
        return []

    atuais = ler_valores_atuais(spreadsheet_id, aplicaveis)

    data = [
        {"range": f"'{a.sheet}'!{a.cell}", "values": [[a.valor]]}
        for a in aplicaveis
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": data},
    ).execute()

    aplicados = []
    for a in aplicaveis:
        anterior = atuais.get(f"{a.sheet}!{a.cell}")
        aplicados.append(ItemAplicado(
            sheet=a.sheet,
            cell=a.cell,
            valor_novo=a.valor,
            valor_anterior=float(str(anterior).replace(".", "").replace(",", ".")) if anterior not in (None, "") else None,
            origem=a.origem,
            confianca=a.confianca,
        ))
    return aplicados