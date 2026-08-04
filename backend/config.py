"""
Configuracao central de mapeamento: onde cada dado extraido do PDF do Ergon
deve ser escrito na Planilha FOPAG.

Isso e' a "fonte unica de verdade" do projeto. Se o layout da planilha mudar,
ou se um novo relatorio/regime for adicionado, a mudanca entra aqui - o
parser e o writer nao devem ter numeros de linha/coluna soltos no meio do
codigo.
"""

SHEET_LIQUIDO = "LÍQUIDO FOLHA -1"
SHEET_CONSIGNACOES = "CONSIGNAÇÕES FOLHA 1"

# ---------------------------------------------------------------------------
# 1) RESUMO DE CRÉDITO BANCÁRIO (GTO0003R) -> totais liquidos por regime
# ---------------------------------------------------------------------------
# Cada regime aparece em uma pagina do PDF com o titulo abaixo. O relatorio
# da 4 numeros: Exercicio Atual, Exercicio Anterior, Indenizacoes, Total.
# Mapeamos para a celula de TOTAL do bloco na Liquido Folha (H15/H30/H44/H58)
# e para o resumo no topo da aba Consignacoes (D3:D6).
CREDITO_BANCARIO_REGIMES = {
    "CONTRATO TEMPORARIO - REGIME GERAL DE PREVIDÊNCIA SOCIAL": {
        "liquido_total_cell": "H15",
        "consignacoes_resumo_cell": "D3",
    },
    "ATIVOS - REGIME PRÓPRIO DE PREVIDÊNCIA SOCIAL": {
        "liquido_total_cell": "H30",
        "consignacoes_resumo_cell": "D4",
    },
    "ATIVOS - REGIME GERAL DE PREVIDÊNCIA SOCIAL": {
        "liquido_total_cell": "H44",
        "consignacoes_resumo_cell": "D5",
    },
    "MILITARES - REGIME DE PREVIDENCIA MILITARES": {
        "liquido_total_cell": "H58",
        "consignacoes_resumo_cell": "D6",
    },
}
CREDITO_BANCARIO_GERAL_TITLE = "RESUMO DE CRÉDITO BANCÁRIO GERAL"
CONSIGNACOES_TOTAL_GERAL_CELL = "D7"  # usado so' para conferencia/alerta

# ---------------------------------------------------------------------------
# 2) RESUMO DE CONSIGNAÇÕES (GTO0004R) -> detalhe por banco/instituicao
# ---------------------------------------------------------------------------
# Cada pagina lista consignacoes de um regime. A coluna de destino na aba
# Consignacoes depende do regime da pagina.
CONSIGNACOES_REGIME_TO_COLUMN = {
    "REGIME PRÓPRIO DE PREVIDÊNCIA SOCIAL": "F",   # Civil RPPS
    "REGIME GERAL DE PREVIDÊNCIA SOCIAL": "G",     # Civil RGPS (ativos)
    "CONTRATO TEMPORARIO": "G",                     # Contrato tambem cai em RGPS
    "MILITARES": "H",                               # Militar
}
CONSIGNACOES_LABEL_COL = "E"      # onde esta' o nome da instituicao na planilha
CONSIGNACOES_ROW_START = 14
CONSIGNACOES_ROW_END = 97
# titulos de pagina que devem ser ignorados (agregado "GERAL", ja' e' soma das outras)
CONSIGNACOES_SKIP_TITLES = ["GERAL"]

# ---------------------------------------------------------------------------
# 3) ENCARGOS SOCIAIS - GERAL (GTO0002R) -> encargos sociais consolidados
# ---------------------------------------------------------------------------
# So' nos interessa a secao "GERAL" (soma de todos os regimes), coluna
# "Contribuicao do Estado", linha "Total" de cada fundo.
ENCARGOS_FUNDO_TO_CELL = {
    "FUNDO DE PREVIDENCIA (FUNDO FINANCEIRO)": "F68",
    "FUNDO DE PREVIDENCIA (FUNDO PREVIDENCIÁRIO)": "F69",
    "I.N.S.S.": "F70",
    "PLANSAUDE": "F71",
}
ENCARGOS_SECTION_TITLE = "ENCARGOS SOCIAIS - GERAL"

# ---------------------------------------------------------------------------
# Registro de origem por celula (auditoria: de onde veio cada numero)
# ---------------------------------------------------------------------------
SOURCE_LABEL = "Importado automaticamente do relatório Ergon"
