# -*- coding: utf-8 -*-
"""Validação manual do parser contra o PDF real de julho/2026 e os valores
conhecidos da planilha. Rode com: python tests/test_parser_manual.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import parser as p
import pdf_extract

BASE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(os.path.dirname(BASE), "fixtures")

pages = pdf_extract.extract_pages_from_path(os.path.join(FIXTURES, "relatorio_julho_2026.pdf"))
with open(os.path.join(FIXTURES, "instituicoes_consignacoes.json"), encoding="utf-8") as f:
    inst_by_row = json.load(f)
    instituicoes = {row: nome for row, nome in inst_by_row.items()}
with open(os.path.join(FIXTURES, "ground_truth_julho_2026.json"), encoding="utf-8") as f:
    truth = json.load(f)

erros = []
avisos_total = []


def checa(label, achado_cell, esperado, tol=0.02):
    global erros
    achados_por_cell = {}
    for r in resultados:
        for a in r.achados:
            achados_por_cell[a.cell] = a.valor
    valor = achados_por_cell.get(achado_cell)
    if valor is None:
        erros.append(f"[FALTOU] {label} ({achado_cell}): esperado {esperado}, parser não encontrou nada")
        return
    if abs(valor - esperado) > tol:
        erros.append(f"[DIVERGIU] {label} ({achado_cell}): esperado {esperado}, parser leu {valor}")
    else:
        print(f"[OK] {label} ({achado_cell}) = {valor}")


print("=== 1) RESUMO DE CRÉDITO BANCÁRIO ===")
r1 = p.parse_credito_bancario(pages)
print(f"achados={len(r1.achados)} avisos={len(r1.avisos)}")
for w in r1.avisos:
    print("  AVISO:", w)

print("\n=== 2) RESUMO DE CONSIGNAÇÕES ===")
r2 = p.parse_consignacoes(pages, instituicoes)
print(f"achados={len(r2.achados)} avisos={len(r2.avisos)}")
for w in r2.avisos:
    print("  AVISO:", w)

print("\n=== 3) ENCARGOS SOCIAIS - GERAL ===")
r3 = p.parse_encargos(pages)
print(f"achados={len(r3.achados)} avisos={len(r3.avisos)}")
for w in r3.avisos:
    print("  AVISO:", w)

resultados = [r1, r2, r3]

print("\n=== CONFERÊNCIA CONTRA A PLANILHA REAL ===")
checa("Líquido Contratos", "H15", truth["liquido"]["H15"])
checa("Líquido RPPS", "H30", truth["liquido"]["H30"])
checa("Líquido RGPS", "H44", truth["liquido"]["H44"])
checa("Líquido Militar", "H58", truth["liquido"]["H58"])
checa("Fundo Financeiro", "F68", truth["liquido"]["F68"], tol=0.05)
checa("Fundo Previdenciário", "F69", truth["liquido"]["F69"])
checa("INSS", "F70", truth["liquido"]["F70"])
checa("Plansaude", "F71", truth["liquido"]["F71"])
checa("Consignações resumo Contratos", "D3", truth["consignacoes_resumo"]["D3"])
checa("Consignações resumo RPPS", "D4", truth["consignacoes_resumo"]["D4"])
checa("Consignações resumo RGPS", "D5", truth["consignacoes_resumo"]["D5"])
checa("Consignações resumo Militar", "D6", truth["consignacoes_resumo"]["D6"])
# D7 é fórmula (=SUM(D3:D6)) na planilha real, não é um valor de entrada -
# não deve ser escrito diretamente. Confirma só que a soma bate:
soma_d3_d6 = sum(truth["consignacoes_resumo"][c] for c in ["D3", "D4", "D5", "D6"])
if abs(soma_d3_d6 - truth["consignacoes_resumo"]["D7"]) > 0.02:
    erros.append("D7 não bate com soma de D3:D6 nos dados de referência (verifique o fixture)")
else:
    print(f"[OK] D7 (fórmula =SUM(D3:D6)) confere: {soma_d3_d6}")

# amostras de consignacoes detalhadas: nome esperado na linha X, coluna F (RPPS) e G (RGPS)
# valores em 0/None sao esperados quando a instituicao simplesmente nao
# aparece naquele regime no relatorio (equivale a zero, nao e' erro).
achados_cons = {a.cell: (a.valor, a.confianca) for a in r2.achados}
for key, (nome, f_esperado, g_esperado) in truth["consignacoes_detalhe_amostra"].items():
    row = key.split("_")[0][1:]
    f_val, f_conf = achados_cons.get(f"F{row}", (None, None))
    g_val, g_conf = achados_cons.get(f"G{row}", (None, None))
    ok_f = (f_val is None and f_esperado == 0) or (f_val is not None and abs(f_val - f_esperado) < 0.02)
    ok_g = (g_val is None and g_esperado == 0) or (g_val is not None and abs(g_val - g_esperado) < 0.02)
    status = "OK" if (ok_f and ok_g) else "DIVERGIU"
    print(f"[{status}] {nome}: F{row}={f_val}(conf={f_conf}) esperado={f_esperado} | "
          f"G{row}={g_val}(conf={g_conf}) esperado={g_esperado}")
    if status == "DIVERGIU":
        erros.append(f"[DIVERGIU] {nome} linha {row}")

print("\n=== RESUMO ===")
print(f"Total de achados: {sum(len(r.achados) for r in resultados)}")
print(f"Total de avisos: {sum(len(r.avisos) for r in resultados)}")
print(f"Total de erros de conferência: {len(erros)}")
for e in erros:
    print(" ", e)

sys.exit(1 if erros else 0)
