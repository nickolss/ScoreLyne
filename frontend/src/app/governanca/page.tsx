import type { Metadata } from "next";
import { EXCLUDED_DATA, FACTOR_META, THRESHOLDS } from "@/lib/data";

export const metadata: Metadata = { title: "Governança" };

const PRINCIPLES = [
  {
    title: "Equidade e antibias",
    body: "O modelo só consome fatores de comportamento de uso. Taxas de aprovação são monitoradas por região e faixa etária para detectar efeitos discriminatórios indiretos.",
  },
  {
    title: "Transparência e explicabilidade",
    body: "Todo score vem com a contribuição de cada fator. Quem é aprovado entende o porquê; quem é recusado recebe o que fazer para melhorar.",
  },
  {
    title: "Privacidade (LGPD)",
    body: "Consentimento explícito, granular e revogável antes de qualquer uso. O banco recebe fatores agregados, nunca o histórico bruto da linha.",
  },
  {
    title: "Supervisão humana",
    body: `Scores entre ${THRESHOLDS.review} e ${THRESHOLDS.approve} sempre passam por um analista. Qualquer decisão automática pode ser sobreposta, com justificativa registrada.`,
  },
  {
    title: "Conformidade",
    body: "Alinhado às diretrizes do Banco Central para concessão de crédito e da ANPD para tratamento de dados pessoais.",
  },
];

export default function GovernancaPage() {
  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 py-16">
          <h1 className="display text-[clamp(2.5rem,6vw,4.75rem)] max-w-5xl">
            Decisões de crédito que dá para{" "}
            <span className="bg-lime text-ink px-2 box-decoration-clone">explicar, auditar e contestar.</span>
          </h1>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 sm:px-8 py-16 grid lg:grid-cols-[1.4fr_1fr] gap-12 lg:gap-16 items-start">
        <ol className="border-t-2 border-ink">
          {PRINCIPLES.map((p, i) => (
            <li key={p.title} className="py-7 grid grid-cols-[3.5rem_1fr] border-b border-rule">
              <span className="num text-sm text-cobalt pt-1.5">§ {i + 1}</span>
              <div>
                <h2 className="text-2xl font-bold">{p.title}</h2>
                <p className="mt-2 text-ink-2 leading-relaxed max-w-[62ch]">{p.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <aside className="space-y-8 lg:sticky lg:top-20">
          <div className="border border-ink">
            <h2 className="px-5 py-3 border-b border-ink bg-tint font-bold">O que entra no modelo</h2>
            <ul className="px-5 py-2 text-sm">
              {Object.values(FACTOR_META).map((m) => (
                <li key={m.label} className="flex items-baseline gap-2 py-2">
                  <span>{m.label}</span>
                  <span className="leader" aria-hidden="true" />
                  <span className="num">{Math.round(m.weight * 100)}%</span>
                </li>
              ))}
              <li className="flex items-baseline gap-2 py-2 border-t-2 border-ink mt-1 font-semibold">
                <span>Total</span>
                <span className="leader" aria-hidden="true" />
                <span className="num">100%</span>
              </li>
            </ul>
          </div>
          <div className="border border-dashed border-ink">
            <h2 className="px-5 py-3 border-b border-dashed border-ink font-bold">O que nunca entra</h2>
            <ul className="px-5 py-4 space-y-2 text-sm text-ink-2">
              {EXCLUDED_DATA.map((d) => (
                <li key={d} className="line-through decoration-red decoration-2">
                  {d}
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </>
  );
}
