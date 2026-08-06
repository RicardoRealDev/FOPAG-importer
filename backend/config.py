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
CREDITO_BANCARIO_REGIMES = {
    "CONTRATO TEMPORARIO - REGIME GERAL DE PREVIDÊNCIA SOCIAL": {
        "liquido_total_cell": "H15",
        "consignacoes_resumo_cell": "D3",
        "liquido_atual_cell": "G6",
    },
    "ATIVOS - REGIME PRÓPRIO DE PREVIDÊNCIA SOCIAL": {
        "liquido_total_cell": "H30",
        "consignacoes_resumo_cell": "D4",
        "liquido_atual_cell": "G28",
    },
    "ATIVOS - REGIME GERAL DE PREVIDÊNCIA SOCIAL": {
        "liquido_total_cell": "H44",
        "consignacoes_resumo_cell": "D5",
        "liquido_atual_cell": "G35",
    },
    "MILITARES - REGIME DE PREVIDENCIA MILITARES": {
        "liquido_total_cell": "H58",
        "consignacoes_resumo_cell": "D6",
        "liquido_atual_cell": "G49",
    },
}
# "liquido_atual_cell": a linha de "Vencimento/Subsídio atual" de cada bloco
# (6/28/35/49) tem colunas G e H DIFERENTES entre si (confirmado comparando
# REL FOPAG JULHO-01.pdf com uma planilha real de julho): G bate exatamente
# com "Exercício Atual" do Resumo de Crédito Bancário (GTO0003R); H (o valor
# realmente liquidado) não bate com nenhum numero dos relatorios que
# recebemos até agora - por isso só G é preenchido automaticamente aqui,
# H fica em branco para lançamento manual (ver RENDIMENTOS_MAPEAMENTO abaixo).
CREDITO_BANCARIO_GERAL_TITLE = "RESUMO DE CRÉDITO BANCÁRIO GERAL"
CONSIGNACOES_TOTAL_GERAL_CELL = "D7"  # usado so' para conferencia/alerta

# ---------------------------------------------------------------------------
# 2) RESUMO DE CONSIGNAÇÕES (GTO0004R) -> detalhe por banco/instituicao
# ---------------------------------------------------------------------------
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
ENCARGOS_FUNDO_TO_CELL = {
    "FUNDO DE PREVIDENCIA (FUNDO FINANCEIRO)": "F68",
    "FUNDO DE PREVIDENCIA (FUNDO PREVIDENCIÁRIO)": "F69",
    "I.N.S.S.": "F70",
    "PLANSAUDE": "F71",
}
ENCARGOS_SECTION_TITLE = "ENCARGOS SOCIAIS - GERAL"

# ---------------------------------------------------------------------------
# 3b) ENCARGOS SOCIAIS - por regime (GTO0002R, seções específicas de cada
# regime - NÃO a seção "GERAL" acima) -> contribuição do SEGURADO
# (empregado) por fundo, que alimenta as linhas 14-19 da aba Consignações
# (Fundo Financeiro, Fundo Previdenciário, INSS - "atual" e "(92) DEA" =
# ajuste de exercício anterior).
#
# Confirmado manualmente contra REL FOPAG JULHO-01.pdf (6 de 6 valores
# batendo exato com uma planilha real de julho). Cada fundo tem um bloco
# "Subtotal (ANTERIOR)" (opcional - nem todo mês tem ajuste) + "Subtotal
# (ATUAL)"; a RGPS-ativos é diferente: vários fundos aparecem juntos num
# só bloco "Subtotal (ATUAL)" repetido. Usa a mesma premissa de "ordem
# estável do relatório" já usada em FUNDOS_EM_ORDEM - se algum mês vier
# fora da ordem esperada, o parser gera um aviso em vez de errar
# silenciosamente.
# ---------------------------------------------------------------------------
ENCARGOS_REGIME_RGPS_TITLE = "ENCARGOS SOCIAIS - ATIVOS - REGIME GERAL DE PREVIDÊNCIA SOCIAL"
ENCARGOS_REGIME_RPPS_TITLE = "ENCARGOS SOCIAIS - ATIVOS - REGIME PRÓPRIO DE PREVIDÊNCIA SOCIAL"
ENCARGOS_REGIME_MILITAR_TITLE = "ENCARGOS SOCIAIS - MILITARES - MILITARES"

# RGPS: bloco único com vários fundos lado a lado ("Subtotal (ATUAL)" x k).
# Só o INSS tem linha dedicada na planilha hoje; PLANSAUDE aparece no
# relatório mas fica de fora (None) até termos uma célula pra ele.
CONSIGNACOES_FUNDOS_RGPS = [
    ("I.N.S.S.", "G18", "G19"),
    ("PLANSAUDE", None, None),
]

# RPPS e MILITAR: um fundo de cada vez, cada um com seu próprio bloco.
CONSIGNACOES_FUNDOS_RPPS = [
    ("FUNDO DE PREVIDENCIA (FUNDO FINANCEIRO)", "F14", "F15"),
    ("FUNDO DE PREVIDENCIA (FUNDO PREVIDENCIÁRIO)", "F16", "F17"),
]
CONSIGNACOES_FUNDOS_MILITAR = [
    ("FUNDO DE PREVIDENCIA (FUNDO FINANCEIRO)", "H14", "H15"),
]

# ---------------------------------------------------------------------------
# 4) RENDIMENTOS E DESCONTOS (GTO0001R) -> IRRF retido por regime
# ---------------------------------------------------------------------------
IRRF_REGIME_TO_CELL = {
    "RESUMO CONTRATO TEMPORARIO": "I15",
    "RESUMO ATIVOS - REGIME PRÓPRIO": "I30",
    "RESUMO ATIVOS - REGIME GERAL": "I44",
    "RESUMO MILITARES": "I58",
}
IRRF_LINHA_DESCRICAO = "3014 - IRRF"

# O mesmo IRRF tambem aparece na linha 20 da aba Consignacoes (F/G/H) -
# confirmado que e' o MESMO valor, so' espelhado numa segunda celula.
# Contrato Temporario nao tem coluna dedicada nessa linha, por isso nao
# entra aqui.
IRRF_REGIME_TO_CONSIGNACOES_CELL = {
    "RESUMO ATIVOS - REGIME PRÓPRIO": "F20",
    "RESUMO ATIVOS - REGIME GERAL": "G20",
    "RESUMO MILITARES": "H20",
}

# ---------------------------------------------------------------------------
# 5) RENDIMENTOS (GTO0001R, pagina "RENDIMENTOS" principal de cada regime)
# -> detalhamento rubrica-por-rubrica da Liquido Folha
# ---------------------------------------------------------------------------
# ATENCAO: este mapeamento e' FIXO (codigo Ergon -> linha da planilha),
# conferido manualmente com o usuario - NAO usa comparacao de texto/nome,
# porque isso ja' se provou perigoso (ex: "Ressarcimento 40%" e
# "Ressarcimento 30%" tem frases quase identicas e comparacao de texto
# confundiu os dois com confianca alta). So' adicione codigo novo aqui
# depois de confirmar manualmente contra a planilha real.
#
# Quando dois codigos apontam pra mesma linha (ex: 1027+1028), os valores
# sao somados.
#
# ATENCAO: os codigos "1201" (linha 6) e "1001" (linha 28) foram REMOVIDOS
# de propósito - essas linhas usam a coluna G vinda do Crédito Bancário
# (ver CREDITO_BANCARIO_REGIMES."liquido_atual_cell" acima), e o "Total" do
# relatório de Rendimentos NÃO bate nem com G nem com H nessas linhas.
# Esses codigos continuam aparecendo na tabela de "não mapeados" para
# conferência manual - não apague-os de lá sem investigar antes.
RENDIMENTOS_MAPEAMENTO = {
    "RESUMO CONTRATO TEMPORARIO": {
        "1027": "7",           # 13º Salário Proporcional
        "1028": "7",           # Adiantamento de 13º Salário
        "1204": "9",           # Férias Proporcionais Indenizadas
        "1205": "9",           # Adicional de Férias Proporcionais Indenizadas
        "1319": "12",          # Auxílio Alimentação
    },
    "RESUMO ATIVOS - REGIME PRÓPRIO": {
        "1026": "19",          # 13º Salário
        "1023": "22",          # Adicional de Férias
        "1319": "23",          # Auxílio Alimentação
        "1311": "24",          # Ressarcimento 30%
        "1113": "25",          # Ressarcimento 40%
        "1002": "27",          # Subsídio
    },
    "RESUMO ATIVOS - REGIME GERAL": {
        "1028": "33",          # Adiantamento de 13º Salário
        "1113": "37",          # Ressarcimento 40%
        "1311": "38",          # Ressarcimento 30%
        "1319": "42",          # Auxílio Alimentação
    },
    "RESUMO MILITARES": {
        "1026": "47",          # 13º Salário
        "1113": "51",          # Ressarcimento 40%
    },
}
# Linha (a partir daqui) onde ficam os itens que o mapeamento acima não
# cobre - nunca lançados na planilha, só listados para revisão manual.
RENDIMENTOS_NAO_MAPEADOS_LINHA_INICIAL = 130
RENDIMENTOS_NAO_MAPEADOS_LINHA_FINAL = 250  # limpo até aqui antes de escrever, para não sobrar lixo de mes anterior

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
    (detalhamento rubrica-por-rubrica não mapeado, NES) - essas continuam
    manuais e não são tocadas aqui."""
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
# Detalhamento rubrica-por-rubrica da aba Líquido Folha - zerado ao gerar
# mês novo (evita mostrar dado velho disfarçado de atual). O que TEM
# mapeamento fixo (RENDIMENTOS_MAPEAMENTO) é preenchido por cima; o resto
# fica em branco mesmo, aguardando lançamento manual.
DETALHE_RUBRICA_BLOCOS = [
    (6, 14),    # Contratos - RGPS (total em H15)
    (18, 29),   # RPPS (total em H30)
    (33, 43),   # RGPS (total em H44)
    (47, 57),   # Militar (total em H58)
]
DETALHE_RUBRICA_COLUNAS = ["G", "H", "I"]


def celulas_detalhe_manual() -> dict[str, list[str]]:
    """Células de detalhe zeradas ao gerar um mês novo (ver docstring
    acima)."""
    celulas: list[str] = []
    for inicio, fim in DETALHE_RUBRICA_BLOCOS:
        for row in range(inicio, fim + 1):
            for col in DETALHE_RUBRICA_COLUNAS:
                celulas.append(f"{col}{row}")
    return {SHEET_LIQUIDO: sorted(celulas)}
