# ScoreLyne: MVP

Documento curto, no espírito do MVP. Responde às perguntas do orientador e guia a apresentação.

## O que o MVP demonstra

Dois módulos separados, cada um com login, banco e segredo próprios:

| | Consumidor | Credor (operador de crédito) |
|---|---|---|
| Quem usa | Quem busca crédito | Analista do banco |
| Faz | Cadastro, consentimento, vê o score, conversa com a IA, envia o pedido | Valida a análise do agente, decide os casos intermediários, usa o copiloto |
| Vê | Só os próprios dados | Só os pedidos que as pessoas decidiram enviar |
| Porta | 8003 | 8002 |

A operadora (8001) é um mock com dados sintéticos. O motor de score é uma biblioteca compartilhada.

## Roteiro da apresentação

1. **Escolher a persona.** Na página inicial, "Sou consumidor" vem primeiro; "Sou operador de crédito" depois. O cabeçalho mostra a persona ativa.
2. **Persona Consumidor: buscar crédito.** Entrar (ou criar conta) com uma pessoa de demonstração, conferir e corrigir os dados, autorizar o consentimento, informar valor e finalidade, ver o score.
3. **IA para o consumidor.** Perguntar ao assistente "por que minha nota ficou assim?". Ele explica fator por fator, sugere como melhorar e simula outro valor. Mostrar as fórmulas em "Como é calculado".
4. **Enviar o pedido ao banco.** O consumidor dá ao banco um consentimento só dele.
5. **Persona Operador de crédito: validar e analisar.** Entrar como analista, abrir o pedido, ver a explicação do agente, perguntar ao copiloto e decidir com justificativa. Ênfase na parte agêntica: o agente calcula, explica e simula; a pessoa decide.
6. **Volta ao consumidor.** A decisão e a justificativa aparecem na tela dele. Mostrar "Revogar": o pedido some do banco e a operadora bloqueia o acesso.

## Registro das fórmulas

As fórmulas do score ficam em `backend/src/scorelyne/score/formulas.yaml`, com versão por fator, pelo modelo e pela política. Cada análise grava a versão do registro e do modelo com que foi calculada. Os testes (`tests/test_formulas.py`) falham se os parâmetros do registro divergirem do código. Está aberto ao público em `/formulas` e na página de governança.

## Modelo de negócio

**Hipótese a validar.** O credor paga por análise (por consulta) ou por assinatura mensal com franquia. O consumidor não paga. Quem tem o dado (a operadora) recebe uma parte pela cessão autorizada.

| | O que entra na conta |
|---|---|
| Receita | Preço por análise cobrado do credor. Fonte alternativa: comissão sobre o crédito concedido |
| Custo variável | Chamadas à IA (watsonx) por conversa e por análise explicada; consulta à operadora; armazenamento |
| Custo fixo | Hospedagem, manutenção do modelo, monitoramento de equidade, jurídico/LGPD |
| Lucro | Receita por análise menos custo variável por análise, menos o custo fixo rateado pelo volume |

**Não temos números reais.** Preço por análise, custo por chamada de IA e volume dependem de cotação do credor e da IBM, e de um piloto. Antes de afirmar lucro, o próximo passo é medir o custo de IA por conversa no uso real e fechar o preço com um credor piloto. O deploy não é obrigatório no MVP, então o custo de hospedagem de produção fica fora desta conta.

## Conflito de interesses: vender score e crédito

**A pergunta.** O que acontece se a mesma entidade vende o score e também empresta?

**Riscos que identificamos** (raciocínio da equipe, não fonte pesquisada):

1. *Viés a favor de si.* Quem empresta e pontua pode ajustar o score para aprovar mais os próprios empréstimos ou negar o concorrente.
2. *Uso de dados além da finalidade.* A pessoa autorizou o score; o dado não pode alimentar oferta de crédito própria sem novo consentimento (LGPD, princípio da finalidade).
3. *Decisão opaca.* Quem é recusado precisa entender o motivo e poder contestar.

**Como o MVP mitiga:**

- A ScoreLyne não empresta: o crédito é do banco parceiro. Este é o desenho que evita o conflito dentro da plataforma.
- Consumidor e credor são módulos separados; o banco só recebe o que a pessoa decide enviar, com consentimento próprio.
- O modelo, os pesos e as fórmulas são públicos e versionados; o monitor de equidade mede aprovação por grupo e calibração.
- Toda decisão tem trilha de auditoria; casos intermediários têm revisão humana, e o consumidor vê a justificativa.
- A operadora fica fora da decisão: só entrega dados autorizados.

**O que ainda é risco:** se a operadora parceira também operar crédito, ela passa a ser o conflito descrito. Isso precisaria de separação societária ou de regras contratuais e auditoria independente do modelo. Não está resolvido no MVP.

**Base legal consultada** (resultado de busca; conferir o texto oficial antes de citar em peça jurídica):

- LGPD, art. 20: direito de pedir revisão de decisões tomadas unicamente por tratamento automatizado, inclusive as que definem perfil de crédito, e de receber informações sobre os critérios, respeitado o segredo comercial. A exigência de revisão por pessoa natural foi retirada pela Lei 13.853/2019, então a revisão humana do MVP é uma escolha de desenho, não uma obrigação direta. Fontes: [Confidata, decisões automatizadas](https://confidata.com.br/blog/decisoes-automatizadas-lgpd-direitos-obrigacoes) e [Migalhas, explicabilidade](https://www.migalhas.com.br/depeso/348841/a-explicabilidade-como-diretriz-para-as-decisoes-automatizadas).
- Lei do Cadastro Positivo (12.414/2011), art. 5º, VII: direito semelhante de revisão de decisões automatizadas de perfil de crédito, que convive com a LGPD. Fonte: [Migalhas, Cadastro Positivo e LGPD](https://www.migalhas.com.br/depeso/298656/a-lei-do-cadastro-positivo-e-a-lei-geral-de-protecao-de-dados-conflito-ou-sinergia).
- **Não encontramos fonte** que trate diretamente de uma empresa que vende score e empresta usando dados de telecom no Brasil. A analogia mais próxima foi a regulação de agências de rating pela CVM, que exige descrever os conflitos potenciais e os procedimentos para minimizá-los. Vale perguntar ao orientador se há referência sugerida.

## Limites conhecidos

- Os dados são sintéticos; o modelo (AUC 0,73) está perto do que os sinais disponíveis permitem: um boosting nos mesmos fatores deu 0,72 e três variáveis novas somaram no máximo 0,006.
- A aprovação automática do pré-pago é menor (regra dos 4/5 falha), mas o modelo está calibrado em todos os planos. Decidir se a regra dos 4/5 prevalece sobre a calibração é uma decisão de produto em aberto.
- O assistente de IA só funciona com credenciais da IBM no `backend/.env`; sem elas ele aparece como desligado.
- Não há deploy: a demo roda local (`docker compose` para o Postgres, ou SQLite). Não usar IBM Cloud para publicação.
