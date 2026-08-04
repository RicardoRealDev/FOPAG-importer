# -*- coding: utf-8 -*-
"""
Testes de regressão do parser contra o relatório real de julho/2026.

IMPORTANTE — PRIVACIDADE: esse PDF contém dados reais de servidores
públicos (inclusive nomes individuais na seção "Servidores Afastados") e
por isso NÃO é commitado no repositório (veja .gitignore). Para rodar
este arquivo, copie o PDF e os dois JSONs de referência para
backend/fixtures/ na sua máquina local - eles nunca vão para o GitHub.

No GitHub Actions (repositório público), este arquivo inteiro é pulado
automaticamente. A validação "de verdade" nesse ambiente é reenviar o PDF
pela própria tela do site, depois do deploy, e conferir visualmente os
valores encontrados antes de clicar em "Gravar na planilha".

Rode com: pytest tests/test_parser_com_pdf_real.py
"""
import json
import os

import pytest

import parser as p
import pdf_extract

BASE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(os.path.dirname(BASE), "fixtures")
PDF_PATH = os.path.join(FIXTURES, "relatorio_julho_2026.pdf")

pytestmark = pytest.mark.skipif(
    not os.path.exists(PDF_PATH),
    reason="PDF real não está presente nesta máquina (não é commitado por privacidade - veja o docstring deste arquivo).",
)


@pytest.fixture(scope="module")
def pages():
    return pdf_extract.extract_pages_from_path(PDF_PATH)


@pytest.fixture(scope="module")
def instituicoes():
    with open(os.path.join(FIXTURES, "instituicoes_consignacoes.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def truth():
    with open(os.path.join(FIXTURES, "ground_truth_julho_2026.json"), encoding="utf-8") as f:
        return json.load(f)


def _achados_por_cell(resultado):
    return {a.cell: a.valor for a in resultado.achados}


def test_credito_bancario_totais_por_regime(pages, truth):
    r = p.parse_credito_bancario(pages)
    achados = _achados_por_cell(r)
    assert not r.avisos
    assert achados["H15"] == pytest.approx(truth["liquido"]["H15"], abs=0.02)
    assert achados["H30"] == pytest.approx(truth["liquido"]["H30"], abs=0.02)
    assert achados["H44"] == pytest.approx(truth["liquido"]["H44"], abs=0.02)
    assert achados["H58"] == pytest.approx(truth["liquido"]["H58"], abs=0.02)
    assert achados["D3"] == pytest.approx(truth["consignacoes_resumo"]["D3"], abs=0.02)
    assert achados["D4"] == pytest.approx(truth["consignacoes_resumo"]["D4"], abs=0.02)
    assert achados["D5"] == pytest.approx(truth["consignacoes_resumo"]["D5"], abs=0.02)
    assert achados["D6"] == pytest.approx(truth["consignacoes_resumo"]["D6"], abs=0.02)


def test_encargos_sociais_por_fundo(pages, truth):
    r = p.parse_encargos(pages)
    achados = _achados_por_cell(r)
    assert not r.avisos
    assert achados["F68"] == pytest.approx(truth["liquido"]["F68"], abs=0.05)
    assert achados["F69"] == pytest.approx(truth["liquido"]["F69"], abs=0.02)
    assert achados["F70"] == pytest.approx(truth["liquido"]["F70"], abs=0.02)
    assert achados["F71"] == pytest.approx(truth["liquido"]["F71"], abs=0.02)


def test_consignacoes_amostra(pages, instituicoes, truth):
    r = p.parse_consignacoes(pages, instituicoes)
    assert not r.avisos
    achados = {a.cell: (a.valor, a.confianca) for a in r.achados}
    for key, (_nome, f_esperado, g_esperado) in truth["consignacoes_detalhe_amostra"].items():
        row = key.split("_")[0][1:]
        f_val, _ = achados.get(f"F{row}", (None, None))
        g_val, _ = achados.get(f"G{row}", (None, None))
        if f_esperado == 0:
            assert f_val is None or f_val == pytest.approx(0, abs=0.02)
        else:
            assert f_val == pytest.approx(f_esperado, abs=0.02)
        if g_esperado == 0:
            assert g_val is None or g_val == pytest.approx(0, abs=0.02)
        else:
            assert g_val == pytest.approx(g_esperado, abs=0.02)
