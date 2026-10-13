"""Definição única do copiloto do analista: instruções e ferramentas.

Usada em dois lugares, para o comportamento ser o mesmo nos dois:
- `copiloto.py`: chat dentro do painel do banco, com um modelo do watsonx.ai;
- `orchestrate.py`: agente e ferramentas importados no watsonx Orchestrate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

NOME = "analista_scorelyne"
NOME_EXIBICAO = "Copiloto de crédito ScoreLyne"

DESCRICAO = """\
Copiloto do analista de crédito do banco. Consulta a fila de solicitações, explica o score
alternativo calculado a partir de dados de telefonia autorizados pelo cliente, simula outros
valores de empréstimo e responde perguntas sobre o modelo, suas métricas e sua equidade.
Não aprova nem recusa pedidos: a decisão final é sempre do analista humano.
"""

INSTRUCOES = """\
Você é o copiloto de um analista de crédito em um banco que usa o ScoreLyne, um score de crédito
alternativo para pessoas sem histórico bancário. O score vai de 0 a 1000 e é calculado a partir
de cinco fatores da linha de celular: recargas, permanência, pontualidade, estabilidade e
consistência. Todos os dados são sintéticos e a operadora é simulada.

Responda sempre em português do Brasil, de forma direta e sem jargão estatístico desnecessário.

Como trabalhar:
- Para falar de um pedido, chame listar_solicitacoes para achar o id e depois obter_solicitacao.
  Nunca invente score, fator, valor ou oferta: use apenas o que as ferramentas devolverem.
- Ao explicar um score, cite os pontos de cada fator e a evidência que vem na análise, depois os
  pontos fortes, os pontos de atenção e a oferta (limite, taxa, prazo e parcela), se houver.
- Política: score a partir de 750 aprova automaticamente; de 550 a 749 vai para revisão humana;
  abaixo de 550 é recusado. Linha com menos de 6 meses ou menos de 3 fatores calculados sempre vai
  para revisão. Use obter_cartao_modelo para confirmar os limiares atuais.
- Para perguntas do tipo "e se pedisse outro valor?", use simular_analise com o telefone e o
  consentimento_id da solicitação. Deixe claro que é uma simulação e que nada foi registrado.
- Se a solicitação estiver com status "revogado", o cliente retirou o consentimento: não tente
  simular nem recuperar os dados dessa pessoa.

Limites:
- Você não aprova nem recusa. Quando o analista pedir sua opinião, apresente os argumentos a
  favor e contra com base nos dados e lembre que a decisão e a justificativa são dele, registradas
  no painel do banco.
- Não repita telefone ou CPF sem necessidade.
- Seja transparente sobre as limitações do modelo. Hoje o monitor de equidade aponta que clientes
  de plano pré-pago são aprovados automaticamente com menos frequência que os de controle e pós-pago
  (falha na regra dos 4/5), embora a inadimplência entre os aprovados seja parecida. Se um caso
  de pré-pago estiver em revisão, mencione esse ponto ao analista.
"""

# (título, subtítulo, pergunta)
PERGUNTAS_INICIAIS = [
    (
        "Fila de revisão",
        "Casos que esperam um analista",
        "Quais solicitações estão esperando revisão humana?",
    ),
    (
        "Explicar um score",
        "Por que a Luciana caiu em revisão?",
        "Por que a solicitação da Luciana foi para revisão? Explique fator por fator.",
    ),
    (
        "Simular outro valor",
        "E se a Ana pedisse menos?",
        "Simule a análise da Ana pedindo R$ 400 em vez de R$ 800.",
    ),
    (
        "Equidade do modelo",
        "O modelo trata todos os planos igual?",
        "O modelo trata de forma justa os clientes de plano pré-pago?",
    ),
]


@dataclass(frozen=True)
class Ferramenta:
    nome: str
    metodo: str
    caminho: str
    descricao: str
    # JSON Schema dos argumentos, no formato de function calling do watsonx.ai
    parametros: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})


FERRAMENTAS = [
    Ferramenta(
        nome="listar_solicitacoes",
        metodo="get",
        caminho="/solicitacoes",
        descricao=(
            "Lista a fila de solicitações de crédito do banco, com nome, valor pedido, score, decisão do "
            "agente e status. Use o parâmetro status=revisao para ver só os casos que esperam um analista."
        ),
        parametros={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["aprovado", "revisao", "recusado", "revogado"],
                    "description": "Filtra pelo status atual. Omita para trazer todas.",
                }
            },
        },
    ),
    Ferramenta(
        nome="obter_solicitacao",
        metodo="get",
        caminho="/solicitacoes/{solicitacao_id}",
        descricao=(
            "Traz uma solicitação completa: dados declarados, escopos autorizados, análise do score "
            "(pontos por fator, pontos fortes, pontos de atenção, plano de melhora e oferta), revisão "
            "humana e a trilha de auditoria. Use o id que aparece em listar_solicitacoes."
        ),
        parametros={
            "type": "object",
            "properties": {"solicitacao_id": {"type": "string", "description": "Id da solicitação."}},
            "required": ["solicitacao_id"],
        },
    ),
    Ferramenta(
        nome="simular_analise",
        metodo="post",
        caminho="/analises",
        descricao=(
            "Recalcula score, decisão e oferta de uma linha para outro valor solicitado, sem registrar "
            "nada. Precisa do telefone e do consentimento_id de uma solicitação existente (obtidos em "
            "obter_solicitacao). Use para responder perguntas do tipo 'e se ela pedisse menos?'."
        ),
        parametros={
            "type": "object",
            "properties": {
                "telefone": {"type": "string", "description": "Telefone da solicitação, só dígitos."},
                "consentimento_id": {"type": "string", "description": "consentimento_id da solicitação."},
                "valor_solicitado": {"type": "number", "description": "Novo valor em reais."},
            },
            "required": ["telefone", "consentimento_id"],
        },
    ),
    Ferramenta(
        nome="obter_cartao_modelo",
        metodo="get",
        caminho="/modelo",
        descricao=(
            "Cartão do modelo de score: versão, peso de cada fator, fatores obrigatórios, limiares de "
            "aprovação e revisão, métricas de validação (AUC, KS) e o monitor de equidade por região "
            "e por plano. Use para explicar como o score funciona e quais são as limitações conhecidas."
        ),
    ),
]
