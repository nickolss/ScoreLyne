"""Linha de comando do banco.

banco servir    # sobe a API em http://localhost:8002 (precisa do Postgres do docker compose)
banco semear    # cria as solicitações das 5 personas da demo (precisa da operadora no ar)
"""

from __future__ import annotations

import argparse
import os
from datetime import timedelta

import httpx

from .db import SolicitacaoDB, agora, criar_sessoes
from .esquemas import NovaSolicitacao
from .servico import Operadora, criar

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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
