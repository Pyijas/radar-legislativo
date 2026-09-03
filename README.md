# Radar Legislativo — Saúde/Farma

Script que coleta projetos de lei federais recém apresentados em três fontes —
**Câmara dos Deputados**, **Senado Federal** (Brasil) e o **Congresso dos
EUA** (House + Senate) — e classifica o impacto de cada um sobre o setor de
saúde/farma (hospitais, planos de saúde, indústria farmacêutica, farmácias,
ANVISA/ANS/FDA, pacientes etc.) em duas camadas:

1. **Heurística por palavras-chave** (português e inglês) — sempre roda,
   100% gratuita, instantânea.
2. **IA** (Anthropic Claude ou Google Gemini) — roda por cima quando há chave
   configurada e refina a classificação da heurística.

Isso significa que o script é útil mesmo sem nenhuma chave de IA, e continua
funcionando (caindo pra heurística) se a IA falhar por rate limit, falta de
crédito ou estar fora do ar.

## Como funciona

1. Consulta a [API da Câmara](https://dadosabertos.camara.leg.br/), a
   [API do Senado](https://legis.senado.leg.br/dadosabertos) e a
   [API do Congress.gov](https://api.congress.gov/) (EUA, se configurada) por
   proposições apresentadas/atualizadas nos últimos N dias.
2. Pra Câmara e EUA, busca detalhes extras (inteiro teor / resumo oficial) de
   cada proposição nova; o Senado já devolve tudo isso na própria listagem.
3. Classifica por palavras-chave (sempre) e, se houver chave de IA configurada,
   também via IA — que retorna resumo em linguagem simples (sempre em
   português, mesmo pra projetos dos EUA), áreas específicas impactadas, tipo
   de impacto (tributário, regulatório etc.) e nível de impacto estimado
   (alto/médio/baixo), substituindo a heurística.
4. Guarda tudo em um banco SQLite local (`data/radar.db`), identificando cada
   proposição por (país, casa, id de origem) para não reprocessar a mesma
   duas vezes nem misturar as numerações de fontes diferentes.
5. Gera o painel (`data/index.html` + `pais.html` + `salvos.html`, ver seção
   abaixo), imprime um resumo no terminal e opcionalmente exporta pra CSV.

## Instalação

```bash
cd radar-legislativo
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edite o `.env` e escolha um provedor de IA (opcional — veja "Custo" abaixo):

- **Gemini** (tem tier gratuito): crie a chave em [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
  e preencha `GEMINI_API_KEY`.
- **Anthropic (Claude)**: crie a chave em [console.anthropic.com](https://console.anthropic.com/settings/keys)
  e preencha `ANTHROPIC_API_KEY` (se a chave for "identity-linked", também
  precisa de `ANTHROPIC_WORKSPACE_ID` — veja o comentário no `.env.example`).

Sem nenhuma chave configurada, o script funciona normalmente — só usa a
classificação heurística em vez da IA.

Pra ativar a coleta dos EUA (opcional — sem isso, essa fonte é só pulada com
um aviso): cadastro grátis (nome + e-mail, sem cartão) em
[api.congress.gov/sign-up](https://api.congress.gov/sign-up/) e preencha
`CONGRESS_API_KEY`.

## Uso

```bash
python main.py                        # últimos 7 dias, todas as fontes disponíveis
python main.py --dias 15              # janela maior
python main.py --fontes camara,senado # só Brasil, sem tentar os EUA
python main.py --tipos PL,PLP,MPV     # tipos de proposição (só afeta a Câmara)
python main.py --mostrar-todas        # inclui também os marcados como não relevantes
python main.py --export relatorio.csv # exporta o relatório
python main.py --sem-navegador        # não abre o relatório automaticamente
python main.py --sem-ia               # força heurística mesmo com chave de IA (backfill)
```

### Automação (Windows)

Já está configurada uma tarefa no Agendador de Tarefas do Windows chamada
**RadarLegislativoSaudeFarma**, que roda `main.py` todo dia às 18h — depois do
horário típico de sessões/protocolos do dia na Câmara. Pra ver, editar ou
remover:

```bash
schtasks /query /tn "RadarLegislativoSaudeFarma" /v /fo list
schtasks /change /tn "RadarLegislativoSaudeFarma" /st 20:00   # trocar horário
schtasks /delete /tn "RadarLegislativoSaudeFarma" /f          # remover
```

A tarefa só roda quando você está com sessão aberta no Windows (pra poder
abrir o navegador visivelmente) — se o PC estiver desligado ou deslogado no
horário, ela simplesmente não dispara naquele dia (nada é perdido: na próxima
execução, o dedupe por ID busca tudo que ficou pra trás dentro da janela
`--dias`).

## Custo de rodar com IA

Preços oficiais (por 1 milhão de tokens):

| Provedor | Entrada | Saída | Custo por PL classificado |
|---|---|---|---|
| Claude Sonnet 5 | $2,00 | $10,00 | ~$0,004 a $0,012 |
| Gemini 3.6 Flash (promocional até dez/2026) | $0,75 | $3,75 | ~$0,0016 a $0,0045 |

Com o volume real observado (~3 PLs novos de saúde/dia, chegando a ~10-13 em
picos), isso dá **~$0,15 a $3,60 por mês** dependendo do provedor — e o tier
gratuito do Gemini (20 classificações/dia) já cobre a maior parte disso sem
custo nenhum. Rodar o script (inclusive via tarefa agendada) não consome
nenhum crédito da conversa com o Claude Code — as chamadas de IA são feitas
diretamente pelo script Python com as chaves do `.env`, então rodar o
histórico do ano inteiro custa só o que a API de IA cobrar, não "tokens" desta
conversa.

## Preenchendo o histórico (backfill)

Pra processar proposições mais antigas, não só as novas, é só aumentar
`--dias` (a API da Câmara limita consultas a no máximo ~3 meses de diferença
entre as datas, então o cliente já quebra automaticamente janelas maiores em
blocos de até 90 dias). Use `--sem-ia` pra classificar só por heurística
(grátis) num backfill grande, sem gastar cota de IA. Dois números de
referência, já validados: o ano de 2026 (até 01/09) tem **1.055 PLs** no tema
Saúde, dos quais **819 foram marcados relevantes** pela heurística.

Pra rodar a IA em cima de tudo isso depois, os preços acima dão uma estimativa
de **~$2 a $13** pro ano inteiro (1.055 PLs), dependendo do provedor — bem
barato mesmo de uma vez só.

## Painel, países e "Meus salvos"

O relatório publicado tem três páginas, geradas juntas por `src/report.py` e
publicadas juntas por `src/publish.py`:

- **`index.html`** — hub: um card por país (com total de PLs e destaque pro
  mais relevante no momento — hoje, o com mais PLs de impacto alto), mais os
  países pesquisados mas ainda sem coleta implementada, como "em breve" (ver
  [EXPANSAO-INTERNACIONAL.md](EXPANSAO-INTERNACIONAL.md)). Clique num país
  pra abrir o dashboard dele.
- **`pais.html?p=BR`** (ou `?p=US`) — dashboard completo daquele país: KPIs,
  gráficos, busca e filtros (nível, área, órgão, situação). Quando o país tem
  mais de uma casa legislativa (Brasil: Câmara/Senado; EUA: House/Senate),
  aparece também um filtro de casa. Cada card tem uma estrela (☆/★) pra
  marcar como salvo — clicável sem abrir o card.
- **`salvos.html`** — só os PLs marcados, de qualquer país/casa, com os
  mesmos busca/ordenação, mais exportação pra CSV e "Limpar todos".

O "salvo" fica gravado no `localStorage` do navegador, então é por
pessoa/navegador, não por conta — não passa pelo servidor nem pelo banco.

## Limitações atuais / próximos passos

- **EUA**: a listagem do Congress.gov filtra por data de *atualização*, não
  de apresentação original (a API não documenta um filtro pra isso), e não
  tem filtro de tema/assunto na consulta (só no detalhe de cada projeto) —
  então o volume de candidatos avaliados por lá é bem maior que no Brasil.
  Ver [`src/congress_client.py`](src/congress_client.py) pros detalhes.
- **Câmara/Senado não são deduplicados entre si.** Um projeto que tramita nas
  duas casas aparece como dois registros separados (um por casa) — decisão
  deliberada, pra manter câmara e senado sempre visíveis separadamente na
  interface, em vez de tentar (e errar) uma fusão automática.
- **Filtro por tema depende da classificação da própria fonte**, que é ampla.
  É por isso que a heurística/IA reavaliam e podem marcar `relevante=false`
  mesmo dentro de uma busca ampla — mas proposições que a fonte não rotula
  como candidatas não entram na busca.
- **A heurística é grosseira**: detecta presença de termos, não entende
  contexto — pode marcar como relevante algo que não é (falso positivo) com
  mais frequência que a IA. É um piso de qualidade, não um substituto.
- **PDFs escaneados sem camada de texto** não têm o conteúdo extraído (cai de
  volta para a ementa, que geralmente já é suficiente para classificar).
- Outros países pesquisados (Chile, Argentina, Colômbia, Guatemala) ainda não
  têm cliente de coleta — ver [EXPANSAO-INTERNACIONAL.md](EXPANSAO-INTERNACIONAL.md).
- Áreas de interesse (hoje: saúde/farma) estão no prompt de
  [`src/classify.py`](src/classify.py) e nas palavras-chave de
  [`src/heuristic_classify.py`](src/heuristic_classify.py) — para acompanhar
  outro setor, ajuste os dois.

## Estrutura

```
main.py                    orquestra a coleta (multi-fonte), classificação e o relatório
src/paises.py              metadados de país/casa (nome, bandeira) usados na coleta e no painel
src/camara_client.py       chamadas à API da Câmara dos Deputados
src/senado_client.py       chamadas à API do Senado Federal
src/congress_client.py     chamadas à API do Congresso dos EUA (Congress.gov)
src/pdf_extract.py         download e extração de texto do inteiro teor
src/heuristic_classify.py  classificação por palavras-chave, PT e EN (sem IA, sempre roda)
src/classify.py            prompt e chamadas às APIs da Anthropic / Gemini
src/storage.py             persistência em SQLite (multi-país/multi-casa)
src/report.py              geração do painel HTML (hub + dashboard por país + salvos)
src/publish.py             publicação automática no GitHub Pages
```
