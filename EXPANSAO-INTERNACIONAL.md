# Expansão internacional — opções por país

Pesquisa de viabilidade pra replicar o Radar Legislativo (coleta + IA +
painel) em outros países. Ordenado do mais fácil pro mais difícil de
implementar, com base na qualidade dos dados abertos disponíveis.

## Resumo executivo

| País | Fonte | Formato | Nível de esforço | Recomendação |
|---|---|---|---|---|
| 🇧🇷 Senado Federal | `legis.senado.leg.br/dadosabertos` | REST/JSON, oficial | Baixo — já comecei (`src/senado_client.py`) | **Fazer primeiro** |
| 🇺🇸 EUA | `api.congress.gov` | REST/JSON, oficial, chave grátis | Baixo | **Melhor 2ª opção** |
| 🇨🇱 Chile | `opendata.congreso.cl` + BCN (`datos.bcn.cl`) | XML / dados ligados (RDF) | Médio | Viável, mais trabalho de adaptação |
| 🇦🇷 Argentina | `datos.hcdn.gob.ar` (Câmara) + Senado | Portal CKAN, formato a confirmar | Médio | Viável, precisa validar API na prática |
| 🇨🇴 Colômbia | `datos.gov.co` (dataset "Proyectos de Ley") | Socrata (API SODA — REST/JSON) | Médio | Viável via Socrata, mas dataset pode não estar 100% atualizado |
| 🇬🇹 Guatemala | Nenhuma API encontrada | PDFs no site do Congresso | Alto | Não recomendo agora — exigiria scraping frágil |

## Por que essa ordem

**O critério que mais pesa aqui não é "o país é importante", é "os dados são
abertos e estruturados"** — é isso que determina se dá pra construir uma
versão confiável e barata (como fizemos com a Câmara) ou se vira um projeto
de scraping caro e frágil, que quebra toda vez que o site muda o HTML.

### 🇧🇷 Senado Federal — comece por aqui

Mesma língua, mesmo time, e o Senado tem uma API de dados abertos tão boa
quanto (ou melhor que) a da Câmara: `https://legis.senado.leg.br/dadosabertos/processo`
retorna matérias em JSON limpo, com ementa, situação atual, data da última
atualização e link do documento. **Já testei e confirmei que funciona** —
comecei um cliente em [`src/senado_client.py`](src/senado_client.py), com
uma função `listar_novas_materias()` funcionando de verdade. Falta:

1. Descobrir como filtrar por tema (Saúde) nesse endpoint — o parâmetro
   `assunto=` que testei não filtrou corretamente.
2. Mapear os campos de tramitação pro mesmo formato que já uso na Câmara.
3. Decidir como evitar duplicar um PL que tramita nas duas casas.
4. Integrar no `main.py` como uma segunda fonte, unificada no mesmo banco.

Isso é o caminho de menor esforço pra "dobrar" a cobertura do projeto atual,
porque muita legislação de saúde relevante nasce ou passa pelo Senado.

### 🇺🇸 Estados Unidos — melhor opção fora do Brasil

O Congress.gov tem uma API oficial mantida pela Library of Congress/GPO
(`api.congress.gov`), com chave de acesso gratuita (cadastro simples em
[api.congress.gov/sign-up](https://www.congress.gov/help/using-data-offsite)),
documentação completa, e cobre bills, status, patrocinadores, comitês e
texto integral. É provavelmente **mais fácil de integrar do que a própria
Câmara dos Deputados** — API mais madura e melhor documentada. Existe até
um projeto open-source de referência
([unitedstates/congress](https://github.com/unitedstates/congress)) com
anos de uso.

Ponto de atenção: "saúde" nos EUA é um mercado gigantesco e mais fragmentado
(federal + 50 estados) — pra manter escopo parecido ao do Brasil, eu
recomendaria começar só no nível federal (Congress), do jeito que fizemos
aqui.

### 🇨🇱 Chile — dados abertos de verdade, só que em outro formato

A Biblioteca del Congreso Nacional (BCN) do Chile é **citada internacionalmente
como referência em dados legislativos abertos** — eles têm até uma ontologia
de dados ligados (linked data / RDF) sobre leis e proposições
([datos.bcn.cl](https://datos.bcn.cl/es/)), além de um portal dedicado
(`opendata.congreso.cl`) e serviços web em XML tanto da Câmara quanto do
Senado. A cobertura é ótima; o trabalho extra é que o formato (XML/RDF) dá
mais trabalho de adaptação do que o JSON limpo que temos hoje.

### 🇦🇷 Argentina — promissor, precisa validar na prática

A Câmara de Deputados (HCDN) mantém um portal de dados abertos em
`datos.hcdn.gob.ar`, construído sobre CKAN (a mesma plataforma usada por
muitos governos, incluindo partes do próprio governo brasileiro) — isso
normalmente significa uma API REST padronizada disponível. O Senado também
tem uma seção de dados abertos separada. Não consegui confirmar com certeza
o formato exato de resposta via pesquisa (o fetch direto não trouxe
detalhes técnicos suficientes) — o próximo passo seria testar a API na mão,
igual fiz com o Senado brasileiro.

### 🇨🇴 Colômbia — via portal nacional de dados abertos

Não existe uma API dedicada do Congresso colombiano, mas o dataset
"Proyectos de Ley" está publicado no portal oficial `datos.gov.co`, que roda
sobre a plataforma **Socrata** — isso é uma boa notícia, porque Socrata tem
uma API REST bem documentada e padronizada (SODA API) usada por dezenas de
governos ao redor do mundo. O dataset específico é mantido pela Cámara de
Representantes; vale checar a frequência de atualização antes de depender
dele pra algo "quase em tempo real" como fizemos aqui. Existe também o
[Congreso Visible](https://congresovisible.uniandes.edu.co/) (projeto
acadêmico da Universidad de los Andes) como fonte complementar de contexto,
mas não parece ter uma API pública própria.

### 🇬🇹 Guatemala — não recomendo por agora

Não encontrei nenhuma API ou portal de dados abertos do Congreso guatemalteco.
As iniciativas de lei são publicadas como PDFs individuais no site
institucional (`congreso.gob.gt/seccion_informacion_legislativa/iniciativas`).
Dá pra fazer, mas seria via scraping de HTML + leitura de PDF pra cada
iniciativa — mais caro de construir, mais frágil de manter (quebra toda vez
que o site redesenha), e sem garantia de estrutura de dados consistente.
Interessante notar que o próprio Congresso guatemalteco está discutindo uma
"Lei de Interoperabilidade do Governo Digital" que menciona dados abertos —
vale reavaliar esse país daqui a uns anos, se isso avançar.

## Como eu abordaria cada implementação

O padrão que funcionou aqui (e que eu repetiria) é: **cliente da fonte
oficial → heurística por palavra-chave em português/espanhol/inglês →
classificação por IA em cima → mesmo painel HTML**. A arquitetura do projeto
atual (`src/camara_client.py`, `src/heuristic_classify.py`,
`src/classify.py`, `src/storage.py`, `src/report.py`) já é bem desacoplada
— trocar a fonte de dados não deveria exigir reescrever classificação nem
painel, só um novo `_client.py` por país + ajuste de idioma no prompt da IA
e nas palavras-chave da heurística.

Se for tocar mais de um país, minha sugestão é manter **um projeto por
país** (ou um banco separado por país dentro do mesmo projeto) em vez de
misturar tudo numa base só — os esquemas de tramitação são diferentes o
suficiente (nomes de órgãos, tipos de proposição, idioma) que forçar um
schema único desde o início provavelmente vai gerar mais retrabalho do que
economizar.
