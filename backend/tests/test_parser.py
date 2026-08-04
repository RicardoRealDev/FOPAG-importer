# -*- coding: utf-8 -*-
"""
Testes unitários do parser que NÃO dependem de nenhum dado real - por isso
sempre rodam, inclusive no GitHub Actions do repositório público. Os
testes que usam o PDF real de julho/2026 (com dados de servidores
públicos) ficam em test_parser_com_pdf_real.py e são pulados quando esse
arquivo não está presente (veja o motivo lá).
"""
import parser as p


def test_normalize_ignora_acento_e_caixa():
    assert p.normalize("Plansaúde (Comparticipação)") == p.normalize("PLANSAUDE COMPARTICIPACAO")


def test_find_best_match_abaixo_do_limiar_retorna_none():
    candidatos = {"1": "SISTEMA TOTALMENTE DIFERENTE"}
    cell, score = p.find_best_match("ZZZZZZZZZ", candidatos)
    assert cell is None


def test_find_best_match_acima_do_limiar_retorna_melhor():
    candidatos = {"1": "PLANSAÚDE COMPARTICIPAÇÃO", "2": "PLANSAÚDE MENSALIDADE"}
    cell, score = p.find_best_match("PLANSAUDE (Comparticipacao)", candidatos)
    assert cell == "1"
    assert score > 0.8


def test_to_float_formato_brasileiro():
    assert p._to_float("1.234,56") == 1234.56
    assert p._to_float("0,00") == 0.0
