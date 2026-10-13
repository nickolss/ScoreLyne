"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Arrow } from "@/components/icons";
import { Barcode } from "@/components/score";
import { MARIA_RECHARGES, MARIA_SNAPSHOT as maria, fmtPts } from "@/lib/data";

const ROWS = 8;
const STEP = 110; // ms entre linhas impressas

function useCountUp(target: number, delay: number) {
  const [value, setValue] = useState(target);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const start = performance.now() + delay;
    const dur = 1100;
    const tick = (now: number) => {
      const t = Math.min(1, Math.max(0, (now - start) / dur));
      setValue(Math.round(target * (1 - Math.pow(1 - t, 4))));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, delay]);
  return value;
}

export function MariaStatement() {
  const score = maria.score;
  const rows = MARIA_RECHARGES.slice(0, ROWS);
  const factorStart = (ROWS + 2) * STEP;
  const totalAt = factorStart + (maria.factors.length + 2) * STEP;
  const shown = useCountUp(score, totalAt);
  let n = 0;
  const d = () => ({ animationDelay: `${n++ * STEP}ms` });

  return (
    <article
      aria-label="Extrato ilustrativo da Maria"
      className="feed relative bg-paper text-ink shadow-[0_24px_48px_-20px_rgb(5_12_60/0.55)]"
    >
      <header className="px-5 sm:px-6 pt-5 pb-4 border-b border-ink">
        <div className="flex items-start justify-between gap-4">
          <p className="display text-lg leading-none">Extrato de relacionamento</p>
          <span className="label border border-ink px-1.5 py-0.5 shrink-0">Ilustrativo</span>
        </div>
        <dl className="mt-4 grid grid-cols-[1fr_auto_auto] gap-3 sm:gap-5 text-xs">
          <div>
            <dt className="label text-ink-2">Titular</dt>
            <dd className="font-semibold mt-0.5">{maria.name}</dd>
          </div>
          <div>
            <dt className="label text-ink-2">Linha</dt>
            <dd className="num mt-0.5 whitespace-nowrap">{maria.phone}</dd>
          </div>
          <div>
            <dt className="label text-ink-2">Desde</dt>
            <dd className="num mt-0.5">{maria.since}</dd>
          </div>
        </dl>
      </header>

      <div className="px-5 sm:px-6 pt-3">
        <p className="label text-ink-2 print" style={d()}>
          Recargas · últimos {ROWS} de {maria.months} meses
        </p>
        <table className="w-full mt-1 text-xs">
          <tbody>
            {rows.map((r) => (
              <tr key={r.date} className="print border-b border-rule" style={d()}>
                <td className="num py-1.5 text-ink-2 w-[6.5rem]">{r.date}</td>
                <td className="py-1.5">{r.amount ? "Recarga pré-paga" : "Sem recarga no mês"}</td>
                <td className={`num py-1.5 text-right ${r.amount ? "" : "text-red-ink"}`}>
                  {r.amount ? `R$ ${r.amount},00` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-5 sm:px-6 pt-4">
        <p className="label text-ink-2 print" style={{ animationDelay: `${factorStart - STEP}ms` }}>
          Pontos por fator
        </p>
        <ul className="mt-1 text-xs">
          <li className="print flex items-baseline gap-2 py-1 text-ink-2" style={{ animationDelay: `${factorStart}ms` }}>
            <span>Cliente médio da base</span>
            <span className="leader" aria-hidden="true" />
            <span className="num">{fmtPts(maria.base, false)}</span>
          </li>
          {maria.factors.map((x, i) => (
            <li
              key={x.key}
              className="print flex items-baseline gap-2 py-1"
              style={{ animationDelay: `${factorStart + (i + 1) * STEP}ms` }}
            >
              <span>{x.label}</span>
              <span className="leader" aria-hidden="true" />
              <span className={`num ${x.points < 0 ? "text-red-ink" : ""}`}>{fmtPts(x.points)}</span>
            </li>
          ))}
        </ul>
      </div>

      <div
        className="print mx-5 sm:mx-6 mt-3 border-t-2 border-ink pt-3 pb-5 flex items-end justify-between"
        style={{ animationDelay: `${totalAt}ms` }}
      >
        <span className="display text-xl leading-none">Total</span>
        <span className="num text-5xl font-semibold leading-none">
          <span className="bg-lime px-1.5" aria-label={`${score} de 1000`}>
            {shown}
          </span>
        </span>
      </div>

      {/* canhoto destacável: a ação principal */}
      <div className="relative text-ink">
        <div className="perf" aria-hidden="true" />
        <div className="px-5 sm:px-6 py-4 flex items-center gap-4 bg-tint">
          <Link
            href="/cliente"
            className="group flex-1 flex items-center justify-between gap-3 bg-ink text-paper px-4 py-3 font-semibold hover:bg-cobalt-deep transition-colors"
          >
            Simular meu score
            <span className="transition-transform group-hover:translate-x-1">
              <Arrow />
            </span>
          </Link>
          <Barcode value={`MARIA-${score}`} className="hidden sm:block h-10 w-28 text-ink" />
        </div>
      </div>
    </article>
  );
}
