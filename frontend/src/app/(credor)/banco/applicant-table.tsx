"use client";

import Link from "next/link";
import { useState } from "react";
import { DecisionBadge } from "@/components/score";
import type { SolicitacaoResumo, Status } from "@/lib/api";
import { DECISION_LABEL, PLAN_LABEL, THRESHOLDS, brl } from "@/lib/data";

const FILTERS: ("todas" | Status)[] = ["todas", "revisao", "aprovado", "recusado", "revogado"];

const dateFmt = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

// Mini-régua do score com os limiares, legível numa linha de tabela.
function ScoreTick({ score }: { score: number | null }) {
  if (score === null) return <span className="num text-ink-2 block text-right">—</span>;
  return (
    <div className="flex items-center justify-end gap-3">
      <div className="relative w-24 h-2 bg-tint hidden md:block" aria-hidden="true">
        <div className="absolute inset-y-0 bg-lime" style={{ left: `${THRESHOLDS.approve / 10}%`, right: 0 }} />
        {[THRESHOLDS.review, THRESHOLDS.approve].map((t) => (
          <div key={t} className="absolute -inset-y-0.5 w-px bg-ink-2" style={{ left: `${t / 10}%` }} />
        ))}
        <div className="absolute -inset-y-1 w-0.5 bg-ink" style={{ left: `${score / 10}%` }} />
      </div>
      <span className="num text-base font-semibold w-10 text-right">{score}</span>
    </div>
  );
}

export function ApplicantTable({ rows }: { rows: SolicitacaoResumo[] }) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("todas");
  const visible = filter === "todas" ? rows : rows.filter((r) => r.status === filter);

  return (
    <div>
      <div className="flex flex-wrap border border-ink w-fit" role="tablist" aria-label="Filtrar por decisão">
        {FILTERS.map((f) => {
          const count = f === "todas" ? rows.length : rows.filter((r) => r.status === f).length;
          const active = f === filter;
          return (
            <button
              key={f}
              role="tab"
              aria-selected={active}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 text-sm font-semibold border-r border-ink last:border-r-0 transition-colors ${
                active ? "bg-ink text-paper" : "hover:bg-tint"
              }`}
            >
              {f === "todas" ? "Todas" : DECISION_LABEL[f]}{" "}
              <span className={`num text-xs ${active ? "text-paper/70" : "text-ink-2"}`}>{count}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-5 overflow-x-auto border border-ink">
        <table className="w-full text-sm min-w-[46rem]">
          <thead className="text-left">
            <tr className="border-b-2 border-ink">
              <th className="label font-normal px-5 py-3">Solicitante</th>
              <th className="label font-normal px-5 py-3">Plano</th>
              <th className="label font-normal px-5 py-3 text-right">Pedido</th>
              <th className="label font-normal px-5 py-3 text-right">Score</th>
              <th className="label font-normal px-5 py-3">Situação</th>
              <th className="label font-normal px-5 py-3">Recebido</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.id} className="group relative border-b border-rule last:border-b-0 hover:bg-tint">
                <td className="px-5 py-4">
                  {/* o link cobre a linha inteira via ::after */}
                  <Link
                    href={`/banco/${r.id}`}
                    className="font-bold after:absolute after:inset-0 group-hover:underline focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:outline-cobalt focus-visible:after:-outline-offset-2"
                  >
                    {r.nome}
                  </Link>
                  <span className="block text-ink-2">{r.ocupacao}</span>
                </td>
                <td className="px-5 py-4 text-ink-2">{r.plano ? PLAN_LABEL[r.plano] : "—"}</td>
                <td className="px-5 py-4 text-right num">{brl(r.valor_solicitado)}</td>
                <td className="px-5 py-4">
                  <ScoreTick score={r.score} />
                </td>
                <td className="px-5 py-4">
                  <DecisionBadge decision={r.status} />
                  {r.status !== r.decisao_agente && r.status !== "revogado" && (
                    <span className="block mt-1 text-xs text-ink-2">agente: {DECISION_LABEL[r.decisao_agente]}</span>
                  )}
                </td>
                <td className="px-5 py-4 num text-xs text-ink-2">{dateFmt.format(new Date(r.criado_em))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
