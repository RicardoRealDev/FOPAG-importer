"""
Parser dos relatórios do Ergon (Governo do Tocantins - Secretaria da
Administração) em PDF, exportados para alimentar a Planilha FOPAG.

Cada função `parse_*` recebe a lista de textos de página (uma string por
página, na ordem do PDF) e devolve uma lista de `Achado` — um valor lido,
já mapeado para a célula de destino na planilha, com a evidência de onde
veio (para auditoria).

Este módulo não sabe nada sobre Google Sheets: só lê o PDF e produz uma
lista de instruções "escreva X na célula Y". Isso é proposital (separação
de responsabilidades) — troque o "writer" sem tocar aqui, e vice-versa.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import config

MONEY_RE = re.compile(r"^-?\s?\d{1,3}(?:\.\d{3})*,\d{2}$")
PERCENT_RE = re.compile(r"^-?\s?\d+,\d+%$")
INT_RE = re.compile(r"^\d+$")
INSTITUICAO_RE = re.compile(r"^\d+\s*-\s*.+")


@dataclass
class Achado:
    sheet: str
    cell: str
    valor: float
    origem: str          # de onde veio (nome do relatório/linha), para auditoria
    confianca: str = "alta"   # "alta" | "media" | "baixa" (baixa = precisa revisão)


@dataclass
class ItemNaoMapeado:
    regime: str
    codigo: str
    descricao: str
    valor: float
    origem: str


@dataclass
class ResultadoParse:
    achados: list[Achado] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    nao_mapeados: list[ItemNaoMapeado] = field(default_factory=list)


def _to_float(token: str) -> float:
    token = token.strip().replace("%", "")
    token = token.replace(".", "").replace(",", ".")
    return float(token)


def normalize(text: str) -> str:
    """Maiúsculas, sem acento, sem pontuação, espaços simples."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().upper()
    return text


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def _bloco_descricoes(lines: list[str], anchor_idx: int) -> tuple[int, int, list[str]]:
    """A partir de uma linha que bate com INSTITUICAO_RE (anchor_idx),
    expande pra trás e pra frente pra achar o bloco completo de itens
    "código - descrição", tolerando descrições que quebram em mais de uma
    linha no PDF (ex: "1113 - Ressarcimento 40%, Art. 22-A, Lei" seguido de
    "3661/2020" na linha de baixo - essa segunda linha não bate com
    INSTITUICAO_RE nem é um número, é só a continuação do texto).

    Devolve (start, end, itens) - start/end são os índices em `lines` que
    cobrem o bloco inteiro (incluindo continuações), itens é a lista de
    descrições já reconstituídas (uma por item de verdade, texto quebrado
    unido com espaço)."""
    end = anchor_idx
    while end + 1 < len(lines):
        nxt = lines[end + 1]
        if INSTITUICAO_RE.match(nxt) or _classify(nxt) is None:
            end += 1
        else:
            break  # comecei a bater em número - bloco de descrição acabou

    start = anchor_idx
    while start > 0:
        prev = lines[start - 1]
        if INSTITUICAO_RE.match(prev) or _classify(prev) is None:
            start -= 1
        else:
            break

    bloco = lines[start:end + 1]
    itens = []
    i = 0
    while i < len(bloco):
        texto = bloco[i]
        j = i + 1
        while j < len(bloco) and not INSTITUICAO_RE.match(bloco[j]):
            texto += " " + bloco[j]
            j += 1
        itens.append(texto)
        i = j
    return start, end, itens


def find_best_match(nome_pdf: str, candidatos: dict[str, str], limiar: float = 0.55) -> tuple[str | None, float]:
    """candidatos: {row_number_ou_cell: nome_na_planilha}. Retorna (cell, score) do melhor match."""
    best_cell, best_score = None, 0.0
    for cell, nome_planilha in candidatos.items():
        score = _similarity(nome_pdf, nome_planilha)
        if score > best_score:
            best_cell, best_score = cell, score
    if best_score < limiar:
        return None, best_score
    return best_cell, best_score


# ---------------------------------------------------------------------------
# Mês/ano do relatório -> corrige os títulos da planilha automaticamente
# ---------------------------------------------------------------------------
MESES_PT = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
            "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
MES_ANO_RELATORIO_RE = re.compile(r"M[êe]s/Ano\s*-\s*Folha:\s*(\d{2})/(\d{4})")


def extrair_mes_ano(pages: list[str]) -> str | None:
    """Lê o padrão 'Mês/Ano - Folha: MM/AAAA' que aparece em toda página do
    relatório do Ergon e devolve o rótulo em português, ex: 'JULHO DE 2026'.
    Usado pra corrigir automaticamente títulos desatualizados na planilha
    (ex: uma aba que ainda diz 'MAIO/2026' num mês de julho, porque o
    arquivo original foi reaproveitado de um mês anterior sem atualizar)."""
    texto = "\n".join(pages)
    m = MES_ANO_RELATORIO_RE.search(texto)
    if not m:
        return None
    mes_num = int(m.group(1))
    ano = m.group(2)
    if not (1 <= mes_num <= 12):
        return None
    return f"{MESES_PT[mes_num - 1]} DE {ano}"


# ---------------------------------------------------------------------------
# 1) RESUMO DE CRÉDITO BANCÁRIO -> totais líquidos por regime
# ---------------------------------------------------------------------------
CREDITO_BANCARIO_ANCHOR = "RESUMO DE CRÉDITO BANCÁRIO"


def parse_credito_bancario(pages: list[str]) -> ResultadoParse:
    resultado = ResultadoParse()
    total_geral_lido = None

    for page_num, text in enumerate(pages, start=1):
        if CREDITO_BANCARIO_ANCHOR not in text:
            continue

        lines = [l.strip() for l in text.split("\n")]
        if "DETALHES" not in lines:
            continue
        idx = lines.index("DETALHES")
        valores = []
        for l in lines[idx + 2: idx + 7]:
            if MONEY_RE.match(l):
                valores.append(_to_float(l))
        if len(valores) < 4:
            resultado.avisos.append(f"Pág. {page_num}: esperava 4 valores após DETALHES, achou {len(valores)}.")
            continue
        _atual, _anterior, _indenizacoes, total = valores[-4:]

        if config.CREDITO_BANCARIO_GERAL_TITLE in text:
            total_geral_lido = total
            continue  # usado so' para conferencia, nao mapeado para celula

        destino = None
        for titulo, alvo in config.CREDITO_BANCARIO_REGIMES.items():
            if titulo in text:
                destino = alvo
                break
        if destino is None:
            resultado.avisos.append(f"Pág. {page_num}: achou DETALHES mas não reconheci o regime do título.")
            continue

        origem = f"Pág. {page_num} — RESUMO DE CRÉDITO BANCÁRIO"
        resultado.achados.append(Achado(config.SHEET_LIQUIDO, destino["liquido_total_cell"], total, origem))
        resultado.achados.append(Achado(config.SHEET_CONSIGNACOES, destino["consignacoes_resumo_cell"], total, origem))
        if "liquido_atual_cell" in destino:
            resultado.achados.append(Achado(
                config.SHEET_LIQUIDO, destino["liquido_atual_cell"], _atual,
                f"{origem} — Exercício Atual",
            ))

    if total_geral_lido is not None:
        soma = sum(a.valor for a in resultado.achados if a.sheet == config.SHEET_CONSIGNACOES)
        if abs(soma - total_geral_lido) > 0.02:
            resultado.avisos.append(
                f"Conferência: soma dos 4 regimes ({soma:.2f}) não bate com o total geral do relatório ({total_geral_lido:.2f})."
            )
    return resultado


# ---------------------------------------------------------------------------
# 2) RESUMO DE CONSIGNAÇÕES -> detalhe por banco/instituição
# ---------------------------------------------------------------------------
def _classify(line: str) -> str | None:
    if MONEY_RE.match(line):
        return "money"
    if PERCENT_RE.match(line):
        return "percent"
    if INT_RE.match(line):
        return "int"
    return None


def _consignacoes_coluna(titulo: str) -> str | None:
    if titulo.strip().endswith("FACULTATIVAS - GERAL"):
        return None  # agregado - ignorar para nao contar em dobro
    if "CONTRATO TEMPORARIO" in titulo:
        # Essas consignações pertencem à seção separada "Apropriação das
        # Consignações - Contratos RGPS" (linhas 109-131), não ao bloco
        # principal F:J. Ainda não mapeado — ver README "limitações".
        return None
    if "MILITARES" in titulo:
        return "H"
    if "REGIME PRÓPRIO" in titulo:
        return "F"
    if "REGIME GERAL" in titulo:
        return "G"
    return None


def parse_consignacoes(pages: list[str], sheet_institution_names: dict[str, str]) -> ResultadoParse:
    """sheet_institution_names: {cell: nome_atual_na_planilha} - ex: {"27": "PLANSAÚDE COMPARTICIPAÇÃO", ...}"""
    resultado = ResultadoParse()
    title_re = re.compile(r"^RESUMO DE CONSIGNA.*FACULTATIVAS.*$", re.MULTILINE)

    for page_num, text in enumerate(pages, start=1):
        title_match = title_re.search(text)
        if not title_match:
            continue
        titulo = title_match.group(0).strip()
        coluna = _consignacoes_coluna(titulo)
        if coluna is None:
            continue

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        title_idx = lines.index(titulo)

        # coleta as linhas de instituicao (formato "codigo - nome") logo antes do titulo
        descricoes = []
        i = title_idx - 1
        while i >= 0 and INSTITUICAO_RE.match(lines[i]):
            descricoes.append(lines[i])
            i -= 1
        descricoes.reverse()
        n = len(descricoes)
        if n == 0:
            resultado.avisos.append(f"Pág. {page_num} ({titulo}): nenhuma instituição encontrada.")
            continue

        # classifica os tokens numericos ANTES do bloco de descricoes
        tokens = []
        for l in lines[:i + 1]:
            tipo = _classify(l)
            if tipo:
                tokens.append((tipo, _to_float(l) if tipo != "int" else int(l)))
        esperado = 4 + 5 * n
        if len(tokens) < esperado:
            resultado.avisos.append(
                f"Pág. {page_num} ({titulo}): esperava {esperado} números, achou {len(tokens)}. Pulando página."
            )
            continue
        tokens = tokens[-esperado:]
        # ordem das colunas na pagina: Qtd | Vlr Normal | Aliq | Vlr Fungerp | Vlr Liquido.
        # A planilha usa o valor ANTES do desconto do Fungerp (Vlr Normal),
        # confirmado comparando com institutos que tem aliquota > 0 (onde
        # Normal != Liquido) contra os valores ja existentes na planilha.
        pos = 4  # pula os 4 totais da pagina (nao usados aqui)
        pos += n  # qtd por linha
        vlr_normal = [v for (_t, v) in tokens[pos: pos + n]]

        for nome_pdf, valor in zip(descricoes, vlr_normal):
            nome_limpo = re.sub(r"^\d+\s*-\s*", "", nome_pdf)
            cell, score = find_best_match(nome_limpo, sheet_institution_names)
            origem = f"Pág. {page_num} — RESUMO DE CONSIGNAÇÕES — {nome_pdf}"
            if cell is None:
                resultado.avisos.append(
                    f"Não encontrei instituição correspondente a '{nome_limpo}' na planilha (pág. {page_num})."
                )
                continue
            confianca = "alta" if score > 0.85 else ("media" if score > 0.65 else "baixa")
            resultado.achados.append(Achado(config.SHEET_CONSIGNACOES, f"{coluna}{cell}", valor, origem, confianca))
    return resultado


# ---------------------------------------------------------------------------
# 3) ENCARGOS SOCIAIS - GERAL -> encargos sociais consolidados
# ---------------------------------------------------------------------------
# Layout observado (relatorio GTO0002R, secao "GERAL"): cada fundo conclui
# sua serie historica com um bloco "Total" contendo exatamente 4 valores
# monetarios (Vlr Base, Contribuição do Estado, Contribuição Segurado,
# Recolhimento) por fundo. Quando dois fundos concluem juntos na mesma
# pagina (ex: Fundo Previdenciário + INSS), os valores vem em blocos de
# colunas (column-major): primeiro os 4 valores do 1o fundo, depois os do
# 2o, na MESMA ordem em que os cabecalhos de coluna foram declarados.
#
# Importante: os cabecalhos de fundo podem aparecer "adiantados" na pagina
# (o relatorio ja declara a proxima coluna antes dela ter dados de fato),
# entao rastrear "qual foi o ultimo cabecalho visto" nao e' confiavel.
# Em vez disso, usamos uma premissa mais forte e estavel: o relatorio
# sempre fecha os fundos na MESMA ordem em que aparecem na config
# (Financeiro -> Previdenciário -> INSS -> Plansaude). Cada bloco "Total"
# de tamanho K e' atribuido aos proximos K fundos dessa lista que ainda
# nao foram encontrados.
FUNDOS_EM_ORDEM = list(config.ENCARGOS_FUNDO_TO_CELL.keys())


def parse_encargos(pages: list[str]) -> ResultadoParse:
    resultado = ResultadoParse()
    encontrados: list[str] = []  # preserva ordem de descoberta

    for page_num, text in enumerate(pages, start=1):
        if config.ENCARGOS_SECTION_TITLE not in text:
            continue
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        i = 0
        while i < len(lines):
            if lines[i] != "Total":
                i += 1
                continue
            k = 0
            j = i
            while j < len(lines) and lines[j] == "Total":
                k += 1
                j += 1
            money_block = lines[max(0, i - 4 * k): i]
            valores = [_to_float(v) for v in money_block if MONEY_RE.match(v)]

            pendentes = [f for f in FUNDOS_EM_ORDEM if f not in encontrados]
            alvo = pendentes[:k]

            if len(valores) != 4 * k:
                resultado.avisos.append(
                    f"Pág. {page_num}: bloco 'Total' (k={k}) com {len(valores)} valores monetários, esperava {4 * k}."
                )
            elif len(alvo) < k:
                resultado.avisos.append(
                    f"Pág. {page_num}: bloco 'Total' (k={k}) mas só restam {len(alvo)} fundo(s) pendente(s)."
                )
            else:
                # layout e' "metric-major": [vlr_base * k, contrib_estado * k,
                # contrib_segurado * k, recolhimento * k] - NAO agrupado por fundo.
                # contrib_estado e' a 2a metrica (indice 1), entao seu bloco
                # comeca em valores[1*k : 1*k + k].
                for idx_f, fundo in enumerate(alvo):
                    contrib_estado = valores[k + idx_f]
                    cell = config.ENCARGOS_FUNDO_TO_CELL[fundo]
                    origem = f"Pág. {page_num} — ENCARGOS SOCIAIS GERAL — {fundo} (Total)"
                    resultado.achados.append(Achado(config.SHEET_LIQUIDO, cell, contrib_estado, origem))
                    encontrados.append(fundo)
            i = j

    for f in FUNDOS_EM_ORDEM:
        if f not in encontrados:
            resultado.avisos.append(f"Não encontrei o total de '{f}' em ENCARGOS SOCIAIS - GERAL.")
    return resultado


# ---------------------------------------------------------------------------
# 4) RENDIMENTOS E DESCONTOS -> IRRF retido por regime
# ---------------------------------------------------------------------------
# Layout observado (relatorio GTO0001R, pagina "DESCONTOS" de cada regime):
# as descricoes ("codigo - nome", ex: "3014 - IRRF") vem ANTES dos numeros
# (ao contrario do RESUMO DE CONSIGNAÇÕES, onde vem depois). Depois delas,
# 3 pares de colunas Quant/Valor (Normal, Diferença, Devolução) e por fim
# uma coluna "Total" - todas com N valores, N = quantidade de linhas de
# descricao. O IRRF e' so' mais uma dessas N linhas; usamos sua posicao
# dentro do bloco de descricoes para achar seu valor na coluna Total.
def _irrf_regime_cell(text: str) -> str | None:
    if "RESUMO GERAL" in text:
        return None  # agregado de todos os regimes - ignorar p/ nao contar em dobro
    for titulo, cell in config.IRRF_REGIME_TO_CELL.items():
        if titulo in text:
            return cell
    return None


def parse_irrf(pages: list[str]) -> ResultadoParse:
    resultado = ResultadoParse()
    for page_num, text in enumerate(pages, start=1):
        if "DESCONTOS" not in text or config.IRRF_LINHA_DESCRICAO not in text:
            continue
        cell = _irrf_regime_cell(text)
        if cell is None:
            continue

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if config.IRRF_LINHA_DESCRICAO not in lines:
            resultado.avisos.append(f"Pág. {page_num}: achei '{config.IRRF_LINHA_DESCRICAO}' no texto mas não como linha isolada.")
            continue
        irrf_idx = lines.index(config.IRRF_LINHA_DESCRICAO)

        start, end, itens = _bloco_descricoes(lines, irrf_idx)
        n = len(itens)
        pos = next((i for i, it in enumerate(itens) if it.startswith(config.IRRF_LINHA_DESCRICAO)), None)
        if pos is None:
            resultado.avisos.append(f"Pág. {page_num}: não consegui localizar '{config.IRRF_LINHA_DESCRICAO}' dentro do bloco reconstituído.")
            continue

        # coleta os tokens numericos DEPOIS do bloco de descricoes: espera
        # 7 grupos de tamanho n (Quant/Valor x3 + Total)
        tokens = []
        for l in lines[end + 1:]:
            tipo = _classify(l)
            if tipo:
                tokens.append((tipo, _to_float(l) if tipo != "int" else int(l)))
            if len(tokens) >= 7 * n:
                break

        if len(tokens) < 7 * n:
            resultado.avisos.append(
                f"Pág. {page_num}: esperava {7 * n} números para a seção de IRRF, achei {len(tokens)}."
            )
            continue

        total_array = [v for (_t, v) in tokens[6 * n: 7 * n]]
        valor_irrf = total_array[pos]
        origem = f"Pág. {page_num} — RENDIMENTOS/DESCONTOS — {config.IRRF_LINHA_DESCRICAO}"
        resultado.achados.append(Achado(config.SHEET_LIQUIDO, cell, valor_irrf, origem))

    encontrados_cells = {a.cell for a in resultado.achados}
    for cell in config.IRRF_REGIME_TO_CELL.values():
        if cell not in encontrados_cells:
            resultado.avisos.append(f"Não encontrei IRRF para a célula {cell} (pode ser R$ 0,00 esse mês, ou o relatório de RENDIMENTOS não veio no PDF).")
    return resultado


# ---------------------------------------------------------------------------
# 5) RENDIMENTOS -> detalhamento rubrica-por-rubrica (mapeamento FIXO, ver
# config.RENDIMENTOS_MAPEAMENTO - não usa comparação de texto)
# ---------------------------------------------------------------------------
_CODIGO_DESCRICAO_RE = re.compile(r"^(\d+)\s*-\s*(.+)$")


def _rendimentos_regime_titulo(lines: list[str], text: str) -> str | None:
    """Só reconhece a página PRINCIPAL de rendimentos de cada regime - não
    "DESCONTOS" (isso é parse_irrf), nem "INDENIZAÇÕES" ou "EXERCÍCIOS
    ANTERIORES" (sub-relatórios ainda não mapeados)."""
    if "RENDIMENTOS" not in lines:
        return None
    if "DESCONTOS" in lines or "INDENIZAÇÕES" in lines or "EXERCÍCIOS ANTERIORES" in lines:
        return None
    if "RESUMO GERAL" in text:
        return None  # agregado de todos os regimes - ignorar p/ nao contar em dobro
    for titulo in config.RENDIMENTOS_MAPEAMENTO.keys():
        if titulo in text:
            return titulo
    return None


def parse_rendimentos(pages: list[str]) -> ResultadoParse:
    resultado = ResultadoParse()

    for page_num, text in enumerate(pages, start=1):
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        titulo_regime = _rendimentos_regime_titulo(lines, text)
        if titulo_regime is None:
            continue

        # acha uma linha-ancora "codigo - descricao" pra partir dali
        anchor_idx = next((idx for idx, l in enumerate(lines) if INSTITUICAO_RE.match(l)), None)
        if anchor_idx is None:
            resultado.avisos.append(f"Pág. {page_num} ({titulo_regime}): não achei nenhuma linha 'código - descrição' em RENDIMENTOS.")
            continue

        _start, desc_end, descricoes = _bloco_descricoes(lines, anchor_idx)
        n = len(descricoes)

        tokens = []
        for l in lines[desc_end + 1:]:
            tipo = _classify(l)
            if tipo:
                tokens.append((tipo, _to_float(l) if tipo != "int" else int(l)))
            if len(tokens) >= 7 * n:
                break
        if len(tokens) < 7 * n:
            resultado.avisos.append(
                f"Pág. {page_num} ({titulo_regime}): esperava {7 * n} números em RENDIMENTOS, achei {len(tokens)}."
            )
            continue

        total_array = [v for (_t, v) in tokens[6 * n: 7 * n]]
        mapa = config.RENDIMENTOS_MAPEAMENTO[titulo_regime]
        somas_por_linha: dict[str, float] = {}

        for desc_pdf, valor in zip(descricoes, total_array):
            m = _CODIGO_DESCRICAO_RE.match(desc_pdf)
            if not m:
                continue
            codigo, descricao_texto = m.group(1), m.group(2)
            if codigo in mapa:
                row = mapa[codigo]
                somas_por_linha[row] = somas_por_linha.get(row, 0.0) + valor
            elif valor != 0:
                resultado.nao_mapeados.append(ItemNaoMapeado(
                    regime=titulo_regime, codigo=codigo, descricao=descricao_texto,
                    valor=valor, origem=f"Pág. {page_num} — RENDIMENTOS",
                ))

        for row, valor in somas_por_linha.items():
            origem = f"Pág. {page_num} — RENDIMENTOS — {titulo_regime}"
            resultado.achados.append(Achado(config.SHEET_LIQUIDO, f"G{row}", valor, origem))
            resultado.achados.append(Achado(config.SHEET_LIQUIDO, f"H{row}", valor, origem))

    return resultado
