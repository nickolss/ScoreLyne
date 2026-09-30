import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { DecisionBadge, FactorLines, ScoreScale, ScoreTotal } from "@/components/score";
import {
  APPLICANTS,
  brl,
  computeScore,
  decide,
  getApplicant,
  monthlyRate,
  suggestedLimit,
  tenureLabel,
} from "@/lib/data";
import { ReviewPanel } from "./review-panel";

export function generateStaticParams() {
  return APPLICANTS.map((a) => ({ id: a.id }));
}

export async function generateMetadata(props: PageProps<"/banco/[id]">): Promise<Metadata> {
  const { id } = await props.params;
  return { title: getApplicant(id)?.name ?? "Solicitante" };
}

export default async function ApplicantPage(props: PageProps<"/banco/[id]">) {
  const { id } = await props.params;
  const a = getApplicant(id);
  if (!a) notFound();

  const score = computeScore(a.factors);
  const decision = decide(score);
  const limit = suggestedLimit(score);

  // Contribuição de cada fator em relação a um fator "neutro" de 50 pontos.
  const ranked = [...a.factors]
    .map((x) => ({ ...x, impact: Math.round((x.value - 50) * x.weight * 10) }))
    .sort((p, q) => q.impact - p.impact);
  const strengths = ranked.filter((x) => x.impact > 0).slice(0, 2);
  const risks = ranked.filter((x) => x.impact < 0).reverse().slice(0, 2);

  const trail = [
    ["Consentimento registrado", "Finalidade: análise de crédito · validade 30 dias"],
    ["Dados recebidos da operadora", `${a.factors.length} categorias autorizadas · sem dados brutos`],
    ["Score calculado", `${score} pontos · modelo v0.3`],
    ["Checagem de equidade", "Nenhuma variável sensível ou proxy detectada"],
    [
      "Decisão do agente",
      decision === "revisao"
        ? "Faixa intermediária: encaminhado a analista"
        : decision === "aprovado"
          ? "Pré-aprovação automática"
          : "Recusa com plano de melhora enviado ao cliente",
    ],
  ];

  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-8 pb-10">
          <Link href="/banco" className="num text-xs text-on-cobalt-2 hover:text-on-cobalt underline">
            ← Solicitações
          </Link>
          <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="display text-5xl sm:text-6xl">{a.name}</h1>
              <p className="mt-3 text-on-cobalt-2">
                {a.age} anos · {a.occupation} · {a.city}
              </p>
            </div>
            <DecisionBadge decision={decision} />
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 sm:px-8 py-10 grid lg:grid-cols-[24rem_1fr] gap-8 items-start">
        <div className="space-y-8 lg:sticky lg:top-20">
          <div className="border border-ink p-5">
            <ScoreTotal score={score} />
            <ScoreScale score={score} />
            <dl className="grid grid-cols-2 border-t border-ink text-sm">
              {[
                ["Pedido", brl(a.requested), true],
                ["Limite sugerido", limit ? brl(limit) : "—", true],
                ["Plano", a.plan, false],
                ["Na base há", tenureLabel(a.tenureMonths), false],
                ["Finalidade", a.purpose, false],
                ["Taxa indicativa", limit ? `${monthlyRate(score).toFixed(2).replace(".", ",")}% a.m.` : "—", true],
              ].map(([k, v, mono], i) => (
                <div key={k as string} className={`py-3 border-b border-rule ${i % 2 ? "pl-4" : "pr-4 border-r"}`}>
                  <dt className="label text-ink-2">{k}</dt>
                  <dd className={`mt-1 ${mono ? "num" : ""}`}>{v}</dd>
                </div>
              ))}
            </dl>
          </div>

          <ReviewPanel name={a.name} decision={decision} />
        </div>

        <div className="space-y-10">
          <section>
            <h2 className="display text-2xl">Explicação do agente.</h2>
            <div className="mt-4 grid sm:grid-cols-2 border border-ink">
              <div className="p-5 sm:border-r border-b sm:border-b-0 border-ink">
                <p className="label"><span className="bg-lime px-1">A favor</span></p>
                <ul className="mt-3 space-y-3 text-sm">
                  {strengths.map((x) => (
                    <li key={x.key}>
                      <span className="flex items-baseline gap-2">
                        <span className="font-semibold">{x.label}</span>
                        <span className="leader" aria-hidden="true" />
                        <span className="num">+{x.impact}</span>
                      </span>
                      <span className="block text-ink-2 mt-0.5">{x.evidence}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="p-5">
                <p className="label"><span className="bg-red text-paper px-1">Pontos de atenção</span></p>
                {risks.length ? (
                  <ul className="mt-3 space-y-3 text-sm">
                    {risks.map((x) => (
                      <li key={x.key}>
                        <span className="flex items-baseline gap-2">
                          <span className="font-semibold">{x.label}</span>
                          <span className="leader" aria-hidden="true" />
                          <span className="num text-red-ink">{x.impact}</span>
                        </span>
                        <span className="block text-ink-2 mt-0.5">{x.evidence}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-ink-2">Nenhum fator abaixo da média.</p>
                )}
              </div>
            </div>
          </section>

          <section>
            <h2 className="display text-2xl">Fatores do score.</h2>
            <div className="mt-4 border-t-2 border-ink">
              <FactorLines factors={a.factors} />
            </div>
          </section>

          <section>
            <h2 className="display text-2xl">Trilha de auditoria.</h2>
            <ol className="mt-4 border-t-2 border-ink">
              {trail.map(([title, detail], i) => (
                <li key={title} className="grid grid-cols-[2.5rem_1fr] py-3 border-b border-rule">
                  <span className="num text-xs text-ink-2 pt-0.5">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <p className="font-semibold text-sm">{title}</p>
                    <p className="text-sm text-ink-2">{detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>
    </>
  );
}
