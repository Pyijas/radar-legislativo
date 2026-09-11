# Radar Legislativo — Saúde/Farma

Script que coleta projetos de lei federais recém apresentados em quatro
fontes — **Câmara dos Deputados**, **Senado Federal** (Brasil), o
**Congresso dos EUA** (House + Senate) e o **Congresso Nacional do Chile**
(Cámara de Diputadas y Diputados + Senado) — e classifica o impacto de cada
um sobre o setor de saúde/farma (hospitais, planos de saúde, indústria
farmacêutica, farmácias, ANVISA/ANS/FDA/ISP/Isapres, pacientes etc.) em duas
camadas:

1. **Heurística por palavras-chave** (português, inglês e espanhol) —
   sempre roda, 100% gratuita, instantânea.
2. **IA** (Anthropic Claude ou Google Gemini) — roda por cima quando há chave
   configurada e refina a classificação da heurística.

Isso significa que o script é útil mesmo sem nenhuma chave de IA, e continua
funcionando (caindo pra heurística) se a IA falhar por rate limit, falta de
crédito ou estar fora do ar.

## Como funciona

1. Consulta a [API da Câmara](https://dadosabertos.camara.leg.br/), a
   [API do Senado](https://legis.senado.leg.br/dadosabertos), a
   [API do Congress.gov](https://api.congress.gov/) (EUA, se configurada) e o
   [serviço de tramitação do Congresso do Chile](https://tramitacion.senado.cl/wspublico/)
   por proposições apresentadas/atualizadas nos últimos N dias.
2. Pra Câmara e EUA, busca detalhes extras (inteiro teor / resumo oficial) de
   cada proposição nova; Senado e Chile já devolvem tudo isso na própria
   listagem.
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
- **Ollama** (modelo local, sem chave nem custo por token — veja
  "Classificação local com Ollama" abaixo): defina `LLM_PROVIDER=ollama`.

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
python main.py --fontes camara,senado # só Brasil, sem tentar EUA/Chile
python main.py --fontes chile         # só Chile
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

## Classificação local com Ollama (sem chave, sem custo por token)

Terceira opção além de Claude/Gemini: rodar um modelo aberto localmente via
[Ollama](https://ollama.com/), de graça e offline (só a instalação inicial
precisa de internet, pra baixar o binário e o modelo).

```bash
# 1. Instale o Ollama (https://ollama.com/download) ou baixe só o binário CLI
#    (ollama-darwin.tgz / ollama-linux-*.tgz em github.com/ollama/ollama/releases)
#    se preferir não instalar o app completo.
ollama serve                       # sobe o serviço em localhost:11434 (deixe rodando)
ollama pull qwen2.5:7b-instruct    # baixa o modelo (~4,7 GB, uma vez só)
```

No `.env`, defina:

```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b-instruct   # já é o padrão se omitir
```

A partir daí, `python main.py` classifica pelo modelo local automaticamente
— mesmo prompt, mesmo schema estruturado (JSON forçado via
`ClassificacaoSchema`) que os provedores pagos usam, só que rodando na sua
própria máquina.

**Trade-offs a considerar:**
- **Qualidade**: um modelo de 7-8B parâmetros é bom, mas não tão preciso
  quanto Claude/Gemini em casos ambíguos (ex: distinguir impacto direto vs.
  indireto por demanda induzida — ver discussão no prompt de
  [`src/classify.py`](src/classify.py)). Vale amostrar os resultados de vez
  em quando comparando com uma leitura manual.
- **Velocidade**: bem mais lento que uma API na nuvem (segundos por PL em
  vez de frações de segundo), mas sem rate limit e sem custo por chamada —
  rodar um backfill grande localmente é questão de tempo, não de dinheiro.
- **Hardware**: qwen2.5:7b-instruct roda bem em 16GB de RAM (ex: Apple
  Silicon M1/M2/M3). Modelos maiores (14B+) são mais precisos mas exigem
  mais memória — ver `OLLAMA_MODEL` no `.env.example` pra trocar.
- Se o serviço do Ollama cair no meio de uma execução, o pipeline não
  quebra: `classify.py` levanta `ClassificacaoIndisponivel` e o registro cai
  de volta pra classificação heurística, do mesmo jeito que já acontece com
  falha de rede na API paga.

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
- **`pais.html?p=BR`** (ou `?p=US`, `?p=CL`) — dashboard completo daquele
  país: KPIs, gráficos, busca e filtros (nível, área, órgão, situação).
  Quando o país tem mais de uma casa legislativa (Brasil: Câmara/Senado;
  EUA: House/Senate; Chile: Cámara/Senado), aparece também um filtro de
  casa. Cada card tem uma estrela (☆/★) pra marcar como salvo — clicável
  sem abrir o card.
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
  **Precisa de `CONGRESS_API_KEY`** (grátis, ver "Instalação" acima) — sem
  ela essa fonte é só pulada com um aviso; ainda não teve uma primeira
  coleta rodada (aparece "Aguardando primeira coleta…" no painel até isso
  acontecer).
- **Chile**: o serviço de tramitação do Congresso não aceita consultar mais
  de ~1 mês pra trás (`--dias` é limitado automaticamente a esse teto pra
  essa fonte), então não dá pra fazer um backfill de histórico grande igual
  se faz com Brasil/EUA — só acompanhamento do que vem daqui pra frente. O
  documento original do projeto (mensagem/moção) costuma vir em `.doc`, não
  PDF, então a classificação usa o título do projeto na maioria dos casos
  (sem inteiro teor). Não precisa de chave/cadastro. Ver
  [`src/chile_client.py`](src/chile_client.py) pros detalhes.
- **Câmara/Senado (Brasil e EUA) não são deduplicados entre si.** Um projeto
  que tramita nas duas casas aparece como dois registros separados (um por
  casa) — decisão deliberada, pra manter câmara e senado sempre visíveis
  separadamente na interface, em vez de tentar (e errar) uma fusão
  automática. **Chile é diferente**: como a fonte já acompanha o projeto ao
  longo de toda a tramitação bicameral, ele aparece uma vez só, na casa
  onde está atualmente.
- **Filtro por tema depende da classificação da própria fonte**, que é ampla
  (Brasil e EUA) ou inexistente (Chile, onde a fonte não filtra por tema
  algum). É por isso que a heurística/IA reavaliam e podem marcar
  `relevante=false` mesmo dentro de uma busca ampla — mas proposições que a
  fonte não rotula como candidatas (Brasil/EUA) não entram na busca.
- **A heurística é grosseira**: detecta presença de termos, não entende
  contexto — pode marcar como relevante algo que não é (falso positivo) com
  mais frequência que a IA. É um piso de qualidade, não um substituto.
- **PDFs escaneados sem camada de texto** (ou documentos em formato não-PDF,
  caso do Chile) não têm o conteúdo extraído (cai de volta para a ementa/
  título, que geralmente já é suficiente para classificar).
- Outros países pesquisados (Argentina, Colômbia, Guatemala) ainda não têm
  cliente de coleta — ver [EXPANSAO-INTERNACIONAL.md](EXPANSAO-INTERNACIONAL.md).
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
src/chile_client.py        chamadas ao serviço de tramitação do Congresso do Chile
src/pdf_extract.py         download e extração de texto do inteiro teor
src/heuristic_classify.py  classificação por palavras-chave, PT/EN/ES (sem IA, sempre roda)
src/classify.py            prompt e chamadas às APIs da Anthropic / Gemini
src/storage.py             persistência em SQLite (multi-país/multi-casa)
src/report.py              geração do painel HTML (hub + dashboard por país + salvos)
src/publish.py             publicação automática no GitHub Pages
```
