# Radar Legislativo — Saúde/Farma

Script que coleta projetos de lei federais recém apresentados na **Câmara dos
Deputados**, sob o tema Saúde, e classifica o impacto de cada um sobre o setor
de saúde/farma (hospitais, planos de saúde, indústria farmacêutica, farmácias,
ANVISA/ANS, pacientes etc.) em duas camadas:

1. **Heurística por palavras-chave** — sempre roda, 100% gratuita, instantânea.
2. **IA** (Anthropic Claude ou Google Gemini) — roda por cima quando há chave
   configurada e refina a classificação da heurística.

Isso significa que o script é útil mesmo sem nenhuma chave de IA, e continua
funcionando (caindo pra heurística) se a IA falhar por rate limit, falta de
crédito ou estar fora do ar.

## Como funciona

1. Consulta a [API de Dados Abertos da Câmara](https://dadosabertos.camara.leg.br/)
   por proposições apresentadas nos últimos N dias, filtradas pelo tema "Saúde".
2. Para cada uma, baixa o inteiro teor (PDF) e extrai o texto.
3. Classifica por palavras-chave (sempre) e, se houver chave de IA configurada,
   também via IA — que retorna resumo em linguagem simples, áreas específicas
   impactadas, tipo de impacto (tributário, regulatório etc.) e nível de
   impacto estimado (alto/médio/baixo), substituindo a heurística.
4. Guarda tudo em um banco SQLite local (`data/radar.db`) para não reprocessar
   a mesma proposição duas vezes.
5. Imprime um relatório no terminal, gera `data/relatorio.html` (visual, abre
   sozinho no navegador) e opcionalmente exporta pra CSV.

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

## Uso

```bash
python main.py                        # últimos 7 dias, tipos PL e PLP
python main.py --dias 15              # janela maior
python main.py --tipos PL,PLP,MPV     # inclui outros tipos de proposição
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

## Limitações atuais / próximos passos

- **Só cobre a Câmara dos Deputados.** O Senado Federal tem uma API de dados
  abertos equivalente ([legis.senado.leg.br/dadosabertos](https://legis.senado.leg.br/dadosabertos))
  mas com estrutura diferente — ainda não implementada aqui. Boa parte das
  proposições relevantes também tramita ou se origina lá.
- **Filtro por tema depende da classificação da própria Câmara**, que é ampla.
  É por isso que a heurística/IA reavaliam e podem marcar `relevante=false`
  mesmo dentro do tema "Saúde" — mas proposições que a Câmara não rotula como
  Saúde não entram na busca. Se notar lacunas, dá pra ampliar a busca por
  palavras-chave na ementa em vez de só por `codTema`.
- **A heurística é grosseira**: detecta presença de termos, não entende
  contexto — pode marcar como relevante algo que não é (falso positivo) com
  mais frequência que a IA. É um piso de qualidade, não um substituto.
- **PDFs escaneados sem camada de texto** não têm o conteúdo extraído (cai de
  volta para a ementa, que geralmente já é suficiente para classificar).
- Áreas de interesse (hoje: saúde/farma) estão no prompt de
  [`src/classify.py`](src/classify.py) e nas palavras-chave de
  [`src/heuristic_classify.py`](src/heuristic_classify.py) — para acompanhar
  outro setor, ajuste os dois e troque o tema buscado em `main.py`
  (`camara_client.find_cod_tema("Saúde")`).

## Estrutura

```
main.py                    orquestra a coleta, classificação e o relatório
src/camara_client.py       chamadas à API da Câmara dos Deputados
src/pdf_extract.py         download e extração de texto do inteiro teor
src/heuristic_classify.py  classificação por palavras-chave (sem IA, sempre roda)
src/classify.py            prompt e chamadas às APIs da Anthropic / Gemini
src/storage.py             persistência em SQLite
src/report.py              geração do relatório HTML
```
