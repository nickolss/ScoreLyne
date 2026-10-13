# ScoreLyne — Backend

Dois serviços e um banco de dados:

- **Operadora mock** (`scorelyne.operadora`, porta 8001): base sintética de linhas telefônicas e
  uma API que só libera os dados de uma linha mediante consentimento do titular.
- **Banco** (`scorelyne.banco`, porta 8002): recebe as solicitações de crédito, busca os dados
  autorizados na operadora, roda o motor de score (`scorelyne.score`), guarda a decisão e a
  trilha de auditoria no PostgreSQL e recebe a revisão humana.
- **PostgreSQL** via `docker-compose.yml` na raiz do repositório.

## Rodando a demo completa

```bash
docker compose up -d                 # na raiz: PostgreSQL na porta 5432
cd backend && uv sync
uv run operadora servir              # terminal 1 · http://localhost:8001/docs
uv run banco servir                  # terminal 2 · http://localhost:8002/docs
uv run banco semear --limpar         # cria as solicitações das 5 personas
cd ../frontend && npm run dev        # terminal 3 · http://localhost:3000
```

A operadora guarda os consentimentos em memória. Se ela reiniciar, rode `banco semear --limpar`
de novo para as solicitações apontarem para consentimentos válidos.

Outros comandos: `uv run score treinar` (retreina e grava `src/scorelyne/score/modelo.json`),
`uv run operadora exportar` (CSVs da base sintética em `data/`), `uv run pytest`.

Variáveis: `OPERADORA_POPULACAO` (3000), `OPERADORA_SEMENTE` (42), `OPERADORA_DEMO` (1 liga
`/demo/*`), `OPERADORA_URL` (onde o banco acha a operadora), `BANCO_DB_URL`
(`postgresql+psycopg://scorelyne:scorelyne@localhost:5432/scorelyne`), `OPERADORA_CORS` e
`BANCO_CORS` (`http://localhost:3000`). No frontend: `NEXT_PUBLIC_OPERADORA_URL` e
`NEXT_PUBLIC_BANCO_URL`.

## API do banco

```
POST   /solicitacoes                    { nome, telefone, consentimento_id, valor_solicitado, finalidade, ... }
GET    /solicitacoes[?status=revisao]   fila
GET    /solicitacoes/{id}               análise completa + trilha de auditoria
POST   /solicitacoes/{id}/decisao       { veredito: aprovar|recusar, justificativa (mín. 10) }
DELETE /solicitacoes/{id}/decisao       desfaz a decisão do analista
POST   /solicitacoes/{id}/revogar       revoga na operadora e apaga score e análise
POST   /analises                        análise avulsa, sem registrar (ferramenta do agente)
GET    /modelo                          cartão do modelo: importâncias, métricas, equidade,
                                        perda máxima de pontos ao omitir cada fator
```

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
