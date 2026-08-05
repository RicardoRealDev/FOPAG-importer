"""
Gera um arquivo .xlsx pronto pra download, a partir do modelo da Planilha
FOPAG (backend/templates/planilha_fopag_template.xlsx) com os valores do
PDF já escritos nas células certas.

Isso substitui a escrita ao vivo via Google Sheets API: em vez de o
usuário "conectar" a planilha, ele baixa um arquivo já preenchido e
substitui manualmente no Google Drive quando quiser (File > Import >
Replace spreadsheet). Mais simples, sem autenticação, sem CORS, sem
depender da Cloud Function ficar "no ar" pra sempre.
"""
from __future__ import annotations

import io
import os

import openpyxl

from parser import Achado

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "planilha_fopag_template.xlsx")


def gerar_xlsx(achados: list[Achado], apenas_alta_e_media: bool = True) -> bytes:
    """Abre o modelo, escreve cada Achado na célula certa e devolve os
    bytes do arquivo resultante. Fórmulas e formatação do modelo são
    preservadas - só as células de valor são sobrescritas."""
    wb = openpyxl.load_workbook(TEMPLATE_PATH, data_only=False)

    aplicaveis = [a for a in achados if (not apenas_alta_e_media or a.confianca in ("alta", "media"))]

    nao_encontrados = []
    for a in aplicaveis:
        if a.sheet not in wb.sheetnames:
            nao_encontrados.append(f"{a.sheet}!{a.cell} (aba não existe no modelo)")
            continue
        ws = wb[a.sheet]
        ws[a.cell] = a.valor

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read(), len(aplicaveis), nao_encontrados