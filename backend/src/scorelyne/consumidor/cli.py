"""Linha de comando do consumidor.

consumidor servir    # sobe a API em http://localhost:8003 (precisa do Postgres do docker compose)
consumidor semear    # cadastra as 5 personas da demo como consumidores (precisa da operadora no ar)
"""

from __future__ import annotations

import argparse
import os

import httpx

from scorelyne.comum.erros import ErroApi

from .db import ClienteDB, criar_sessoes
from .esquemas import Cadastro
from .servico import cadastrar

# Senha só da demo: os consumidores semeados são dados de teste, não pessoas reais.
SENHA_DEMO = "scorelyne123"

OCUPACOES_DEMO = {
    "maria": "Cabeleireira autônoma",
    "joao": "Motorista de aplicativo",
    "ana": "Vendedora ambulante",
    "carlos": "Pedreiro",
    "luciana": "Manicure",
}


def servir(args: argparse.Namespace) -> None:
    import uvicorn
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))

    uvicorn.run(
        "scorelyne.consumidor.api:create_app",
        factory=True,
        host=args.host,
        port=args.porta,
        reload=args.reload,
    )


def semear(args: argparse.Namespace) -> None:
    sessoes = criar_sessoes()
    url = os.getenv("OPERADORA_URL", "http://localhost:8001")
    personas = httpx.get(f"{url}/demo/personas", timeout=10).raise_for_status().json()

    with sessoes() as sessao:
        if args.limpar:
            for c in sessao.query(ClienteDB).all():
                sessao.delete(c)
            sessao.commit()
        for p in personas:
            try:
                cadastrar(
                    sessao,
                    Cadastro(
                        nome=p["titular"],
                        cpf=p["cpf"],
                        telefone=p["telefone"],
                        senha=SENHA_DEMO,
                        ocupacao=OCUPACOES_DEMO.get(p["chave"]),
                        cidade=p["cidade"],
                        uf=p["uf"],
                    ),
                )
                situacao = "cadastrado"
            except ErroApi:
                situacao = "já existia"
            print(f"{p['titular']:<28} CPF {p['cpf']}  {situacao}")
    print(f"\nSenha da demo para todos: {SENHA_DEMO}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="consumidor", description="API do consumidor do ScoreLyne")
    sub = parser.add_subparsers(required=True)

    p_servir = sub.add_parser("servir", help="Sobe a API")
    p_servir.add_argument("--host", default="127.0.0.1")
    p_servir.add_argument("--porta", type=int, default=8003)
    p_servir.add_argument("--reload", action="store_true")
    p_servir.set_defaults(func=servir)

    p_semear = sub.add_parser("semear", help="Cadastra as personas da demo como consumidores")
    p_semear.add_argument("--limpar", action="store_true", help="Apaga os cadastros existentes antes")
    p_semear.set_defaults(func=semear)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
