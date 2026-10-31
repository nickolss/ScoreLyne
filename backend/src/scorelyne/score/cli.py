"""Linha de comando do motor de score.

score treinar   # treina na população sintética e grava modelo.json
score servir    # sobe a API em http://localhost:8002
"""

from __future__ import annotations

import argparse


def treinar(args: argparse.Namespace) -> None:
    from .modelo import ARQUIVO_MODELO, salvar_modelo
    from .treino import treinar as rodar

    modelo = rodar(args.populacao, args.semente)
    salvar_modelo(modelo)
    m = modelo.metricas
    print(f"Modelo {modelo.versao} gravado em {ARQUIVO_MODELO}\n")
    print(f"AUC {m['auc']:.3f} · Gini {m['gini']:.3f} · KS {m['ks']:.3f} (teste, n={int(m['n_teste'])})")
    print(f"Inadimplência da base: {m['taxa_inadimplencia']:.1%}\n")
    print("Importância dos fatores:")
    for k, v in sorted(modelo.importancia.items(), key=lambda kv: -kv[1]):
        nota = "" if modelo.coeficientes[k] else "  (sem poder preditivo, fora do modelo)"
        print(f"  {k.value:<14}{v:>6.1%}{nota}")
    print(
        f"\nPolítica no teste: {m['taxa_aprovacao_automatica']:.0%} aprovação automática "
        f"(inadimplência {m['inadimplencia_aprovados']:.1%}), {m['taxa_revisao']:.0%} revisão, "
        f"{m['taxa_recusa']:.0%} recusa (inadimplência {m['inadimplencia_recusados']:.1%})"
    )
    print("\nEquidade (aprovação automática por grupo, regra dos 4/5):")
    for dimensao, r in modelo.equidade.items():
        taxas = ", ".join(
            f"{g} {t['taxa_aprovacao']:.0%} (inad. aprov. {t['inadimplencia_aprovados'] or 0:.1%})"
            for g, t in r["grupos"].items()
        )
        status = "ok" if r["passa_regra_4_5"] else "ATENÇÃO"
        print(f"  {dimensao:<7} razão {r['razao_impacto']} [{status}]  {taxas}")
        cal = "calibrado" if r["calibrado_em_todos_os_grupos"] else "DESCALIBRADO"
        print(
            f"          {cal}: erro máximo entre PD prevista e inadimplência real {r['erro_calibracao_maximo']:.1%}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(prog="score", description="Motor de score do ScoreLyne")
    sub = parser.add_subparsers(required=True)

    p_treinar = sub.add_parser("treinar", help="Treina o modelo e grava modelo.json")
    p_treinar.add_argument("--populacao", type=int, default=3000)
    p_treinar.add_argument("--semente", type=int, default=42)
    p_treinar.set_defaults(func=treinar)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
