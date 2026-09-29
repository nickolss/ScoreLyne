# ScoreLyne

> **Credit scoring alternativo baseado em padrões de uso de telecomunicações**

## Sobre o Projeto

ScoreLyne é uma plataforma de **credit scoring alternativo** que utiliza dados comportamentais de operadoras de telecomunicações como pontualidade no pagamento de faturas, histórico de recargas pré-pagas e tempo de permanência na base.

O objetivo é viabilizar o acesso ao crédito formal para pessoas hoje **invisíveis aos modelos tradicionais**: trabalhadores autônomos, informais e desbancados que mantêm um relacionamento contínuo e estável com sua operadora de telefonia, mas não possuem histórico em birôs de crédito.

Este projeto é desenvolvido no contexto de um evento da **IBM**, com utilização do **IBM Bob** como assistente de IA agêntica para apoiar o desenvolvimento, a documentação e o design da solução.

---

## Problema

Uma parcela relevante da população economicamente ativa no Brasil permanece desbancada ou subatendida pelo sistema financeiro, mesmo com comportamento financeiro responsável. Os modelos tradicionais de análise de crédito falham por:

- **Ausência de histórico formal** em birôs de crédito, mesmo com pagamentos em dia em outras frentes.
- **Renda informal e variável** não reconhecida por comprovantes tradicionais, penalizando autônomos.
- **Dependência do crédito informal** (agiotagem, "fiado") com juros muito superiores ao mercado regulado.
- **Decisão binária** baseada apenas em dados bancários, sem caminho de melhora para o usuário recusado.

### Usuário Central: "Maria"

Cabeleireira autônoma. Recebe em dinheiro ou Pix (muitas vezes na conta de outra pessoa). Paga suas contas em dia e recarrega o celular todo mês há anos. Precisa de um microcrédito para comprar equipamentos e aumentar a renda, mas é recusada por falta de histórico bancário.

---

## A Solução

ScoreLyne cria uma **ponte entre a operadora de telecomunicações e instituições financeiras**, transformando o rastro comportamental do cliente telecom em uma variável de score complementar:

| Quem | Ganha o quê |
|---|---|
| **Cliente (Maria)** | Acesso a crédito justo a partir de um histórico que já constrói no dia a dia |
| **Banco/Fintech** | Novo canal para aprovar crédito a um público antes recusado, com risco controlado |
| **Operadora** | Retenção de clientes e incentivo à migração do pré-pago para o pós-pago |

### Por que soluções atuais falham?

| Solução Atual | Faz bem | Onde falha |
|---|---|---|
| Score de birôs | Escala e padronização | Sem histórico bancário -> sem score |
| Cadastro Positivo | Premia quem paga em dia | Só registra quem já tem crédito formal |
| Comprovante de renda | Verifica capacidade de pagamento | Não captura renda informal/variável |
| Microcrédito orientado | Relacionamento próximo | Caro de operar, difícil de escalar |
| Open Finance / fintechs | Dados ricos, decisão rápida | Depende de conta bancária inexistente |
| Agiota e "fiado" | Rápido e sem burocracia | Juros abusivos, não gera histórico |

---

## IA Agêntica

A plataforma usa **IA Agêntica** para ir além de uma simples automação ou consulta de dados:

- **Entende o contexto comportamental** do cliente a partir de múltiplas fontes de dados telecom.
- **Coordena** o fluxo entre operadora, banco e cliente com consentimento ativo (LGPD).
- **Toma decisões explicáveis** de risco que o banco aceite e o cliente entenda.
- **Aprende e itera** com base nos resultados de crédito, refinando o modelo de scoring ao longo do tempo.

---

## IBM Bob

Este projeto é desenvolvido com o suporte do **IBM Bob**, assistente de engenharia de software da IBM utilizado no contexto do evento. O Bob é empregado ao longo de todas as fases do projeto para:

- **Leitura e análise de documentos** — extração de informações de propostas, guias e apresentações para consolidar o conhecimento do projeto.
- **Geração e manutenção de documentação** — criação de arquivos como este README a partir do conteúdo existente no repositório.
- **Apoio ao design da solução** — auxílio na estruturação da arquitetura do agente, fluxos de trabalho e escopo do MVP.
- **Desenvolvimento do código** — escrita, revisão e refatoração de código ao longo das semanas de implementação técnica.
- **Boas práticas de governança** — apoio na documentação de considerações éticas, conformidade com LGPD e diretrizes de IA responsável.

O IBM Bob opera como um agente de IA dentro do ambiente de desenvolvimento, com acesso controlado ao workspace do projeto e integração direta ao fluxo de trabalho da equipe.

---

## Estrutura do Projeto

O projeto segue um roadmap de 10 semanas:

| Fase | Periodo | Foco |
|---|---|---|
| Enquadramento da oportunidade | Semanas 1-2 | Pesquisa de usuário, mapa de empatia, cenário atual |
| Conceito da solução | Semana 3 | Persona, ideação, protótipo de baixa fidelidade |
| Arquitetura e Blueprint | Semanas 4-5 | Arquitetura do agente, fluxo de trabalho, governança |
| Implementação técnica | Semanas 6-8 | Desenvolvimento do MVP, testes com usuários |
| Entrega final | Semanas 9-10 | Documentação, demonstração, submissão do MVP |

**Prazo final:** 08/11/2026

---

## Governança e Ética

Dado que a solução lida com dados pessoais sensíveis e decisões de crédito, as seguintes dimensões são prioritárias:

- **Equidade e Antibias:** monitoramento contínuo para evitar decisões discriminatórias.
- **Transparência e Explicabilidade:** o usuário aprovado ou recusado entende o porquê.
- **Privacidade (LGPD):** consentimento explícito antes de qualquer uso de dados telecom.
- **Supervisão humana:** pontos de escalada e auditoria nas decisões críticas.
- **Conformidade:** alinhado com as diretrizes do Banco Central (crédito) e ANPD (dados pessoais).

---

## Equipe

| Nome | Função |
|---|---|
| Nickolas Maia de Araújo | Lider |
| Carlos Eduardo Fernandes Farias | Arquiteto de Soluções |
| Endrigo Gustavo Brandão de Oliveira | Engenheiro de Software |
| Tiago Bryan Ramos de Oliveira | Desenvolvedor Front |
| Gustavo Mendes Ventieri Mariano | Desenvolvedor Backend |

---

## Documentação

- [`Proposta_Credit_Scoring_Telco.docx`](Proposta_Credit_Scoring_Telco.docx) — Proposta detalhada do projeto
- [`Solution_Design_Guide_Participants.pptx`](Solution_Design_Guide_Participants.pptx) — Guia de design da solução
- [`Solution Design Guide for Participants-Portuguese BR.pdf`](Solution%20Design%20Guide%20for%20Participants-Portuguese%20BR.pdf) — Guia em PDF (versao PT-BR)
