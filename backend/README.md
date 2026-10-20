# ScoreLyne — Backend

Três serviços e um banco de dados. O consumidor e o credor são módulos separados, cada um com
login, segredo JWT e tabelas próprias: um token de um lado não vale no outro.

- **Operadora mock** (`scorelyne.operadora`, porta 8001): base sintética de linhas telefônicas e
  uma API que só libera os dados de uma linha mediante consentimento do titular.
- **Consumidor** (`scorelyne.consumidor`, porta 8003): cadastro e login da pessoa, consentimento,
  cálculo do próprio score, assistente com IA que explica a nota e o envio do pedido ao credor.
- **Credor** (`scorelyne.banco`, porta 8002): login do analista, fila de solicitações, revisão
  humana, cartão do modelo e copiloto do analista.
- **Motor de score** (`scorelyne.score`) e peças compartilhadas (`scorelyne.comum`): o motor é uma
  biblioteca sem dependência de API; `comum` guarda só o que cruza a fronteira entre os módulos.
- **PostgreSQL** via `docker-compose.yml` na raiz do repositório.

## Rodando a demo completa

```bash
docker compose up -d                 # na raiz: PostgreSQL na porta 5432
cd backend && uv sync
uv run operadora servir              # terminal 1 · http://localhost:8001/docs
uv run banco servir                  # terminal 2 · http://localhost:8002/docs  (credor)
uv run consumidor servir             # terminal 3 · http://localhost:8003/docs
uv run consumidor semear             # cadastra as 5 personas como consumidores (senha scorelyne123)
uv run banco semear --limpar         # cria o analista (analista@scorelyne.demo) e 5 solicitações
cd ../frontend && npm run dev        # terminal 4 · http://localhost:3000
```

Sem Docker, aponte os bancos para SQLite: `BANCO_DB_URL=sqlite:///credor.db` e
`CONSUMIDOR_DB_URL=sqlite:///consumidor.db`.

As chaves entre os serviços (defina as mesmas nos dois lados em qualquer ambiente real):
`CREDOR_SERVICE_KEY` (o consumidor cria e revoga solicitações no credor), `CREDOR_AGENT_KEY` (o
agente do Orchestrate só lê e simula) e um segredo JWT por módulo, `CREDOR_JWT_SECRET` e
`CONSUMIDOR_JWT_SECRET`. Sem segredo JWT, cada processo sorteia um e os logins caem ao reiniciar.

A operadora guarda os consentimentos em memória. Se ela reiniciar, rode `consumidor semear` e
`banco semear --limpar` de novo para tudo apontar para consentimentos válidos.

Outros comandos: `uv run banco orchestrate --url <túnel>` e `uv run consumidor orchestrate` (geram os
agentes do watsonx Orchestrate em `../orchestrate/`), `uv run score treinar` (retreina, grava
`src/scorelyne/score/modelo.json` e uma cópia em `score/versoes/`), `uv run operadora exportar`
(CSVs da base sintética em `data/`), `uv run pytest`.

Variáveis: `OPERADORA_POPULACAO` (3000), `OPERADORA_SEMENTE` (42), `OPERADORA_DEMO` (1 liga
`/demo/*`), `OPERADORA_URL` (onde os módulos acham a operadora), `CREDOR_URL` (onde o consumidor
acha o credor), `BANCO_DB_URL` e `CONSUMIDOR_DB_URL`
(`postgresql+psycopg://scorelyne:scorelyne@localhost:5432/scorelyne`), `OPERADORA_CORS`,
`BANCO_CORS` e `CONSUMIDOR_CORS` (`http://localhost:3000`). IA: `WATSONX_APIKEY`,
`WATSONX_PROJECT_ID`, `ORCHESTRATE_URL`, `ORCHESTRATE_AGENT_ID` (analista) e
`ORCHESTRATE_CONSUMIDOR_AGENT_ID` (consumidor). O frontend chama os módulos pelo próprio servidor
Next, com o token num cookie httpOnly: `CONSUMIDOR_URL`, `CREDOR_URL` e `OPERADORA_URL` (padrões nas
portas acima), sem variáveis `NEXT_PUBLIC_*`.

## API do consumidor

```
POST   /cadastro                        { nome, cpf, telefone, senha (mín. 8), ocupacao, cidade, uf }
POST   /login                           { cpf, senha } -> token (papel consumidor, 60 min)
GET    /me                              dados da própria pessoa
PATCH  /meus-dados                      corrige telefone, ocupação, cidade, uf (trocar o telefone revoga tudo)
POST   /consentimentos                  { escopos } autoriza a ScoreLyne a ler a operadora
POST   /meu-score                       { valor_solicitado, finalidade } calcula e guarda
GET    /meu-score                       nota, fatores, pontos fortes e de atenção, plano de melhora
POST   /enviar-ao-credor                dá ao credor um consentimento só dele e envia o pedido
GET    /minha-solicitacao               situação: decisão, justificativa do analista, oferta
POST   /retirar-do-credor               desfaz só o envio (o score continua)
POST   /revogar                         revoga tudo e apaga o score guardado
GET    /assistente · POST /assistente   chat com a IA sobre a própria nota (só enxerga os dados de quem está logado)
GET    /formulas · GET /modelo          públicos: registro versionado das fórmulas e cartão do modelo
```

O assistente nunca recebe identificador de cliente: as ferramentas rodam no servidor sobre o cliente
do token (watsonx.ai), ou o servidor injeta só a análise da própria pessoa na conversa (Orchestrate).

## API do credor

Tudo exige login de analista, a chave de agente (só leitura e simulação) ou a chave de serviço.
`/saude`, `/login`, `/modelo` e `/formulas` são públicos.

```
POST   /login                           { email, senha } -> token do analista
POST   /solicitacoes                    (chave de serviço) { nome, telefone, consentimento_id, valor_solicitado, finalidade, ... }
GET    /solicitacoes[?status=revisao]   fila
GET    /solicitacoes/{id}               análise completa + trilha de auditoria
POST   /solicitacoes/{id}/decisao       { veredito: aprovar|recusar, justificativa (mín. 10) }; quem decidiu vem do login
DELETE /solicitacoes/{id}/decisao       desfaz a decisão do analista
GET    /solicitacoes/{id}/situacao      (chave de serviço) o que o consumidor pode ver do próprio pedido
POST   /solicitacoes/{id}/revogar       (chave de serviço) revoga na operadora e apaga score e análise
POST   /analises                        análise avulsa, sem registrar (ferramenta do agente)
GET    /modelo                          cartão do modelo: importâncias, métricas, equidade,
                                        perda máxima de pontos ao omitir cada fator
GET    /copiloto                        copiloto ligado? provedor, modelo e perguntas iniciais
POST   /copiloto                        { mensagens: [{ papel: analista|copiloto, texto }] }
```

O copiloto do analista conversa com o agente do watsonx Orchestrate (ou com um modelo do
watsonx.ai) usando as credenciais do `backend/.env`, que o `banco servir` carrega sozinho. Como
configurar e publicar o agente: `../orchestrate/README.md`.

A trilha de auditoria só cresce: consentimento, dados recebidos, score, checagem de variáveis,
decisão do agente e cada ação do analista ou do cliente.

## Os dados

A data de referência é fixa em **28/09/2026**, então a base é sempre a mesma para a mesma semente.

- **Personas da demo** (`personas.py`): Maria, João, Ana, Carlos e Luciana, montados à mão para
  bater com as telas do frontend (ex.: Maria tem 71 recargas em 74 meses; Carlos tem 6 atrasos
  acima de 15 dias nas últimas 12 faturas e 2 suspensões).
- **População** (`generator.py`): cada linha nasce de três traços ocultos (disciplina,
  volatilidade, mobilidade) que geram os eventos brutos: recargas, faturas, saldos zerados,
  suspensões (atraso acima de 30 dias), trocas de chip, portabilidade e migração pré → controle.
- **Rótulo de inadimplência**: sorteado a partir dos mesmos traços (cerca de 20% da base). Só
  aparece no `exportar` (`rotulos.csv`), nunca na API. Ele simula o resultado do crédito que
  o banco observaria depois e serve para treinar o modelo.

## Fluxo da API

```
POST   /consentimentos              { telefone, cpf, escopos[], finalidade, solicitante }
GET    /linhas/{telefone}/dados     cabeçalho X-Consentimento-Id
GET    /consentimentos/{id}         consentimento + trilha de cada acesso
DELETE /consentimentos/{id}         revoga; acessos seguintes recebem 403
GET    /demo/personas               telefones e CPFs das personas
```

Os escopos são os mesmos fatores da tela de consentimento do cliente, e a resposta só traz os
blocos autorizados:

| Escopo | O que a operadora entrega |
|---|---|
| `permanencia` | data de ativação, meses na base, plano atual, histórico de planos |
| `recargas` | só as datas das recargas |
| `pontualidade` | vencimento e pagamento das faturas, saldos zerados, suspensões |
| `estabilidade` | trocas de chip, portabilidade de entrada |
| `consistencia` | totais mensais agregados (recargas e fatura), sem transações individuais |

Nome, CPF, cidade e UF nunca saem pela API de dados. O CPF só é usado para conferir que quem
consente é o titular.

## Motor de score

**Fatores** (`fatores.py`): calculados só a partir da resposta da operadora, numa janela de 24
meses. Cada fator sai em 0–100 com a evidência em texto e uma dica de melhora.

**Modelo** (`modelo.py`, `treino.py`): regressão logística sobre os fatores, treinada na base
sintética. Como o modelo é linear, os pontos de cada fator são exatos e somam o score
(`pontos_base + Σ pontos = score`), equivalente ao SHAP. Restrições:

- *monotônico*: nenhum fator pode aumentar o score quando piora. Fator com sinal invertido sai
  do modelo (hoje é o caso de estabilidade: troca de chip não teve poder preditivo);
- *escala ligada ao risco*: 750 pontos = 10% de probabilidade de inadimplência, 550 = 25%.

Resultado atual no conjunto de teste: AUC 0,73, KS 0,38. Aprovação automática de 41% dos
pedidos, com 7% de inadimplência; 43% vão para revisão; 17% são recusados, com 39% de inadimplência.

**Política** (`politica.py`):

| Regra | Por quê |
|---|---|
| Score ≥ 750 aprova, 550–749 vai para analista, < 550 recusa | supervisão humana na faixa incerta |
| Menos de 6 meses de linha ou menos de 3 fatores → sempre analista | o agente não decide sozinho com pouco dado |
| `permanencia`, `recargas` e `pontualidade` são obrigatórios | se fossem opcionais, quem tem histórico ruim ganharia pontos omitindo |
| Fator opcional não autorizado entra com o pior valor da base | omitir dado nunca aumenta o score (verificado em teste) |
| Oferta nunca passa do valor pedido; taxa cai com o score | |

**Equidade**: o treino mede a aprovação automática por região e por plano (regra dos 4/5) e a
inadimplência entre os aprovados de cada grupo. Região passa (razão 0,89). **Plano não passa**:
o pré-pago tem 31% de aprovação automática contra cerca de 50% do controle e do pós-pago, com a
mesma inadimplência entre os aprovados (6%). A diferença vem da informação disponível: pagar
uma fatura em dia diz mais sobre disciplina do que recarregar no mês, então o modelo identifica
o pós-pago de baixo risco com mais segurança. Fechar essa diferença é uma decisão de produto,
ainda em aberto.
