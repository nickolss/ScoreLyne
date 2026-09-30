import type { Metadata } from "next";
import { APPLICANTS, THRESHOLDS, brl, computeScore, decide } from "@/lib/data";
import { ApplicantTable, type Row } from "./applicant-table";

export const metadata: Metadata = { title: "Painel do banco" };

export default function BancoPage() {
  const rows: Row[] = APPLICANTS.map((a) => {
    const score = computeScore(a.factors);
    return {
      id: a.id,
      name: a.name,
      occupation: a.occupation,
      plan: a.plan,
      requested: a.requested,
      submittedAt: a.submittedAt,
      score,
      decision: decide(score),
    };
  });

  const approved = rows.filter((r) => r.decision === "aprovado");
  const review = rows.filter((r) => r.decision === "revisao");
  const volume = approved.reduce((s, r) => s + r.requested, 0);

  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-12 pb-10">
          <p className="num text-sm text-on-cobalt-2">Microcrédito · últimos 7 dias</p>
          <h1 className="display text-5xl sm:text-6xl mt-3">Solicitações</h1>
          <p className="mt-5 text-on-cobalt-2 max-w-2xl leading-relaxed">
            Todos os solicitantes abaixo foram recusados ou não pontuam nos birôs tradicionais. O score
            ScoreLyne é complementar: acima de {THRESHOLDS.approve} o agente pré-aprova, entre{" "}
            {THRESHOLDS.review} e {THRESHOLDS.approve} a decisão é de um analista.
          </p>
          <dl className="mt-10 grid grid-cols-2 lg:grid-cols-4 border-t border-on-cobalt/40">
            {[
              ["Solicitações", String(rows.length)],
              ["Pré-aprovadas", String(approved.length)],
              ["Aguardando analista", String(review.length)],
              ["Volume pré-aprovado", brl(volume)],
            ].map(([k, v], i) => (
              <div key={k} className={`pt-4 pb-1 pr-4 ${i > 0 ? "lg:pl-6 lg:border-l border-on-cobalt/40" : ""}`}>
                <dt className="label text-on-cobalt-2">{k}</dt>
                <dd className="num text-3xl mt-2">
                  {k === "Aguardando analista" && review.length > 0 ? (
                    <span className="bg-lime text-ink px-1">{v}</span>
                  ) : (
                    v
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </section>
      <div className="mx-auto max-w-7xl px-4 sm:px-8 py-10">
        <ApplicantTable rows={rows} />
      </div>
    </>
  );
}
