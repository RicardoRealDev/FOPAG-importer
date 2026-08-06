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
SHEET_NES = "NES"

# ---------------------------------------------------------------------------
# 1) RESUMO DE CRÉDITO BANCÁRIO (GTO0003R) -> totais liquidos por regime
# ---------------------------------------------------------------------------
CREDITO_BANCARIO_REGIMES = {
    "CONTRATO TEMPORARIO - REGIME GERAL DE PREVIDÊNCIA SOCIAL": {
        "liquido_total_cell": "H15",
        "consignacoes_resumo_cell": "D3",
        "liquido_atual_cell": "G6",
        "liquido_anterior_linha": "11",
        "liquido_indenizacoes_linha": "14",
    },
    "ATIVOS - REGIME PRÓPRIO DE PREVIDÊNCIA SOCIAL": {
        "liquido_total_cell": "H30",
        "consignacoes_resumo_cell": "D4",
        "liquido_atual_cell": "G28",
        "liquido_anterior_linha": "26",
        "liquido_indenizacoes_linha": "29",
    },
    "ATIVOS - REGIME GERAL DE PREVIDÊNCIA SOCIAL": {
        "liquido_total_cell": "H44",
        "consignacoes_resumo_cell": "D5",
        "liquido_atual_cell": "G35",
        "liquido_anterior_linha": "41",
        "liquido_indenizacoes_linha": "43",
    },
    "MILITARES - REGIME DE PREVIDENCIA MILITARES": {
        "liquido_total_cell": "H58",
        "consignacoes_resumo_cell": "D6",
        "liquido_atual_cell": "G49",
        "liquido_anterior_linha": "55",
        "liquido_indenizacoes_linha": "57",
    },
}
# "liquido_atual_cell": a linha de "Vencimento/Subsídio atual" de cada bloco
# (6/28/35/49) tem colunas G e H DIFERENTES entre si (confirmado comparando
# REL FOPAG JULHO-01.pdf com uma planilha real de julho): G bate exatamente
# com "Exercício Atual" do Resumo de Crédito Bancário (GTO0003R); H (o valor
# realmente liquidado) não bate com nenhum numero dos relatorios que
# recebemos até agora - por isso só G é preenchido automaticamente aqui,
# H fica em branco para lançamento manual (ver RENDIMENTOS_MAPEAMENTO abaixo).
#
# "liquido_anterior_linha"/"liquido_indenizacoes_linha": mesma lógica, mas
# pras linhas "(Exercício Anterior) DEA" e "Indenizações" de cada bloco -
# vêm do "Exercício Anterior" e "Indenizações" do mesmo relatório de
# Crédito Bancário (os outros 2 dos 4 números que já líamos e
# descartávamos). Confirmado exato contra a mesma planilha de julho.
# DIFERENTE do "atual" acima: aqui G e H são sempre IGUAIS (confirmado),
# e as fórmulas da aba NES puxam especificamente da coluna H - por isso
# escrevemos nas DUAS colunas (G e H), não só em G.
# continua manual).
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
# 2b) RESUMO DE CONSIGNAÇÕES - mapeamento FIXO (nome normalizado -> linha),
# por coluna/regime, pras instituições já confirmadas. Complementa o
# find_best_match (comparação de texto) usado pras demais - quando o nome
# bate aqui, usa direto, sem depender de score de similaridade.
#
# Construído cruzando REL FOPAG JULHO-01.pdf com os valores REAIS de uma
# planilha de julho, casando por VALOR (não por nome) pra evitar erro -
# só entrou aqui o que teve casamento numérico exato/único. Escopado por
# coluna (F=RPPS, G=RGPS, H=Militar) porque a MESMA instituição pode cair
# em linhas diferentes dependendo do regime (ex: Plansaúde Comparticipação
# é linha 27 tanto em F quanto G, mas BRB-Banco de Brasília no Militar não
# bateu com a mesma linha usada em F/G - por isso não entrou pra H).
CONSIGNACOES_MAPEAMENTO = {
    "F": {  # RPPS
        "PLANSAUDE COMPARTICIPACAO": "27",
        "BANCO DO BRASIL": "41",
        "CAIXA DO TRABALHADOR": "56",
        "SINPOL MENSALIDADE": "58",
        "BANCO DAYCOVAL": "63",
        "CIASPREV MENSALIDADE": "67",
        "AJUSP TO": "85",
        "BRB BANCO DE BRASILIA": "87",
        "BRB BANCO DE BRASILIA PASSIVOS": "86",
        "ASSECAD MENSALIDADE": "31",
        "SISEPE MENSALIDADE": "52",
    },
    "G": {  # RGPS
        "PLANSAUDE COMPARTICIPACAO": "27",
        "PLANSAUDE DEPENDENTE INDIRETO": "28",
        "ASSECAD MENSALIDADE": "31",
        "BRADESCO EMPRESTIMO": "45",
        "KARDBANK": "89",
        "BRB BANCO DE BRASILIA": "87",
        "ZAHAV ADIANT SALARIO": "90",
    },
    "H": {},  # Militar - nenhum nome confirmado ainda, ver CONSIGNACOES_CODIGO_MAPEAMENTO
}

# Casos em que o mesmo código Ergon cobre várias variantes que a planilha
# soma numa única linha (ex: Plano de Saúde Militar tem 3 variantes -
# Comparticipação/Mensalidade/Odontológico - todas com código "3059",
# somadas na linha 26). Diferente do mapeamento acima, aqui a chave é o
# código (não o nome), porque o nome varia mas o código não.
CONSIGNACOES_CODIGO_MAPEAMENTO = {
    "H": {
        "3059": "26",
    },
}

# ---------------------------------------------------------------------------
# 2c) "Apropriação das Consignações - Contratos RGPS" (segunda tabela da
# aba Consignações, linhas ~109-119) -> consignações dos funcionários de
# Contrato Temporário. Diferente do bloco principal (colunas F/G/H por
# regime), aqui só existe UMA coluna de valor (F), porque é um regime só.
# Confirmado contra REL FOPAG JULHO-01.pdf e uma planilha real de julho.
# ---------------------------------------------------------------------------
CONSIGNACOES_CONTRATO_MAPEAMENTO = {
    "ZAHAV ADIANT SALARIO": "119",
}
CONSIGNACOES_CONTRATO_ROW_START = 109
CONSIGNACOES_CONTRATO_ROW_END = 119

# INSS dos Contratos vem do relatório de Encargos Sociais (GTO0002R,
# seção específica de Contrato Temporário) - mesma técnica/formato usado
# em CONSIGNACOES_FUNDOS_RPPS/MILITAR acima.
ENCARGOS_REGIME_CONTRATO_TITLE = "ENCARGOS SOCIAIS - CONTRATO TEMPORARIO - REGIME GERAL DE PREVIDÊNCIA SOCIAL"
CONSIGNACOES_CONTRATO_FUNDOS = [
    ("I.N.S.S.", "F109", None),
]

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
    "RESUMO CONTRATO TEMPORARIO": "F111",  # tabela "Apropriação... Contratos RGPS"
    "RESUMO ATIVOS - REGIME PRÓPRIO": "F20",
    "RESUMO ATIVOS - REGIME GERAL": "G20",
    "RESUMO MILITARES": "H20",
}

# O IRRF também aparece espelhado na própria aba Líquido Folha, na coluna I
# da linha "Vencimento/Subsídio atual" de cada regime (mesma linha do
# liquido_atual_cell acima - ex: I28 pra RPPS, na mesma linha de G28).
# Confirmado exato contra REL FOPAG JULHO-01.pdf.
IRRF_REGIME_TO_LIQUIDO_MIRROR_CELL = {
    "RESUMO CONTRATO TEMPORARIO": "I6",
    "RESUMO ATIVOS - REGIME PRÓPRIO": "I28",
    "RESUMO ATIVOS - REGIME GERAL": "I35",
    "RESUMO MILITARES": "I49",
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
        "1028": "19",          # Adiantamento de 13º Salário (confirmado: soma com 1026 em G19)
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
        "1023": "48",          # Adicional de Férias
        "1113": "51",          # Ressarcimento 40%
    },
}
# Linha (a partir daqui) onde ficam os itens que o mapeamento acima não
# cobre - nunca lançados na planilha, só listados para revisão manual.
RENDIMENTOS_NAO_MAPEADOS_LINHA_INICIAL = 130
RENDIMENTOS_NAO_MAPEADOS_LINHA_FINAL = 250  # limpo até aqui antes de escrever, para não sobrar lixo de mes anterior

# ---------------------------------------------------------------------------
# 6) Aba NES ("Nº NE" / Notas de Empenho) -> coluna FOLHA (E)
# ---------------------------------------------------------------------------
# A aba NES lista o valor da folha por código de natureza orçamentária. As
# colunas "Nº NE" e "SALDO" são dados do sistema orçamentário (não vêm no
# relatório de folha) - continuam manuais. A coluna "FOLHA" (E) é sempre
# vazia no modelo - é o slot que este sistema preenche.
#
# Confirmado cruzando REL FOPAG JULHO-01.pdf com uma planilha real de
# julho: pra cada natureza abaixo, o valor bate EXATO com uma combinação
# específica de dados que já extraímos de outros relatórios (não é uma
# soma simples "por natureza" - cada linha tem sua própria regra, documentada
# em parser.py:parse_nes). Só entrou aqui o que bateu exato - as demais
# naturezas da aba continuam manuais.
NES_FOLHA_COL = "E"
NES_LINHA_13_SALARIO_RPPS = "7"          # Rendimentos RPPS (G19) + Rendimentos RGPS (G33)
NES_LINHA_FERIAS_RPPS = "8"              # Rendimentos RPPS, código 1023 (mesma fonte de G22)
NES_LINHA_VENC_ANTERIOR_RPPS = "12"      # Crédito Bancário RPPS - "Exercício Anterior"
NES_LINHA_INDENIZACOES = "15"            # Crédito Bancário - soma "Indenizações" de Contrato+RPPS+RGPS (exclui Militar)
NES_LINHA_INSS_RGPS = "16"               # Encargos Sociais RGPS - INSS, Contribuição do Estado
NES_LINHA_OBRIGACOES_ANTERIOR_RPPS = "18"  # Encargos RPPS - 2 fundos somados, Contribuição do Estado, Anterior
NES_LINHA_CONTRIB_PATRONAL_CIVIL_RPPS = "19"  # Encargos RPPS - 2 fundos somados, Contribuição do Estado, Atual
NES_LINHA_PLANSAUDE_PATRONAL = "20"      # Encargos GERAL - Plansaúde, Contribuição do Estado (mesma fonte de F71)
NES_LINHA_FUNDO_GOIAS = "23"             # Encargos Militar - Fundo Financeiro, Contribuição do Estado, Atual

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
    (detalhamento rubrica-por-rubrica não mapeado, maioria da aba NES) -
    essas continuam manuais e não são tocadas aqui."""
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

    for row in range(CONSIGNACOES_CONTRATO_ROW_START, CONSIGNACOES_CONTRATO_ROW_END + 1):
        add(SHEET_CONSIGNACOES, f"F{row}")

    for linha in (
        NES_LINHA_13_SALARIO_RPPS, NES_LINHA_FERIAS_RPPS, NES_LINHA_VENC_ANTERIOR_RPPS,
        NES_LINHA_INDENIZACOES, NES_LINHA_INSS_RGPS, NES_LINHA_OBRIGACOES_ANTERIOR_RPPS,
        NES_LINHA_CONTRIB_PATRONAL_CIVIL_RPPS, NES_LINHA_PLANSAUDE_PATRONAL, NES_LINHA_FUNDO_GOIAS,
    ):
        add(SHEET_NES, f"{NES_FOLHA_COL}{linha}")

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
