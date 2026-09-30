"use client";

import { useState } from "react";
import type { Decision } from "@/lib/data";

type Outcome = { verdict: "aprovar" | "recusar"; note: string };

export function ReviewPanel({ name, decision }: { name: string; decision: Decision }) {
  const [note, setNote] = useState("");
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const needsReview = decision === "revisao";

  if (outcome) {
    const ok = outcome.verdict === "aprovar";
    return (
      <div className="border border-ink" role="status">
        <p className={`label px-5 py-2 ${ok ? "bg-lime" : "bg-red text-paper"}`}>
          {ok ? "Crédito aprovado pelo analista" : "Crédito recusado pelo analista"}
        </p>
        <div className="p-5">
          <p className="label text-ink-2">Justificativa registrada</p>
          <p className="mt-2">“{outcome.note}”</p>
          <p className="mt-3 text-sm text-ink-2">
            {name.split(" ")[0]} recebe a justificativa e, em caso de recusa, o plano de melhora.
          </p>
          <button onClick={() => setOutcome(null)} className="mt-4 text-sm font-semibold underline hover:no-underline">
            Desfazer
          </button>
        </div>
      </div>
    );
  }

  const ready = note.trim().length >= 10;

  return (
    <div className={`border ${needsReview ? "border-ink border-2" : "border-ink"}`}>
      <div className={`px-5 py-3 border-b border-ink ${needsReview ? "bg-ink text-paper" : "bg-tint"}`}>
        <h2 className="font-bold">{needsReview ? "Sua decisão é necessária" : "Revisar decisão do agente"}</h2>
        <p className={`text-sm mt-0.5 ${needsReview ? "text-paper/75" : "text-ink-2"}`}>
          {needsReview
            ? "Score na faixa intermediária. O agente não decide sozinho aqui."
            : "Analistas podem sobrepor qualquer decisão automática, com justificativa."}
        </p>
      </div>
      <div className="p-5">
        <label htmlFor="note" className="label">
          Justificativa
        </label>
        <textarea
          id="note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          placeholder="Ex.: histórico de recargas compensa o tempo curto de base"
          className="mt-2 w-full border border-ink bg-paper p-3 text-sm placeholder:text-ink-2 focus:outline-2 focus:outline-cobalt focus:-outline-offset-1"
        />
        <p className="mt-1 text-xs text-ink-2">Obrigatória, mínimo de 10 caracteres. Fica na trilha de auditoria.</p>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            disabled={!ready}
            onClick={() => setOutcome({ verdict: "aprovar", note: note.trim() })}
            className="bg-ink text-paper py-3 text-sm font-semibold hover:bg-cobalt transition-colors disabled:opacity-35 disabled:hover:bg-ink disabled:cursor-not-allowed"
          >
            Aprovar
          </button>
          <button
            disabled={!ready}
            onClick={() => setOutcome({ verdict: "recusar", note: note.trim() })}
            className="border border-red-ink text-red-ink py-3 text-sm font-semibold hover:bg-red hover:text-paper hover:border-red transition-colors disabled:opacity-35 disabled:hover:bg-transparent disabled:hover:text-red-ink disabled:cursor-not-allowed"
          >
            Recusar
          </button>
        </div>
      </div>
    </div>
  );
}
