"""As cinco personas da demo, montadas à mão para bater com a narrativa do frontend.

Ao contrário da população, aqui cada fato citado nas telas (meses sem recarga,
faturas atrasadas, troca de chip) é colocado de propósito.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from .generator import (
    DATA_REFERENCIA,
    _registrar_fatura,
    gerar_cpf,
    somar_meses,
)
from .models import Linha, Plano, Recarga, SaldoZerado


def _cpf(nome: str) -> str:
    return gerar_cpf(random.Random(f"persona-{nome}"))


def maria() -> Linha:
    """Pré-pago há 74 meses, 71 meses com recarga, sem portabilidade nem troca de chip."""
    linha = Linha(
        telefone="11987124821",
        titular="Maria Aparecida dos Santos",
        cpf=_cpf("maria"),
        cidade="Osasco",
        uf="SP",
        plano=Plano.PRE_PAGO,
        ativada_em=date(2020, 7, 25),
    )
    valores = [20, 30, 25, 30, 20, 50, 30, 25]
    sem_recarga = {9, 27, 44}
    for i in range(74):
        mes = somar_meses(date(2020, 8, 1), i)
        data = mes.replace(day=3 + (i * 7) % 5)
        if i in sem_recarga:
            linha.saldos_zerados.append(SaldoZerado(data=data, dias_sem_saldo=28))
        else:
            linha.recargas.append(Recarga(data=data, valor=valores[i % len(valores)]))
    return linha


def joao() -> Linha:
    """Controle há 38 meses, 37 de 38 faturas em dia, uma troca de chip em 2025."""
    rng = random.Random("persona-joao")
    linha = Linha(
        telefone="81996537210",
        titular="João Batista Ferreira",
        cpf=_cpf("joao"),
        cidade="Recife",
        uf="PE",
        plano=Plano.CONTROLE,
        ativada_em=date(2023, 7, 14),
        trocas_chip=[date(2025, 3, 18)],
    )
    for i in range(38):
        vencimento = somar_meses(date(2023, 8, 10), i)
        atraso = 4 if i == 20 else -rng.randint(0, 3)
        _registrar_fatura(linha, vencimento, atraso, rng.uniform(45, 55))
        if rng.random() < 0.8:
            data = vencimento + timedelta(days=rng.randint(5, 15))
            if data <= DATA_REFERENCIA:
                linha.recargas.append(Recarga(data=data, valor=rng.choice([10, 15])))
    return linha


def ana() -> Linha:
    """Pré-pago há 14 meses, 10 meses com recarga, 5 vezes com saldo zerado."""
    rng = random.Random("persona-ana")
    linha = Linha(
        telefone="91984412093",
        titular="Ana Clara Souza",
        cpf=_cpf("ana"),
        cidade="Belém",
        uf="PA",
        plano=Plano.PRE_PAGO,
        ativada_em=date(2025, 7, 20),
    )
    sem_recarga = {3, 6, 7, 11}
    for i in range(14):
        mes = somar_meses(date(2025, 8, 1), i)
        data = mes.replace(day=rng.randint(5, 20))
        if i in sem_recarga:
            linha.saldos_zerados.append(SaldoZerado(data=data, dias_sem_saldo=rng.randint(15, 30)))
        else:
            linha.recargas.append(Recarga(data=data, valor=rng.choice([10, 15, 20, 30])))
    linha.saldos_zerados.append(SaldoZerado(data=date(2026, 9, 2), dias_sem_saldo=4))
    linha.saldos_zerados.sort(key=lambda s: s.data)
    return linha


def carlos() -> Linha:
    """Pós-pago há 112 meses, 6 atrasos acima de 15 dias nas últimas 12 faturas, 2 suspensões."""
    rng = random.Random("persona-carlos")
    linha = Linha(
        telefone="31991827746",
        titular="Carlos Henrique Lima",
        cpf=_cpf("carlos"),
        cidade="Contagem",
        uf="MG",
        plano=Plano.POS_PAGO,
        ativada_em=date(2017, 5, 10),
    )
    atrasos_recentes = {100: 18, 102: 22, 104: 35, 106: 17, 108: 41, 110: 20}
    picos = {97, 103, 109}
    for i in range(112):
        vencimento = somar_meses(date(2017, 6, 20), i)
        if i in atrasos_recentes:
            atraso = atrasos_recentes[i]
        elif i < 100 and rng.random() < 0.08:
            atraso = rng.randint(1, 6)
        else:
            atraso = -rng.randint(0, 4)
        valor = rng.uniform(85, 110) * (2.1 if i in picos else 1)
        _registrar_fatura(linha, vencimento, atraso, valor)
    return linha


def luciana() -> Linha:
    """Pré-pago ativado há 5 meses, 4 meses com recarga. Histórico curto demais."""
    linha = Linha(
        telefone="71988305518",
        titular="Luciana Ferreira",
        cpf=_cpf("luciana"),
        cidade="Salvador",
        uf="BA",
        plano=Plano.PRE_PAGO,
        ativada_em=date(2026, 4, 22),
        recargas=[
            Recarga(data=date(2026, 5, 6), valor=20),
            Recarga(data=date(2026, 6, 9), valor=15),
            Recarga(data=date(2026, 8, 12), valor=30),
            Recarga(data=date(2026, 9, 10), valor=20),
        ],
        saldos_zerados=[SaldoZerado(data=date(2026, 7, 8), dias_sem_saldo=35)],
    )
    return linha


PERSONAS = {
    "maria": maria,
    "joao": joao,
    "ana": ana,
    "carlos": carlos,
    "luciana": luciana,
}


def gerar_personas() -> dict[str, Linha]:
    return {chave: construir() for chave, construir in PERSONAS.items()}
