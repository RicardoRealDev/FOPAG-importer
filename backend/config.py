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
# 4) RENDIMENTOS E DESCONTOS (GTO0001R) -> IRRF retido por regime
# ---------------------------------------------------------------------------
# Cada regime tem uma pagina "DESCONTOS" com uma linha "3014 - IRRF". O
# valor na coluna "Total" dessa linha e' o IRRF retido daquele regime.
# "RESUMO GERAL" (agregado de todos os regimes) e' ignorado, senao conta em
# dobro.
IRRF_REGIME_TO_CELL = {
    "RESUMO CONTRATO TEMPORARIO": "I15",
    "RESUMO ATIVOS - REGIME PRÓPRIO": "I30",
    "RESUMO ATIVOS - REGIME GERAL": "I44",
    "RESUMO MILITARES": "I58",
}
IRRF_LINHA_DESCRICAO = "3014 - IRRF"

# ---------------------------------------------------------------------------
# Registro de origem por celula (auditoria: de onde veio cada numero)
# ---------------------------------------------------------------------------
SOURCE_LABEL = "Importado automaticamente do relatório Ergon"


def celulas_gerenciadas() -> dict[str, list[str]]:
    """Todas as células que este sistema é responsável por preencher (ou
    seja: onde um Achado PODE cair). Usado pra zerar essas células antes de
    escrever um novo mês - assim, se o PDF de um mês não trouxer dado pra
    alguma delas (ex: nenhum Contrato Temporário naquele mês), a célula vira
    0 de verdade em vez de continuar com o valor do mês anterior.

    NÃO inclui as células que o sistema ainda não sabe preencher sozinho
    (detalhamento rubrica-por-rubrica, NES) - essas continuam manuais e
    não são tocadas aqui."""
    celulas: dict[str, set[str]] = {}

    def add(sheet, cell):
        celulas.setdefault(sheet, set()).add(cell)

    for destino in CREDITO_BANCARIO_REGIMES.values():
        add(SHEET_LIQUIDO, destino["liquido_total_cell"])
        add(SHEET_CONSIGNACOES, destino["consignacoes_resumo_cell"])

    for cell in ENCARGOS_FUNDO_TO_CELL.values():
        add(SHEET_LIQUIDO, cell)

    for cell in IRRF_REGIME_TO_CELL.values():
        add(SHEET_LIQUIDO, cell)

    for col in set(CONSIGNACOES_REGIME_TO_COLUMN.values()):
        for row in range(CONSIGNACOES_ROW_START, CONSIGNACOES_ROW_END + 1):
            add(SHEET_CONSIGNACOES, f"{col}{row}")

    return {sheet: sorted(cells) for sheet, cells in celulas.items()}


# ---------------------------------------------------------------------------
# Detalhamento rubrica-por-rubrica da aba Líquido Folha - o parser NÃO sabe
# preencher essas linhas (só sabe o total do bloco, via
# CREDITO_BANCARIO_REGIMES). Mas se a gente não limpar essas células ao
# gerar um mês novo, elas continuam mostrando o valor do mês anterior,
# parecendo dado real quando na verdade está desatualizado - pior do que
# deixar em branco. Por isso são zeradas junto (mas nunca preenchidas
# automaticamente com um valor - só o usuário sabe o valor certo aqui).
DETALHE_RUBRICA_BLOCOS = [
    (6, 14),    # Contratos - RGPS (total em H15)
    (18, 29),   # RPPS (total em H30)
    (33, 43),   # RGPS (total em H44)
    (47, 57),   # Militar (total em H58)
]
DETALHE_RUBRICA_COLUNAS = ["G", "H", "I"]


def celulas_detalhe_manual() -> dict[str, list[str]]:
    """Células de detalhe que o sistema NÃO preenche sozinho, mas limpa ao
    gerar um mês novo (ver docstring acima)."""
    celulas: list[str] = []
    for inicio, fim in DETALHE_RUBRICA_BLOCOS:
        for row in range(inicio, fim + 1):
            for col in DETALHE_RUBRICA_COLUNAS:
                celulas.append(f"{col}{row}")
    return {SHEET_LIQUIDO: sorted(celulas)}