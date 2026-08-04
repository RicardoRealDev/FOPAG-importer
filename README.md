# FOPAG Importer

Lê o relatório em PDF do Ergon (folha de pagamento — Governo do Tocantins,
Secretaria da Administração) e grava os valores direto na Planilha FOPAG no
Google Sheets, sem digitação manual.

Feito para crescer: hoje importa 3 tipos de relatório para 1 planilha; a
estrutura já foi pensada para receber novos relatórios e novos sistemas da
secretaria sem reescrever nada do que já existe.

## Como funciona (visão geral)

```
[PDF do Ergon] --arraste-->  [frontend estático]  --POST-->  [Cloud Function]
                                (GitHub Pages)                     |
                                                          extrai texto (parser.py)
                                                          casa com a planilha
                                                          mostra pra você conferir
                                                                    |
                                                          você clica "Gravar"
                                                                    |
                                                          escreve no Google Sheets
                                                          (sheet_writer.py)
```

Nada é gravado sem você ver antes. O fluxo é sempre: enviar → conferir →
confirmar. Itens de baixa confiança (nomes de instituição que não bateram
com segurança) ficam de fora automaticamente — aparecem na tela pra
revisão manual, nunca são gravados sozinhos.

## O que já está coberto

| Relatório do Ergon | Vai para | Status |
|---|---|---|
| Resumo de Crédito Bancário (GTO0003R) | Totais líquidos por regime (Líquido Folha + resumo da aba Consignações) | ✅ Testado |
| Resumo de Consignações (GTO0004R) | Detalhe por banco/instituição (aba Consignações, colunas F/G/H) | ✅ Testado (Ativos RPPS/RGPS/Militar) |
| Encargos Sociais - Geral (GTO0002R) | Fundo Financeiro, Fundo Previdenciário, INSS, Plansaude (aba Líquido Folha) | ✅ Testado |

## Limitações conhecidas (leia antes de confiar de olhos fechados)

- **IRRF retido** e **NES (Notas de Empenho)** não vêm neste PDF — não
  encontramos esses relatórios na exportação que testamos. Ainda são
  manuais. Ver `docs/roteiro-requisitos` do projeto principal.
- **Detalhamento rubrica-por-rubrica** da aba Líquido Folha (13º, férias,
  auxílio-alimentação linha a linha) não é automatizado — o PDF só dá o
  agregado por regime. As fórmulas da aba NES dependem dessas linhas
  individuais, então isso não é só "não implementado ainda", é uma decisão
  em aberto (ver conversa sobre isso no histórico do projeto).
- **Consignações de Contrato Temporário** (regime RGPS) aparecem no PDF
  mas ainda não são mapeadas — elas pertencem a uma seção separada da
  planilha (linhas 109-131, "Apropriação das Consignações - Contratos
  RGPS") que ainda não foi conectada ao parser.
- **Nomes de instituição muito genéricos** (ex: "Banco do Brasil" no PDF
  quando a planilha tem várias linhas "BB ..." diferentes) podem casar com
  a linha errada. Por isso todo casamento de nome vem com um nível de
  confiança (alta/média/baixa) e o item some da lista de gravação
  automática se a confiança não for alta ou média — sempre confira a
  seção "avisos" e os itens de baixa confiança antes de assumir que está
  tudo certo.
- Testado com **um único mês** (julho/2026). O layout do Ergon é estável
  entre páginas do mesmo relatório, mas ainda não foi validado com um
  segundo mês — rode a importação em modo "revisar" e compare com a
  planilha manualmente nos primeiros 2-3 meses de uso antes de confiar
  cegamente no modo "aplicar".

## Privacidade: por que o repositório é público mas os dados não

O GitHub Pages gratuito só funciona em repositório público. Pra isso não
significar expor dados reais de servidores, o `.gitignore` exclui:

- `backend/fixtures/relatorio_julho_2026.pdf` (tem nomes individuais na
  seção "Servidores Afastados" do relatório)
- `backend/fixtures/ground_truth_julho_2026.json` e
  `instituicoes_consignacoes.json` (valores financeiros reais)

Esses arquivos **nunca são enviados ao GitHub** — ficam só na sua máquina.
Os testes que dependem deles (`tests/test_parser_com_pdf_real.py`) são
pulados automaticamente quando não existem (é isso que roda no GitHub
Actions). Veja `backend/fixtures/README.md` para recriá-los localmente.
A verificação "de verdade" em produção é reenviar o PDF do mês pela
própria tela do site e conferir os valores antes de gravar — não precisa
do PDF morar no repositório pra isso funcionar.

**Antes de dar `git push` pela primeira vez**, confira que esses 3
arquivos não aparecem em `git status` (se aparecerem, o `.gitignore` não
foi aplicado — rode `git rm --cached <arquivo>` antes de commitar).

## Estrutura do projeto

```
backend/
  config.py          # mapeamento único: relatório -> célula da planilha
  parser.py           # le o texto do PDF, devolve lista de "Achado"
  pdf_extract.py       # so' extrai texto (troque aqui se precisar de OCR no futuro)
  sheet_writer.py      # escreve os Achado na planilha via Google Sheets API
  main.py              # Cloud Function HTTP (a "cola" entre tudo isso)
  fixtures/            # PDF real + valores conhecidos - NAO commitado (ver .gitignore)
  tests/               # pytest - roda sozinho no GitHub Actions a cada push
                        # (test_parser.py sempre roda; test_parser_com_pdf_real.py
                        # so' roda se voce tiver as fixtures locais)
frontend/
  index.html           # pagina unica, sem build, hospedada no GitHub Pages
.github/workflows/
  test.yml             # roda os testes em todo push/PR
  deploy.yml           # publica a Cloud Function (so' se os testes passarem)
```

### Por que separado assim (para quem for mexer depois)

- `parser.py` não sabe que existe Google Sheets. `sheet_writer.py` não sabe
  que existe PDF. Um dia, se precisar importar de outro sistema da
  secretaria, o novo parser entra do lado do `parser.py` sem tocar no
  resto.
- `config.py` é a única fonte de verdade sobre "o que vai pra onde". Se o
  layout da planilha mudar, mexe só aqui.
- Testes usam o PDF real como fixture — qualquer alteração que quebrar a
  leitura correta dos números é pega automaticamente, antes de chegar em
  produção (é isso que o `test.yml` garante a cada push).

## Como implantar (passo a passo)

Isso aqui você faz uma vez. Precisa de uma conta Google e uma conta
GitHub (as suas mesmas, gratuitas).

### 1. Criar a conta de serviço do Google (pra Cloud Function acessar o Sheets)

1. Acesse [console.cloud.google.com](https://console.cloud.google.com), crie um projeto (gratuito)
2. Ative a **Google Sheets API** (Menu → APIs e Serviços → Ativar APIs)
3. Crie uma **conta de serviço** (IAM e administrador → Contas de serviço → Criar)
4. Gere uma chave JSON dessa conta de serviço e guarde com segurança
5. Abra a Planilha FOPAG no Sheets → Compartilhar → cole o e-mail da conta
   de serviço (termina em `.iam.gserviceaccount.com`) com permissão de
   **Editor**

### 2. Publicar o repositório no GitHub

O repositório precisa ser **público** (GitHub Pages gratuito exige isso).
Os dados sensíveis já ficam de fora automaticamente pelo `.gitignore` —
confira com `git status` antes do commit que `backend/fixtures/*.pdf` e os
dois `.json` de dados reais não aparecem como "arquivos a enviar".

```bash
cd fopag-importer
git init
git add .
git status   # confira aqui que os arquivos de fixtures NAO aparecem
git commit -m "Importador de PDF da FOPAG"
gh repo create fopag-importer --public --source=. --push
```

Se você já criou o repositório pelo site do GitHub como **privado** (como
no seu caso), pode trocar depois em Settings → General → role até o fim
→ **Change repository visibility** → **Make public**. Antes de trocar,
confirme no site (aba **Code**) que `backend/fixtures/relatorio_julho_2026.pdf`
não está listado — se você fez upload manual dos arquivos do zip, é
possível que ele tenha subido junto; se estiver lá, apague esse arquivo
específico pelo GitHub antes de tornar o repositório público.

### 3. Configurar os segredos do GitHub Actions

No repositório → Settings → Secrets and variables → Actions:

| Nome | Valor |
|---|---|
| `GCP_SA_KEY` | conteúdo do JSON da conta de serviço do passo 1 |
| `GCP_FUNCTION_SERVICE_ACCOUNT` | e-mail da conta de serviço |
| `DEFAULT_SPREADSHEET_ID` | o ID da Planilha FOPAG (está na URL, entre `/d/` e `/edit`) |

E em Variables:

| Nome | Valor |
|---|---|
| `ALLOWED_ORIGIN` | a URL do seu GitHub Pages (ex: `https://seuusuario.github.io`) |

Assim que você der `git push`, o `deploy.yml` publica a Cloud Function
sozinho (só se os testes passarem primeiro).

### 4. Ativar o GitHub Pages

Settings → Pages → Source: branch `main`, pasta `/frontend`. Em alguns
minutos o site fica em `https://seuusuario.github.io/fopag-importer`.

### 5. Configurar o frontend

Edite `frontend/index.html`, no topo do `<script>`:

```js
const API_URL = "https://southamerica-east1-SEUPROJETO.cloudfunctions.net/fopag-importar-pdf";
const SPREADSHEET_ID = "o-id-da-sua-planilha";
```

`git push` de novo e pronto — o site atualiza sozinho.

## Rodando localmente (pra testar antes de publicar)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # no Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -v                              # roda os testes (pula os que precisam do PDF real, se ele nao estiver em fixtures/)
python tests/conferencia_manual.py     # relatório de conferência linha a linha (precisa das fixtures locais)
```

## Custo esperado

Rodando pra uma secretaria (uso mensal, poucos usuários): **essencialmente
R$ 0/mês**. GitHub Pages é gratuito, e o volume de uso fica muito abaixo
da cota gratuita da Google Cloud Functions (2 milhões de execuções/mês).
O único custo possível é um domínio próprio, se um dia quiserem trocar o
`github.io` por algo como `fopag.suasecretaria.gov.br` (~R$40-80/ano).
