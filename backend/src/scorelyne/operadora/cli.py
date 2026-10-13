"""Linha de comando da operadora mock.

operadora servir                # sobe a API em http://localhost:8001
operadora exportar --saida data # gera os CSVs de treino do modelo
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from .generator import DATA_REFERENCIA, gerar_populacao, meses_entre


def servir(args: argparse.Namespace) -> None:
    import os

    import uvicorn

    os.environ["OPERADORA_POPULACAO"] = str(args.populacao)
    os.environ["OPERADORA_SEMENTE"] = str(args.semente)
    uvicorn.run(
        "scorelyne.operadora.api:create_app",
        factory=True,
        host=args.host,
        port=args.porta,
        reload=args.reload,
    )


def exportar(args: argparse.Namespace) -> None:
    """Exporta a população (sem as personas) em CSVs normalizados, com o rótulo de inadimplência."""
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    populacao = gerar_populacao(args.populacao, args.semente)

    tabelas: dict[str, tuple[list[str], list[list]]] = {
        "linhas": (["telefone", "plano", "ativada_em", "meses_na_base", "uf", "portabilidade_entrada"], []),
        "recargas": (["telefone", "data", "valor"], []),
        "faturas": (["telefone", "competencia", "vencimento", "pago_em", "valor"], []),
        "saldos_zerados": (["telefone", "data", "dias_sem_saldo"], []),
        "suspensoes": (["telefone", "inicio", "fim"], []),
        "trocas_chip": (["telefone", "data"], []),
        "mudancas_plano": (["telefone", "data", "de", "para"], []),
        "rotulos": (["telefone", "inadimplente", "disciplina", "volatilidade", "mobilidade"], []),
    }

    def add(tabela: str, *valores) -> None:
        tabelas[tabela][1].append(["" if v is None else v for v in valores])

    for linha, perfil in populacao:
        t = linha.telefone
        add(
            "linhas",
            t,
            linha.plano.value,
            linha.ativada_em,
            meses_entre(linha.ativada_em, DATA_REFERENCIA),
            linha.uf,
            linha.portabilidade_entrada,
        )
        for r in linha.recargas:
            add("recargas", t, r.data, r.valor)
        for f in linha.faturas:
            add("faturas", t, f.competencia, f.vencimento, f.pago_em, f.valor)
        for s in linha.saldos_zerados:
            add("saldos_zerados", t, s.data, s.dias_sem_saldo)
        for s in linha.suspensoes:
            add("suspensoes", t, s.inicio, s.fim)
        for d in linha.trocas_chip:
            add("trocas_chip", t, d)
        for m in linha.mudancas_plano:
            add("mudancas_plano", t, m.data, m.de.value, m.para.value)
        add("rotulos", t, int(perfil.inadimplente), perfil.disciplina, perfil.volatilidade, perfil.mobilidade)

    for nome, (cabecalho, linhas) in tabelas.items():
        with open(saida / f"{nome}.csv", "w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(cabecalho)
            escritor.writerows(linhas)
        print(f"{nome + '.csv':<22} {len(linhas):>7} linhas")

    planos = Counter(linha.plano.value for linha, _ in populacao)
    taxa = sum(p.inadimplente for _, p in populacao) / len(populacao)
    print(f"\nPlanos: {dict(planos)}")
    print(f"Taxa de inadimplência sintética: {taxa:.1%}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="operadora", description="Operadora mock do ScoreLyne")
    sub = parser.add_subparsers(required=True)

    p_servir = sub.add_parser("servir", help="Sobe a API")
    p_servir.add_argument("--host", default="127.0.0.1")
    p_servir.add_argument("--porta", type=int, default=8001)
    p_servir.add_argument("--reload", action="store_true")
    p_servir.set_defaults(func=servir)

    p_exportar = sub.add_parser("exportar", help="Exporta a base sintética em CSV")
    p_exportar.add_argument("--saida", default="data")
    p_exportar.set_defaults(func=exportar)

    for p in (p_servir, p_exportar):
        p.add_argument("--populacao", type=int, default=3000)
        p.add_argument("--semente", type=int, default=42)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
