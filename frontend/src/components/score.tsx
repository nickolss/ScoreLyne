import {
  band,
  type Decision,
  DECISION_LABEL,
  type Factor,
  THRESHOLDS,
  fmtPts,
  pts,
} from "@/lib/data";

const STAMP: Record<Decision, string> = {
  aprovado: "bg-lime text-ink border-ink",
  revisao: "bg-paper text-ink border-ink border-dashed",
  recusado: "bg-red text-paper border-red",
};

// Carimbo de status, como o de uma fatura quitada.
export function DecisionBadge({ decision }: { decision: Decision }) {
  return (
    <span className={`label inline-block border px-2 py-1 font-semibold ${STAMP[decision]}`}>
      {DECISION_LABEL[decision]}
    </span>
  );
}

// Régua 0–1000 com os limiares desenhados: onde "recusado" vira "revisão" e "aprovado".
export function ScoreScale({ score, tone = "paper" }: { score: number; tone?: "paper" | "cobalt" }) {
  const onCobalt = tone === "cobalt";
  const line = onCobalt ? "bg-on-cobalt" : "bg-ink";
  const muted = onCobalt ? "text-on-cobalt-2" : "text-ink-2";
  const pct = (v: number) => `${v / 10}%`;
  return (
    <div className="pt-8 pb-6" role="img" aria-label={`Score ${score} na escala de 0 a 1000`}>
      <div className="relative h-3">
        {/* zonas */}
        <div className={`absolute inset-y-0 left-0 ${onCobalt ? "bg-on-cobalt/15" : "bg-tint"}`} style={{ width: pct(THRESHOLDS.review) }} />
        <div
          className="absolute inset-y-0 bg-[repeating-linear-gradient(135deg,currentColor_0_1px,transparent_1px_6px)] opacity-40"
          style={{ left: pct(THRESHOLDS.review), width: pct(THRESHOLDS.approve - THRESHOLDS.review) }}
        />
        <div className="absolute inset-y-0 right-0 bg-lime" style={{ left: pct(THRESHOLDS.approve) }} />
        {/* limiares */}
        {[THRESHOLDS.review, THRESHOLDS.approve].map((t) => (
          <div key={t} className={`absolute -top-2 -bottom-2 w-px ${line}`} style={{ left: pct(t) }}>
            <span className={`num absolute top-full mt-1 -translate-x-1/2 text-[10px] ${muted}`}>{t}</span>
          </div>
        ))}
        {/* marcador */}
        <div className="absolute -top-7 bottom-0 -translate-x-1/2 flex flex-col items-center" style={{ left: pct(score) }}>
          <span className={`num text-[11px] font-semibold px-1 ${onCobalt ? "bg-on-cobalt text-cobalt" : "bg-ink text-paper"}`}>
            {score}
          </span>
          <span className={`w-0.5 flex-1 ${line}`} />
        </div>
      </div>
      <ul className={`mt-7 flex flex-wrap gap-x-4 gap-y-1.5 label ${muted}`}>
        <li className="flex items-center gap-1.5">
          <span className={`size-2.5 border border-current ${onCobalt ? "bg-on-cobalt/15" : "bg-tint"}`} aria-hidden="true" />
          Não aprovado
        </li>
        <li className="flex items-center gap-1.5">
          <span className="size-2.5 border border-current bg-[repeating-linear-gradient(135deg,currentColor_0_1px,transparent_1px_3px)]" aria-hidden="true" />
          Revisão humana
        </li>
        <li className="flex items-center gap-1.5">
          <span className="size-2.5 border border-current bg-lime" aria-hidden="true" />
          Pré-aprovado
        </li>
      </ul>
    </div>
  );
}

export function ScoreTotal({ score }: { score: number }) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div>
        <p className="label text-ink-2">Total · de 1000</p>
        <p className="num text-6xl sm:text-7xl font-semibold leading-none mt-2">
          <span className="bg-lime px-1 -mx-1 box-decoration-clone">{score}</span>
        </p>
      </div>
      <p className="label text-ink-2 pb-1">{band(score)}</p>
    </div>
  );
}

// Fatores como itens de extrato: nota × peso = pontos.
export function FactorLines({ factors, showTips = false }: { factors: Factor[]; showTips?: boolean }) {
  return (
    <ul>
      {factors.map((x) => (
        <li key={x.key} className="py-4 border-b border-rule last:border-b-0">
          <div className="flex items-baseline gap-2">
            <span className="font-semibold">{x.label}</span>
            <span className="leader max-sm:hidden" aria-hidden="true" />
            <span className="num text-sm whitespace-nowrap ml-auto">
              <span className="text-ink-2 text-xs">
                {x.value} × {Math.round(x.weight * 100)}% ={" "}
              </span>
              {fmtPts(pts(x))}
            </span>
          </div>
          <div className="mt-2 h-1.5 bg-tint">
            <div
              className={`h-full ${x.value >= 75 ? "bg-cobalt" : x.value >= 55 ? "bg-ink" : "bg-red"}`}
              style={{ width: `${x.value}%` }}
            />
          </div>
          <p className="mt-2 text-sm text-ink-2">{x.evidence}</p>
          {showTips && x.tip && (
            <p className="mt-3 text-sm">
              <span className="bg-lime px-1 font-semibold box-decoration-clone">Como melhorar:</span>{" "}
              {x.tip}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}

// Código de barras determinístico a partir de um texto.
export function Barcode({ value, className = "" }: { value: string; className?: string }) {
  const bars: { x: number; w: number }[] = [];
  let x = 0;
  for (let i = 0; i < value.length * 3; i++) {
    const c = value.charCodeAt(i % value.length) + i * 7;
    const w = (c % 3) + 1;
    if (i % 2 === 0) bars.push({ x, w });
    x += w + ((c >> 2) % 2) + 1;
  }
  return (
    <svg viewBox={`0 0 ${x} 40`} preserveAspectRatio="none" className={className} aria-hidden="true">
      {bars.map((b, i) => (
        <rect key={i} x={b.x} y="0" width={b.w} height="40" fill="currentColor" />
      ))}
    </svg>
  );
}
