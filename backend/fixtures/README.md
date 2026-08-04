# Fixtures locais (não commitadas)

Esta pasta guarda os arquivos de teste do parser. Três deles contêm dados
reais de servidores públicos e **nunca são commitados** (veja `.gitignore`
na raiz do projeto):

- `relatorio_julho_2026.pdf` — o relatório do Ergon
- `ground_truth_julho_2026.json` — valores reais da planilha, pra conferir se o parser leu certo
- `instituicoes_consignacoes.json` — lista de bancos/instituições da aba Consignações

## Como recriá-los na sua máquina

Você só precisa fazer isso se for rodar `pytest tests/test_parser_com_pdf_real.py`
localmente (opcional — o `pytest tests/` normal já roda os testes que não
precisam disso, e pula esses automaticamente se os arquivos não existirem).

**1. Copie o PDF real** para `backend/fixtures/relatorio_julho_2026.pdf`.

**2. Gere os dois JSONs** a partir da sua Planilha FOPAG (rode isso uma vez,
com `openpyxl` instalado — `pip install openpyxl`):

```python
import openpyxl, json

wb = openpyxl.load_workbook("caminho/para/Planilha FOPAG.xlsx", data_only=True)
con = wb["CONSIGNAÇÕES FOLHA 1"]
liq = wb["LÍQUIDO FOLHA -1"]

# instituicoes_consignacoes.json
nomes = {}
for r in range(14, 98):
    v = con[f"E{r}"].value
    if isinstance(v, str) and v.strip():
        nomes[str(r)] = v.strip()
json.dump(nomes, open("backend/fixtures/instituicoes_consignacoes.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# ground_truth_<mes>.json - copie os valores que já existem na planilha
ground_truth = {
    "liquido": {c: liq[c].value for c in ["H15", "H30", "H44", "H58", "F68", "F69", "F70", "F71"]},
    "consignacoes_resumo": {c: con[c].value for c in ["D3", "D4", "D5", "D6", "D7"]},
    "consignacoes_detalhe_amostra": {
        # escolha 2-3 instituições conhecidas pra conferir, formato: "E<linha>_F_G"
        "E27_F_G": [con["E27"].value, con["F27"].value, con["G27"].value],
    },
}
json.dump(ground_truth, open("backend/fixtures/ground_truth_julho_2026.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
```

**3. Rode os testes:**

```bash
cd backend
pytest tests/test_parser_com_pdf_real.py -v
```

## Verificação sem fixtures (produção / GitHub Actions)

Como o PDF real nunca fica no repositório, a validação "de verdade" depois
do deploy é: abra o site publicado, arraste o PDF do mês, e confira os
valores na tela de revisão *antes* de clicar em "Gravar na planilha".
