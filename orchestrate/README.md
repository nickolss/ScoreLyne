# Agente no watsonx Orchestrate

O **Copiloto de crédito ScoreLyne** ajuda o analista do banco a entender a fila, explicar scores e
simular ofertas. Ele **não decide**: aprovar ou recusar continua sendo uma ação do analista no
painel `/banco`, com justificativa registrada na trilha de auditoria.

```
painel /banco ──▶ banco POST /copiloto ──▶ watsonx Orchestrate (agente analista_scorelyne,
                                            modelo watsonx-orchestrate/frontier)
                                                 │
                       túnel público ◀───────────┘ chama as ferramentas
                            │
                            ▼
                  banco GET /solicitacoes, /modelo, POST /analises
```

Instruções e ferramentas ficam em um só lugar, `backend/src/scorelyne/banco/agente.py`. Os dois
arquivos desta pasta são **gerados** a partir dele (não edite à mão):

| Arquivo | Conteúdo |
|---|---|
| `tools/banco-openapi.json` | as 4 ferramentas em OpenAPI 3.0, apontando para a URL do túnel |
| `agents/analista_scorelyne.yaml` | o agente nativo: instruções, modelo, ferramentas e perguntas iniciais |

| Ferramenta | Endpoint | Para quê |
|---|---|---|
| `listar_solicitacoes` | `GET /solicitacoes` | fila, filtrável por `status=revisao` |
| `obter_solicitacao` | `GET /solicitacoes/{id}` | análise completa e trilha de auditoria |
| `simular_analise` | `POST /analises` | recalcula para outro valor, sem registrar |
| `obter_cartao_modelo` | `GET /modelo` | pesos, limiares, métricas e equidade |

## Pré-requisitos (uma vez)

```bash
uv tool install --python 3.12 ibm-watsonx-orchestrate      # CLI `orchestrate` (ADK da IBM)
# cloudflared: binário em ~/.local/bin (github.com/cloudflare/cloudflared/releases)

orchestrate env add -n hackathon -t ibm_iam \
  -u https://api.ca-tor.watson-orchestrate.cloud.ibm.com/instances/2856de27-d89a-4aec-98c0-309efefe3a45
orchestrate env activate hackathon --api-key "$WATSONX_APIKEY"   # chave do backend/.env
```

`backend/.env` (não versionado) precisa de:

```
WATSONX_APIKEY=<chave de API do IBM Cloud>
ORCHESTRATE_URL=https://api.ca-tor.watson-orchestrate.cloud.ibm.com/instances/2856de27-d89a-4aec-98c0-309efefe3a45
ORCHESTRATE_AGENT_ID=<id em `orchestrate agents list`>
```

Sem `ORCHESTRATE_*`, o copiloto usa o watsonx.ai direto se houver `WATSONX_PROJECT_ID`
(modelo `ibm/granite-4-h-small`); sem nenhum dos dois, o chat aparece desligado no painel.

## A cada demo

O túnel rápido do cloudflared muda de URL toda vez que sobe, então as ferramentas precisam ser
reimportadas com a URL nova:

```bash
# com postgres, operadora e banco no ar (veja backend/README.md)
cloudflared tunnel --url http://localhost:8002             # anote a https://....trycloudflare.com

cd backend
uv run banco orchestrate --url https://<url-do-tunel>      # regenera tools/ e agents/
cd ..
orchestrate tools import -k openapi -f orchestrate/tools/banco-openapi.json
orchestrate agents import -f orchestrate/agents/analista_scorelyne.yaml
```

Teste rápido no terminal: `orchestrate chat ask -n analista_scorelyne -r "Quais solicitações estão em revisão?"`.

A API do banco não tem autenticação: deixe o túnel no ar só durante a demo.

## Modelo

`--llm` escolhe o modelo do agente (padrão `watsonx-orchestrate/frontier`; veja
`orchestrate models list -a`). Testado na instância do hackathon:

- `watsonx-orchestrate/frontier`: usa as ferramentas e segue as instruções (equidade, não decidir).
- `groq/openai/gpt-oss-120b`: funciona.
- `watsonx/ibm/granite-4-h-small`: responde só "I am sorry, I did not understand" nesse agente.

## Roteiro de demo

1. Painel `/banco` → "Quais solicitações estão esperando revisão humana?" → Luciana (601), com o
   alerta de equidade do pré-pago.
2. `/banco/<id da Luciana>` → "Por que a Luciana recebeu essa decisão?" → fator por fator, mais a
   regra de linha com menos de 6 meses.
3. "E se a Luciana pedisse R$ 500?" → simulação sem registro.
4. O analista decide no painel, e a decisão aparece na trilha de auditoria.

Se a operadora reiniciar depois do `banco semear`, os consentimentos (em memória) somem e a
simulação falha com "Consentimento inexistente": rode `uv run banco semear --limpar` de novo.
