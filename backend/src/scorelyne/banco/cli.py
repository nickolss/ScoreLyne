"""Linha de comando do banco.

banco servir    # sobe a API em http://localhost:8002 (precisa do Postgres do docker compose)
banco semear    # cria as solicitações das 5 personas da demo (precisa da operadora no ar)
banco orchestrate --url https://...   # ferramentas (OpenAPI 3.0) e agente para o watsonx Orchestrate
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import timedelta

import httpx
from sqlalchemy import select

from .db import AnalistaDB, SolicitacaoDB, agora, criar_sessoes
from .esquemas import NovaSolicitacao
from .servico import Operadora, criar, criar_analista

# Credenciais só da demo: o analista semeado é um dado de teste, não uma pessoa real.
ANALISTA_DEMO = ("analista@scorelyne.demo", "Analista de crédito", "scorelyne123")

# Dados que o cliente declara no pedido. Telefone e CPF vêm de /demo/personas da operadora.
PEDIDOS_DEMO = {
    "maria": ("Cabeleireira autônoma", 1500, "Equipamentos (secador e prancha)", 2),
    "joao": ("Motorista de aplicativo", 3000, "Reparo do veículo", 6),
    "ana": ("Vendedora ambulante", 800, "Capital de giro", 20),
    "carlos": ("Pedreiro", 5000, "Ferramentas", 30),
    "luciana": ("Manicure", 1000, "Materiais de trabalho", 45),
}


def servir(args: argparse.Namespace) -> None:
    import uvicorn
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))  # backend/.env: credenciais do watsonx.ai

    uvicorn.run(
        "scorelyne.banco.api:create_app", factory=True, host=args.host, port=args.porta, reload=args.reload
    )


def semear(args: argparse.Namespace) -> None:
    sessoes = criar_sessoes()
    url = os.getenv("OPERADORA_URL", "http://localhost:8001")
    cliente = httpx.Client(base_url=url, timeout=10)
    operadora = Operadora(cliente)
    personas = {p["chave"]: p for p in cliente.get("/demo/personas").raise_for_status().json()}

    with sessoes() as sessao:
        if not sessao.scalar(select(AnalistaDB).where(AnalistaDB.email == ANALISTA_DEMO[0])):
            criar_analista(sessao, *ANALISTA_DEMO)
        if args.limpar:
            for s in sessao.query(SolicitacaoDB).all():
                sessao.delete(s)
            sessao.commit()
        for chave, (ocupacao, valor, finalidade, horas_atras) in PEDIDOS_DEMO.items():
            p = personas[chave]
            consentimento = (
                cliente.post(
                    "/consentimentos",
                    json={
                        "telefone": p["telefone"],
                        "cpf": p["cpf"],
                        "escopos": [
                            "permanencia",
                            "recargas",
                            "pontualidade",
                            "estabilidade",
                            "consistencia",
                        ],
                        "finalidade": "analise_de_credito",
                        "solicitante": "Banco Parceiro S.A.",
                    },
                )
                .raise_for_status()
                .json()
            )
            pedido = NovaSolicitacao(
                nome=p["titular"],
                telefone=p["telefone"],
                consentimento_id=consentimento["id"],
                valor_solicitado=valor,
                finalidade=finalidade,
                ocupacao=ocupacao,
                cidade=p["cidade"],
                uf=p["uf"],
            )
            s = criar(sessao, operadora, pedido)
            momento = agora() - timedelta(hours=horas_atras)
            s.criado_em = momento
            for e in s.eventos:
                e.em = momento
            sessao.commit()
            print(f"{p['titular']:<28} score {s.score:>4}  {s.decisao_agente}")
    print(f"\nLogin do analista: {ANALISTA_DEMO[0]} / {ANALISTA_DEMO[2]}")


def orchestrate(args: argparse.Namespace) -> None:
    from .orchestrate import gerar_agente, gerar_spec

    spec = gerar_spec(args.url)
    ferramentas = os.path.join(args.saida, "tools", "banco-openapi.json")
    agente = os.path.join(args.saida, "agents", "analista_scorelyne.yaml")
    for caminho in (ferramentas, agente):
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(ferramentas, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(agente, "w", encoding="utf-8") as f:
        f.write(gerar_agente(args.llm))
    nomes = [op["operationId"] for caminho in spec["paths"].values() for op in caminho.values()]
    print(f"{ferramentas}: {', '.join(nomes)} -> {args.url}")
    print(f"{agente}: llm {args.llm}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="banco", description="API do banco do ScoreLyne")
    sub = parser.add_subparsers(required=True)

    p_servir = sub.add_parser("servir", help="Sobe a API")
    p_servir.add_argument("--host", default="127.0.0.1")
    p_servir.add_argument("--porta", type=int, default=8002)
    p_servir.add_argument("--reload", action="store_true")
    p_servir.set_defaults(func=servir)

    p_semear = sub.add_parser("semear", help="Cria as solicitações das personas da demo")
    p_semear.add_argument("--limpar", action="store_true", help="Apaga as solicitações existentes antes")
    p_semear.set_defaults(func=semear)

    p_orq = sub.add_parser("orchestrate", help="Gera o spec OpenAPI das ferramentas do watsonx Orchestrate")
    p_orq.add_argument(
        "--url",
        default=os.getenv("BANCO_URL_PUBLICA", "http://host.docker.internal:8002"),
        help="Endereço do banco visto pelo Orchestrate (túnel público no SaaS)",
    )
    p_orq.add_argument(
        "--llm",
        default=os.getenv("ORCHESTRATE_LLM", "watsonx-orchestrate/frontier"),
        help="Modelo do agente (confira com `orchestrate models list`)",
    )
    p_orq.add_argument("--saida", default="../orchestrate", help="Pasta com tools/ e agents/")
    p_orq.set_defaults(func=orchestrate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
