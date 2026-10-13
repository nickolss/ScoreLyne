"""Gerador determinístico da base sintética da operadora.

Cada linha nasce de três traços latentes (disciplina, volatilidade, mobilidade) que
moldam os eventos brutos: recargas, faturas, saldos zerados, suspensões e trocas de chip.
O rótulo de inadimplência é sorteado a partir dos mesmos traços, então um modelo
treinado só nos eventos observáveis consegue recuperar parte do sinal, como no mundo real.
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

from .models import (
    Fatura,
    Linha,
    MudancaPlano,
    PerfilOculto,
    Plano,
    Recarga,
    SaldoZerado,
    Suspensao,
)

DATA_REFERENCIA = date(2026, 9, 28)

# Atraso a partir do qual a linha é suspensa por falta de pagamento.
DIAS_PARA_SUSPENSAO = 30

CIDADES = [
    ("São Paulo", "SP", "11"),
    ("Osasco", "SP", "11"),
    ("Campinas", "SP", "19"),
    ("Rio de Janeiro", "RJ", "21"),
    ("Belo Horizonte", "MG", "31"),
    ("Contagem", "MG", "31"),
    ("Salvador", "BA", "71"),
    ("Recife", "PE", "81"),
    ("Fortaleza", "CE", "85"),
    ("Belém", "PA", "91"),
    ("Manaus", "AM", "92"),
    ("Porto Alegre", "RS", "51"),
    ("Curitiba", "PR", "41"),
    ("Goiânia", "GO", "62"),
    ("Brasília", "DF", "61"),
    ("São Luís", "MA", "98"),
    ("Teresina", "PI", "86"),
    ("Natal", "RN", "84"),
    ("João Pessoa", "PB", "83"),
    ("Maceió", "AL", "82"),
]

NOMES = [
    "Ana",
    "Antônio",
    "Beatriz",
    "Bruno",
    "Camila",
    "Carlos",
    "Daniela",
    "Diego",
    "Eduarda",
    "Fábio",
    "Fernanda",
    "Francisco",
    "Gabriela",
    "Gustavo",
    "Helena",
    "Igor",
    "Isabela",
    "Jéssica",
    "João",
    "José",
    "Juliana",
    "Larissa",
    "Leonardo",
    "Letícia",
    "Lucas",
    "Luana",
    "Marcos",
    "Mariana",
    "Mateus",
    "Natália",
    "Paulo",
    "Patrícia",
    "Rafael",
    "Raimunda",
    "Renata",
    "Rodrigo",
    "Sandra",
    "Sebastião",
    "Tatiane",
    "Thiago",
    "Vanessa",
    "Vitória",
]

SOBRENOMES = [
    "Almeida",
    "Alves",
    "Araújo",
    "Barbosa",
    "Barros",
    "Cardoso",
    "Carvalho",
    "Castro",
    "Costa",
    "Cunha",
    "Dias",
    "Ferreira",
    "Gomes",
    "Lima",
    "Lopes",
    "Machado",
    "Martins",
    "Melo",
    "Mendes",
    "Monteiro",
    "Moraes",
    "Moreira",
    "Nascimento",
    "Nunes",
    "Oliveira",
    "Pereira",
    "Pinto",
    "Ramos",
    "Ribeiro",
    "Rocha",
    "Rodrigues",
    "Santos",
    "Silva",
    "Soares",
    "Souza",
    "Teixeira",
    "Vieira",
]

VALORES_RECARGA = [10, 15, 20, 25, 30, 35, 40, 50, 60, 80, 100]


# --- Utilitários de data e identificação --------------------------------------


def somar_meses(d: date, meses: int) -> date:
    total = d.year * 12 + (d.month - 1) + meses
    ano, mes = divmod(total, 12)
    return date(ano, mes + 1, min(d.day, 28))


def competencia(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def meses_entre(inicio: date, fim: date) -> int:
    meses = (fim.year - inicio.year) * 12 + (fim.month - inicio.month)
    return meses - (1 if fim.day < inicio.day else 0)


def gerar_cpf(rng: random.Random) -> str:
    base = [rng.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        peso = len(base) + 1
        soma = sum(d * (peso - i) for i, d in enumerate(base))
        resto = (soma * 10) % 11
        base.append(0 if resto == 10 else resto)
    return "".join(map(str, base))


def cpf_valido(cpf: str) -> bool:
    if len(cpf) != 11 or not cpf.isdigit() or len(set(cpf)) == 1:
        return False
    digitos = list(map(int, cpf))
    for n in (9, 10):
        soma = sum(d * (n + 1 - i) for i, d in enumerate(digitos[:n]))
        if (soma * 10) % 11 % 10 != digitos[n]:
            return False
    return True


def ajustar_valor(valor: float) -> int:
    return min(VALORES_RECARGA, key=lambda v: abs(v - valor))


def no_periodo(d: date, ativada_em: date) -> bool:
    return ativada_em <= d <= DATA_REFERENCIA


# --- Simulação de uma linha da população --------------------------------------


def simular_linha(
    rng: random.Random, telefone: str, cidade: tuple[str, str, str]
) -> tuple[Linha, PerfilOculto]:
    disciplina = rng.betavariate(5, 2)
    volatilidade = rng.betavariate(2, 5)
    mobilidade = rng.betavariate(1.5, 8)

    meses_base = max(1, min(160, int(rng.lognormvariate(3.4, 0.8))))
    ativada_em = somar_meses(DATA_REFERENCIA, -meses_base).replace(day=rng.randint(1, 28))
    ativada_em = min(ativada_em, DATA_REFERENCIA)

    plano_inicial = rng.choices([Plano.PRE_PAGO, Plano.CONTROLE, Plano.POS_PAGO], [0.6, 0.2, 0.2])[0]
    mes_migracao: int | None = None
    if plano_inicial is Plano.PRE_PAGO and meses_base > 12 and rng.random() < 0.12:
        mes_migracao = rng.randint(6, meses_base - 1)

    linha = Linha(
        telefone=telefone,
        titular=f"{rng.choice(NOMES)} {rng.choice(SOBRENOMES)} {rng.choice(SOBRENOMES)}",
        cpf=gerar_cpf(rng),
        cidade=cidade[0],
        uf=cidade[1],
        plano=plano_inicial,
        ativada_em=ativada_em,
    )
    if rng.random() < 0.1 + 0.3 * mobilidade:
        linha.portabilidade_entrada = ativada_em

    dia_recarga = rng.randint(1, 28)
    valor_recarga = rng.choice([15, 20, 25, 30, 40, 50])
    dia_vencimento = rng.choice([5, 10, 15, 20, 25])
    valor_fatura = rng.uniform(35, 65) if plano_inicial is Plano.CONTROLE else rng.uniform(60, 160)
    prob_complemento = rng.uniform(0, 0.8)

    plano = plano_inicial
    inicio = ativada_em.replace(day=1)
    for k in range(meses_base + 1):
        mes = somar_meses(inicio, k)
        if mes > DATA_REFERENCIA:
            break

        if mes_migracao is not None and k == mes_migracao:
            linha.mudancas_plano.append(
                MudancaPlano(data=mes.replace(day=dia_recarga), de=plano, para=Plano.CONTROLE)
            )
            plano = Plano.CONTROLE
            valor_fatura = rng.uniform(35, 65)

        if plano is Plano.PRE_PAGO:
            _mes_pre_pago(rng, linha, mes, dia_recarga, valor_recarga, disciplina, volatilidade)
        else:
            _mes_pos_pago(rng, linha, mes, dia_vencimento, valor_fatura, disciplina, volatilidade)
            if plano is Plano.CONTROLE and rng.random() < prob_complemento:
                data = mes.replace(day=rng.randint(1, 28))
                if no_periodo(data, ativada_em):
                    linha.recargas.append(Recarga(data=data, valor=rng.choice([10, 15, 20])))

        if rng.random() < 0.003 + 0.03 * mobilidade:
            data = mes.replace(day=rng.randint(1, 28))
            if no_periodo(data, ativada_em):
                linha.trocas_chip.append(data)

    linha.plano = plano
    linha.recargas.sort(key=lambda r: r.data)

    peso_tempo = min(meses_base, 60) / 60
    z = -5.0 + 9.0 * (1 - disciplina) + 1.5 * volatilidade + 1.0 * mobilidade - 0.8 * peso_tempo
    z += rng.gauss(0, 0.3)
    inadimplente = rng.random() < 1 / (1 + math.exp(-z))

    perfil = PerfilOculto(
        disciplina=round(disciplina, 4),
        volatilidade=round(volatilidade, 4),
        mobilidade=round(mobilidade, 4),
        inadimplente=inadimplente,
    )
    return linha, perfil


def _mes_pre_pago(
    rng, linha: Linha, mes: date, dia_base: int, valor_base: int, disciplina: float, volatilidade: float
):
    if rng.random() < 0.5 + 0.48 * disciplina:
        dia = max(1, min(28, dia_base + round(rng.gauss(0, 2 + 6 * volatilidade))))
        data = mes.replace(day=dia)
        if not no_periodo(data, linha.ativada_em):
            return
        valor = ajustar_valor(valor_base * rng.lognormvariate(0, 0.08 + 0.5 * volatilidade))
        linha.recargas.append(Recarga(data=data, valor=valor))
        if rng.random() < (1 - disciplina) * 0.35:
            dias = rng.randint(1, 7)
            zerou = data - timedelta(days=dias)
            if no_periodo(zerou, linha.ativada_em):
                linha.saldos_zerados.append(SaldoZerado(data=zerou, dias_sem_saldo=dias))
        if rng.random() < 0.12 + 0.2 * volatilidade:
            extra = data + timedelta(days=rng.randint(5, 20))
            if no_periodo(extra, linha.ativada_em) and extra.month == data.month:
                linha.recargas.append(Recarga(data=extra, valor=rng.choice([10, 15, 20])))
    else:
        zerou = mes.replace(day=dia_base)
        if no_periodo(zerou, linha.ativada_em):
            dias = min(rng.randint(10, 30), (DATA_REFERENCIA - zerou).days)
            linha.saldos_zerados.append(SaldoZerado(data=zerou, dias_sem_saldo=dias))


def _mes_pos_pago(
    rng, linha: Linha, mes: date, dia_venc: int, valor_base: float, disciplina: float, volatilidade: float
):
    vencimento = mes.replace(day=dia_venc)
    # A primeira fatura só vence depois de um ciclo completo de uso.
    if vencimento > DATA_REFERENCIA or vencimento < linha.ativada_em + timedelta(days=20):
        return

    valor = valor_base * (1 + rng.gauss(0, 0.04 + 0.25 * volatilidade))
    if rng.random() < 0.04 + 0.1 * volatilidade:
        valor *= rng.uniform(1.6, 2.5)

    if rng.random() < 0.55 + 0.43 * disciplina:
        atraso = -rng.randint(0, 5)
    else:
        atraso = int(rng.expovariate(1 / (3 + 30 * (1 - disciplina)))) + 1
    _registrar_fatura(linha, vencimento, atraso, max(valor, 15.0))


def _registrar_fatura(linha: Linha, vencimento: date, atraso: int, valor: float):
    pago_em: date | None = vencimento + timedelta(days=atraso)
    if pago_em > DATA_REFERENCIA:
        pago_em = None
    linha.faturas.append(
        Fatura(
            competencia=competencia(somar_meses(vencimento, -1)),
            vencimento=vencimento,
            pago_em=pago_em,
            valor=round(valor, 2),
        )
    )
    inicio_suspensao = vencimento + timedelta(days=DIAS_PARA_SUSPENSAO)
    if atraso > DIAS_PARA_SUSPENSAO and inicio_suspensao <= DATA_REFERENCIA:
        linha.suspensoes.append(Suspensao(inicio=inicio_suspensao, fim=pago_em))


# --- População ----------------------------------------------------------------


def gerar_populacao(
    n: int, semente: int = 42, reservados: set[str] | None = None
) -> list[tuple[Linha, PerfilOculto]]:
    """Gera `n` linhas sintéticas. Mesma semente e mesmo `n`, mesma base."""
    rng_base = random.Random(semente)
    usados = set(reservados or ())
    populacao = []
    for i in range(n):
        rng = random.Random(f"{semente}-{i}")
        cidade = rng_base.choice(CIDADES)
        while True:
            telefone = f"{cidade[2]}9{rng_base.randint(0, 99_999_999):08d}"
            if telefone not in usados:
                usados.add(telefone)
                break
        populacao.append(simular_linha(rng, telefone, cidade))
    return populacao
