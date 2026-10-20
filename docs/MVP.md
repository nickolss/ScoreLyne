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

**Hipótese a validar.** O credor paga por análise (ou assinatura mensal com franquia). O consumidor não paga. Quem tem o dado (a operadora) recebe pela cessão autorizada. Não recomendamos cobrar comissão sobre o crédito concedido: ela faz a plataforma lucrar quando o banco aprova, e isso agrava o conflito de interesses descrito abaixo.

| | O que entra na conta |
|---|---|
| Receita | Preço por análise cobrado do credor |
| Custo variável | IA por conversa; taxa pela cessão do dado à operadora (valor desconhecido); armazenamento |
| Custo fixo | Plano do Orchestrate, se usado; hospedagem; manutenção do modelo; monitoramento de equidade; jurídico e LGPD |
| Lucro | (preço por análise menos custo variável por análise) vezes o volume, menos o custo fixo |

### O que conseguimos medir ou pesquisar

**Custo da IA por conversa: desprezível.** Medimos no código o tamanho dos textos enviados ao modelo: instruções, cerca de 600 tokens; definição das ferramentas, cerca de 460; análise do score, cerca de 640; fórmulas, cerca de 1.150 (estimativa de 3,5 caracteres por token). Uma pergunta com duas ou três chamadas ao modelo soma cerca de 6.000 tokens de entrada e 620 de saída. Com o preço público do `ibm/granite-4-h-small` na IBM, **US$ 0,06 por milhão de tokens de entrada e US$ 0,25 por milhão de saída** ([IBM watsonx.ai pricing](https://www.ibm.com/watsonx/pricing), valores indicativos), isso dá **cerca de US$ 0,0005 por pergunta**. Uma sessão de cinco perguntas fica abaixo de US$ 0,01. O copiloto do analista envia mais dados, mas a ordem de grandeza é a mesma.

**O custo fixo relevante é o plano do Orchestrate.** A IBM lista o watsonx Orchestrate a partir de **US$ 530 por mês (Essentials)** e **US$ 6.360 por mês (Standard)**, com 30 dias de teste ([páginas de preço da IBM](https://www.ibm.com/ae-ar/products/watson-orchestrate/pricing); uma listagem de terceiros mostra outros valores e está desatualizada, então confirme com a IBM). Usando o watsonx.ai direto, sem Orchestrate, o custo fixo de IA é zero e só se paga por token.

**Ponto de equilíbrio do Orchestrate Essentials**, só para cobrir esse plano e sem contar o custo do dado. Hipótese de câmbio: US$ 1 = R$ 5,50 (atualize), então US$ 530 são cerca de R$ 2.915 por mês. Os preços por análise abaixo são hipóteses, não cotações:

| Preço por análise (hipótese) | Análises por mês para cobrir o plano |
|---|---|
| R$ 1,00 | cerca de 2.945 |
| R$ 2,00 | cerca de 1.465 |
| R$ 5,00 | cerca de 585 |

A conta é `plano ÷ (preço − custo variável)`. Se a cessão do dado consumir parte do preço, o volume necessário sobe.

### O que não conseguimos descobrir

- **Preço de score por consulta no Brasil.** Buscamos tabelas de Serasa, Boa Vista e Quod e **não encontramos preço B2B público**: o acesso é por contrato, e o que aparece na internet é só consulta gratuita para o consumidor. O número real exige cotação comercial com cada bureau ou com um intermediário que revenda as consultas.
- **Quanto a operadora cobraria pela cessão do dado.** Não existe referência pública.
- **Volume esperado e custos fixos de hospedagem e equipe.**

**Próximos passos para fechar a conta:** pedir cotação a um bureau e a uma operadora; fechar um preço com um credor piloto; decidir se o Orchestrate vale o plano fixo ou se o watsonx.ai direto basta no MVP. Sem isso, qualquer número de lucro seria inventado. O deploy não é obrigatório no MVP, então o custo de hospedagem de produção fica fora desta conta.

## Conflito de interesses: a plataforma que detém os dados, serve o banco e atende o cliente

**A situação.** A plataforma guarda ou intermedeia os dados da pessoa, entrega o score ao banco (que paga) e, do outro lado, conversa com o próprio consumidor (que usa de graça). Ela serve os dois lados e só um deles paga.

### Os conflitos

1. **Neutralidade comprada.** Quem aparece como árbitro neutro para o consumidor, mas é pago por quem concede o crédito, pode orientar a pessoa para quem paga. O exemplo clássico é o Credit Karma, cuja receita depende de comissões pagas por credores quando o usuário aceita uma oferta ([ProductMint](https://productmint.com/the-credit-karma-business-model-how-does-credit-karma-make-money/)). O regulador americano (CFPB) tratou disso em parecer de 2023 sobre plataformas de comparação de crédito imobiliário: há infração quando a plataforma apresenta os credores de forma não neutra, isso direciona o consumidor e ela é paga, ao menos em parte, por esse direcionamento; listar por taxa, do menor ao maior, é apresentação neutra ([parecer do CFPB](https://files.consumerfinance.gov/f/documents/cfpb_respa-advisory-opinion-on-online-mortgage-comparison-shopping-tools_2023-02.pdf); [resumo](https://www.consumerfinance.gov/archive/newsroom/cfpb-issues-guidance-to-protect-mortgage-borrowers-from-pay-to-play-digital-comparison-shopping-platforms/)). É uma regra americana sobre crédito imobiliário, e não confirmamos se o parecer segue em vigor; não achamos ação do CFPB contra o Credit Karma.
2. **Dado usado em mais de um lado sem o conhecimento do titular.** No Brasil, em 2020, um desembargador do TJDFT suspendeu produtos da Serasa ("Lista Online" e "Prospecção de Clientes") após ação do Ministério Público do DF, que alegava venda de dados a empresas interessadas em prospectar clientes sem conhecimento dos titulares ([Olhar Digital](https://olhardigital.com.br/noticia/voce-sabia-que-a-serasa-vende-seus-dados/89065); [Bem Paraná](https://www.bemparana.com.br/noticia/desembargador-suspende-produtos-da-serasa-por-venda-de-dados-sem-autorizacao-664)). A Serasa sustenta que cumpre os critérios legais, e não achamos a situação atual do processo. O ponto para nós é o risco de desvio de finalidade quando o dono do dado o monetiza com várias partes.
3. **Desvio de finalidade no compartilhamento de dados financeiros.** No Open Finance, a regra gira em torno do consentimento do titular e da vedação ao desvio de finalidade, e houve proposta do Banco Central de criar a figura da instituição integradora e de tratar contratos com empresas não reguladas como parceria ([Finsiders Brasil](https://finsidersbrasil.com.br/?p=363002)). Não confirmamos se essa proposta foi aprovada; a norma em vigor deve ser conferida no site do Banco Central.
4. **Decisão que a pessoa não consegue entender nem contestar.** A LGPD (art. 20) dá direito de pedir revisão de decisões automatizadas, inclusive de perfil de crédito, e de receber os critérios usados, respeitado o segredo comercial; a Lei do Cadastro Positivo (art. 5º, VII) traz direito semelhante ([Confidata](https://confidata.com.br/blog/decisoes-automatizadas-lgpd-direitos-obrigacoes); [Migalhas](https://www.migalhas.com.br/depeso/298656/a-lei-do-cadastro-positivo-e-a-lei-geral-de-protecao-de-dados-conflito-ou-sinergia)).
5. **Quem avalia é pago por quem é avaliado.** A CVM, ao propor regras para agências de rating, pediu que elas descrevam os conflitos potenciais e os procedimentos para minimizá-los. É uma analogia, não uma regra para score de pessoa física.

**Não achamos fonte que trate exatamente do caso "plataforma de score com dados de telecom, paga pelo banco, atendendo o cliente".** Os pontos acima são os mais próximos; a aplicação ao nosso caso é raciocínio da equipe.

### Onde o ScoreLyne está exposto

- **O banco paga por análise e a tela do consumidor tem o botão "Enviar pedido ao banco".** Se a receita cresce com os pedidos enviados, a plataforma tem motivo para empurrar o consumidor ao banco, e hoje só existe um banco parceiro, sem comparação. É o conflito 1 em pequeno.
- **O assistente do consumidor é pago, indiretamente, pelo banco.** Ele poderia explicar a nota de forma mais favorável a quem aprova do que a quem pede.
- **A mesma base alimenta o score do consumidor e a análise do banco.** Sem a separação por consentimento, isso viraria o conflito 2.
- **A tela não conta ao consumidor como a plataforma ganha dinheiro.** Hoje isso não está dito.

### O que o MVP já faz

- A ScoreLyne não empresta: o crédito é do banco parceiro.
- Consumidor e credor são módulos separados; o banco só recebe o pedido que a pessoa decide enviar, com um consentimento próprio, e a revogação apaga a análise no banco.
- As fórmulas, os pesos e a equidade são públicos e versionados, e toda decisão tem trilha de auditoria.
- O assistente não promete aprovação, só enxerga os dados de quem está logado e orienta a pedir revisão humana.
- Casos intermediários vão para um analista, e o consumidor vê a justificativa.
- A tela de consentimento e a caixa de envio do pedido mostram ao consumidor como a plataforma ganha dinheiro: ele não paga, o banco paga um valor fixo por análise, não há comissão por crédito aprovado e nenhum banco é destacado por pagar mais. O texto descreve o modelo que pretendemos adotar; se o modelo mudar, a tela precisa mudar junto.

### O que recomendamos e ainda não está feito

1. **Cobrar por análise, nunca por crédito concedido ou aprovado**, para a plataforma não ganhar com a decisão.
2. **Não ranquear nem destacar credores por quanto pagam.** Se houver mais de um banco, mostrar os critérios de ordenação.
3. **Auditoria independente do modelo** e publicação periódica do monitor de equidade.
4. **Separação societária ou contratual** se a operadora parceira também operar crédito: ela passaria a ser, ao mesmo tempo, dona do dado e concorrente de quem empresta.

## Limites conhecidos

- Os dados são sintéticos; o modelo (AUC 0,73) está perto do que os sinais disponíveis permitem: um boosting nos mesmos fatores deu 0,72 e três variáveis novas somaram no máximo 0,006.
- A aprovação automática do pré-pago é menor (regra dos 4/5 falha), mas o modelo está calibrado em todos os planos. Decidir se a regra dos 4/5 prevalece sobre a calibração é uma decisão de produto em aberto.
- O assistente de IA só funciona com credenciais da IBM no `backend/.env`; sem elas ele aparece como desligado.
- Não há deploy: a demo roda local (`docker compose` para o Postgres, ou SQLite). Não usar IBM Cloud para publicação.
