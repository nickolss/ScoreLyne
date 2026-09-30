"use client";

import { useEffect, useMemo, useState } from "react";
import { Arrow } from "@/components/icons";
import { Barcode, DecisionBadge, FactorLines, ScoreScale, ScoreTotal } from "@/components/score";
import {
  APPLICANTS,
  EXCLUDED_DATA,
  FACTOR_META,
  type FactorKey,
  brl,
  brl2,
  computeScore,
  decide,
  installment,
  monthlyRate,
  suggestedLimit,
  tenureLabel,
} from "@/lib/data";

type Step = "inicio" | "consentimento" | "analise" | "resultado";

const PERSONAS = APPLICANTS.filter((a) => ["maria", "ana", "luciana"].includes(a.id));

const CONSENT_ITEMS: { key: FactorKey; detail: string; required?: boolean }[] = [
  { key: "recargas", detail: "Datas e frequência das recargas dos últimos 24 meses", required: true },
  { key: "permanencia", detail: "Data de ativação da linha na operadora", required: true },
  { key: "pontualidade", detail: "Pagamento de faturas ou recarga antes do saldo zerar" },
  { key: "estabilidade", detail: "Trocas de chip e portabilidades do número" },
  { key: "consistencia", detail: "Valores médios de recarga ou fatura" },
];

const AGENT_STEPS = [
  "Verificando consentimento e finalidade do uso",
  "Solicitando à operadora os dados autorizados",
  "Calculando fatores de comportamento",
  "Checando equidade: nenhuma variável sensível no modelo",
  "Gerando explicação da decisão",
];

const TERMS = [6, 12, 18];

const btnPrimary =
  "inline-flex items-center justify-center gap-3 bg-ink text-paper px-5 py-3.5 font-semibold hover:bg-cobalt transition-colors disabled:opacity-35 disabled:hover:bg-ink disabled:cursor-not-allowed";
const btnSecondary =
  "inline-flex items-center justify-center border border-ink px-5 py-3.5 font-semibold hover:bg-tint transition-colors";

export function Journey() {
  const [step, setStep] = useState<Step>("inicio");
  const [personaId, setPersonaId] = useState("maria");
  const [consent, setConsent] = useState<Record<FactorKey, boolean>>({
    recargas: true,
    permanencia: true,
    pontualidade: true,
    estabilidade: true,
    consistencia: true,
  });

  const persona = PERSONAS.find((p) => p.id === personaId)!;

  return (
    <div className="bg-paper border border-ink">
      <Progress step={step} />
      <div className="p-5 sm:p-10">
        {step === "inicio" && (
          <section className="feed">
            <h1 className="display text-4xl sm:text-5xl">Seu celular conta a sua história financeira.</h1>
            <p className="mt-5 text-ink-2 text-lg leading-relaxed">
              Sem conta em banco ou histórico no Serasa? Tudo bem. Com a sua autorização, usamos seu
              relacionamento com a operadora para calcular um score e buscar uma oferta de crédito.
            </p>

            <fieldset className="mt-10">
              <legend className="label text-ink-2">Escolha um perfil para simular</legend>
              <div className="mt-3 grid sm:grid-cols-3 border border-ink">
                {PERSONAS.map((p) => {
                  const active = p.id === personaId;
                  return (
                    <label
                      key={p.id}
                      className={`cursor-pointer p-4 border-b sm:border-b-0 sm:border-r last:border-0 border-ink transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-cobalt has-[:focus-visible]:-outline-offset-4 ${
                        active ? "bg-cobalt text-on-cobalt" : "hover:bg-tint"
                      }`}
                    >
                      <input
                        type="radio"
                        name="persona"
                        value={p.id}
                        checked={active}
                        onChange={() => setPersonaId(p.id)}
                        className="sr-only"
                      />
                      <span className="block font-bold">{p.name}</span>
                      <span className={`block text-sm ${active ? "text-on-cobalt-2" : "text-ink-2"}`}>
                        {p.occupation}
                      </span>
                      <span className={`num mt-4 block text-[11px] ${active ? "text-on-cobalt-2" : "text-ink-2"}`}>
                        {p.plan} · {tenureLabel(p.tenureMonths)}
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>

            <dl className="mt-6 grid grid-cols-2 border-t-2 border-ink">
              <div className="pt-3">
                <dt className="label text-ink-2">Valor desejado</dt>
                <dd className="num text-2xl mt-1">{brl(persona.requested)}</dd>
              </div>
              <div className="pt-3">
                <dt className="label text-ink-2">Para quê</dt>
                <dd className="mt-1.5">{persona.purpose}</dd>
              </div>
            </dl>

            <button onClick={() => setStep("consentimento")} className={`${btnPrimary} mt-10 w-full sm:w-auto`}>
              Continuar <Arrow />
            </button>
          </section>
        )}

        {step === "consentimento" && (
          <ConsentStep
            consent={consent}
            setConsent={setConsent}
            onBack={() => setStep("inicio")}
            onAccept={() => setStep("analise")}
          />
        )}

        {step === "analise" && <AnalysisStep onDone={() => setStep("resultado")} />}

        {step === "resultado" && (
          <ResultStep persona={persona} consent={consent} onRestart={() => setStep("inicio")} />
        )}
      </div>
    </div>
  );
}

function Progress({ step }: { step: Step }) {
  const order: Step[] = ["inicio", "consentimento", "analise", "resultado"];
  const labels = ["Pedido", "Consentimento", "Análise", "Resultado"];
  const idx = order.indexOf(step);
  return (
    <ol className="grid grid-cols-4 border-b border-ink" aria-label="Etapas">
      {labels.map((l, i) => (
        <li
          key={l}
          aria-current={i === idx ? "step" : undefined}
          className={`px-2 sm:px-4 py-3 border-r border-ink last:border-r-0 ${
            i === idx ? "bg-cobalt text-on-cobalt" : i < idx ? "bg-tint" : ""
          }`}
        >
          <span className={`num block text-[10px] ${i === idx ? "text-on-cobalt-2" : "text-ink-2"}`}>
            {i + 1}/4
          </span>
          <span className="block text-xs sm:text-sm font-semibold truncate">{l}</span>
        </li>
      ))}
    </ol>
  );
}

function ConsentStep({
  consent,
  setConsent,
  onBack,
  onAccept,
}: {
  consent: Record<FactorKey, boolean>;
  setConsent: (c: Record<FactorKey, boolean>) => void;
  onBack: () => void;
  onAccept: () => void;
}) {
  const [read, setRead] = useState(false);
  return (
    <section className="feed">
      <h1 className="display text-4xl sm:text-5xl">O que você autoriza.</h1>
      <p className="mt-5 text-ink-2 leading-relaxed">
        Finalidade única: calcular seu score de crédito para esta solicitação. Válido por 30 dias e
        revogável a qualquer momento. Dados que você não autorizar ficam fora do cálculo.
      </p>

      <ul className="mt-8 border-t-2 border-ink">
        {CONSENT_ITEMS.map((item) => (
          <li key={item.key} className="border-b border-rule">
            <label className={`flex items-start gap-4 py-4 ${item.required ? "" : "cursor-pointer"}`}>
              <input
                type="checkbox"
                className="mt-1 size-4 accent-[var(--cobalt)]"
                checked={consent[item.key]}
                disabled={item.required}
                onChange={(e) => setConsent({ ...consent, [item.key]: e.target.checked })}
              />
              <span className="flex-1">
                <span className="font-semibold">{FACTOR_META[item.key].label}</span>
                {item.required && <span className="label ml-2 border border-ink px-1.5 py-0.5">necessário</span>}
                <span className="block text-sm text-ink-2 mt-1">{item.detail}</span>
              </span>
            </label>
          </li>
        ))}
      </ul>

      <div className="mt-6 border border-dashed border-ink p-4">
        <p className="label">Nunca usamos</p>
        <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-ink-2">
          {EXCLUDED_DATA.map((d) => (
            <li key={d} className="line-through decoration-red decoration-2">
              {d}
            </li>
          ))}
        </ul>
      </div>

      <label className="mt-8 flex items-start gap-3 text-sm cursor-pointer bg-tint p-4">
        <input
          type="checkbox"
          className="mt-0.5 size-4 accent-[var(--cobalt)]"
          checked={read}
          onChange={(e) => setRead(e.target.checked)}
        />
        <span>
          Li e autorizo o compartilhamento dos dados acima entre a operadora e a instituição
          financeira, nos termos da LGPD.
        </span>
      </label>

      <div className="mt-8 flex gap-3">
        <button onClick={onBack} className={btnSecondary}>
          Voltar
        </button>
        <button onClick={onAccept} disabled={!read} className={`${btnPrimary} flex-1 sm:flex-none`}>
          Autorizar e calcular <Arrow />
        </button>
      </div>
    </section>
  );
}

function AnalysisStep({ onDone }: { onDone: () => void }) {
  const [done, setDone] = useState(0);
  useEffect(() => {
    if (done >= AGENT_STEPS.length) {
      const t = setTimeout(onDone, 500);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setDone((d) => d + 1), 650);
    return () => clearTimeout(t);
  }, [done, onDone]);

  return (
    <section aria-live="polite">
      <h1 className="display text-4xl sm:text-5xl">O agente está analisando.</h1>
      <p className="mt-4 text-ink-2">Leva só alguns segundos.</p>
      <ol className="mt-8 border-t-2 border-ink">
        {AGENT_STEPS.map((s, i) => {
          const state = i < done ? "done" : i === done ? "doing" : "todo";
          return (
            <li
              key={s}
              className={`flex items-center gap-3 py-3 border-b border-rule transition-opacity ${state === "todo" ? "opacity-35" : ""}`}
            >
              <span className="num text-xs text-ink-2 w-8">{String(i + 1).padStart(2, "0")}</span>
              <span className="flex-1">{s}</span>
              <span className="num text-xs w-16 text-right">
                {state === "done" && <span className="bg-lime px-1">ok</span>}
                {state === "doing" && <span className="text-cobalt animate-pulse">lendo…</span>}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function ResultStep({
  persona,
  consent,
  onRestart,
}: {
  persona: (typeof APPLICANTS)[number];
  consent: Record<FactorKey, boolean>;
  onRestart: () => void;
}) {
  // Fatores não autorizados saem do cálculo e os pesos restantes são renormalizados.
  const factors = useMemo(() => {
    const allowed = persona.factors.filter((x) => consent[x.key]);
    const total = allowed.reduce((s, x) => s + x.weight, 0);
    return allowed.map((x) => ({ ...x, weight: x.weight / total }));
  }, [persona, consent]);

  const score = computeScore(factors);
  const decision = decide(score);
  const limit = suggestedLimit(score);
  const amount = Math.min(persona.requested, limit);
  const rate = monthlyRate(score);
  const [term, setTerm] = useState(12);
  const [revoked, setRevoked] = useState(false);
  const skipped = persona.factors.length - factors.length;

  if (revoked) {
    return (
      <section className="feed">
        <h1 className="display text-4xl sm:text-5xl">Consentimento revogado.</h1>
        <p className="mt-5 text-ink-2 leading-relaxed">
          Seus dados telecom foram descartados e o score desta solicitação foi apagado. Você pode
          simular novamente quando quiser.
        </p>
        <button onClick={onRestart} className={`${btnPrimary} mt-8`}>
          Nova simulação
        </button>
      </section>
    );
  }

  return (
    <section className="feed">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="label text-ink-2">Resultado da análise · {persona.name}</p>
        <DecisionBadge decision={decision} />
      </div>
      <h1 className="display text-3xl sm:text-4xl mt-5">
        {decision === "aprovado" && `${persona.name.split(" ")[0]}, seu crédito foi pré-aprovado.`}
        {decision === "revisao" && "Seu pedido está com um analista."}
        {decision === "recusado" && "Ainda não deu desta vez."}
      </h1>
      <p className="mt-3 text-ink-2 leading-relaxed">
        {decision === "aprovado" &&
          `${tenureLabel(persona.tenureMonths)} de relacionamento com a operadora contaram a seu favor.`}
        {decision === "revisao" &&
          "Seu score ficou na faixa intermediária. Uma pessoa do banco revisa em até 1 dia útil — o modelo nunca recusa sozinho nessa faixa."}
        {decision === "recusado" &&
          "Mas você não sai de mãos vazias: veja abaixo exatamente o que fazer para chegar lá."}
      </p>

      <div className="mt-8 border-t-2 border-ink pt-5">
        <ScoreTotal score={score} />
        <ScoreScale score={score} />
      </div>

      {decision !== "recusado" && (
        <div className="mt-4 border border-ink">
          <div className="px-5 py-3 border-b border-ink bg-tint flex justify-between gap-3">
            <h2 className="font-bold">{decision === "aprovado" ? "Sua oferta" : "Oferta prevista, sujeita à revisão"}</h2>
            {amount < persona.requested && (
              <span className="label text-ink-2 self-center">limite {brl(limit)}</span>
            )}
          </div>
          <dl className="grid grid-cols-2 sm:grid-cols-3">
            {[
              ["Valor", brl(amount)],
              ["Taxa", `${rate.toFixed(2).replace(".", ",")}% a.m.`],
              [`${term}x de`, brl2(installment(amount, rate, term))],
            ].map(([k, v], i) => (
              <div
                key={k}
                className={`px-4 sm:px-5 py-4 border-rule ${i < 2 ? "border-r" : "col-span-2 sm:col-span-1 border-t sm:border-t-0"}`}
              >
                <dt className="label text-ink-2">{k}</dt>
                <dd className={`num text-lg sm:text-2xl mt-1 whitespace-nowrap ${i === 2 ? "font-semibold" : ""}`}>{v}</dd>
              </div>
            ))}
          </dl>
          <div className="px-5 pb-5">
            <div className="flex border border-ink w-fit" role="radiogroup" aria-label="Prazo">
              {TERMS.map((t) => (
                <button
                  key={t}
                  role="radio"
                  aria-checked={t === term}
                  onClick={() => setTerm(t)}
                  className={`num whitespace-nowrap px-3 sm:px-4 py-2 text-xs border-r border-ink last:border-r-0 transition-colors ${
                    t === term ? "bg-ink text-paper" : "hover:bg-tint"
                  }`}
                >
                  {t} meses
                </button>
              ))}
            </div>
            <p className="mt-4 text-xs text-ink-2">
              Para comparação: crédito informal costuma cobrar de 10% a 30% ao mês.
            </p>
          </div>
        </div>
      )}

      <div className="mt-10">
        <h2 className="display text-2xl">Por que esse score.</h2>
        <p className="mt-2 text-sm text-ink-2">
          Cada fator vai de 0 a 100 e tem um peso fixo, igual para todas as pessoas.
          {skipped > 0 &&
            ` ${skipped} ${skipped === 1 ? "fator ficou" : "fatores ficaram"} de fora porque você não autorizou.`}
        </p>
        <div className="mt-4 border-t-2 border-ink">
          <FactorLines factors={factors} showTips />
        </div>
      </div>

      <div className="mt-10 -mx-5 sm:-mx-10 -mb-5 sm:-mb-10">
        <div className="perf text-ink" aria-hidden="true" />
        <div className="px-5 sm:px-10 py-5 bg-tint flex flex-wrap items-center gap-3">
          <button onClick={onRestart} className={`${btnSecondary} bg-paper`}>
            Simular outro perfil
          </button>
          <button
            onClick={() => setRevoked(true)}
            className="px-5 py-3.5 font-semibold text-red-ink underline hover:no-underline"
          >
            Revogar consentimento
          </button>
          <Barcode value={persona.id + score} className="hidden sm:block ml-auto h-9 w-28" />
        </div>
      </div>
    </section>
  );
}
