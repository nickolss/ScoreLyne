"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, banco, type Decisao, type RevisaoHumana } from "@/lib/api";

export function ReviewPanel({
  id,
  name,
  agentDecision,
  review,
  reasons,
}: {
  id: string;
  name: string;
  agentDecision: Decisao;
  review: RevisaoHumana | null;
  reasons: string[];
}) {
  const router = useRouter();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const needsReview = agentDecision === "revisao";

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      setNote("");
      // Recarrega o server component com a solicitação e a trilha atualizadas.
      router.refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Não foi possível salvar. Tente de novo.");
    } finally {
      setBusy(false);
    }
  }

  if (review) {
    const ok = review.veredito === "aprovar";
    return (
      <div className="border border-ink" role="status">
        <p className={`label px-5 py-2 ${ok ? "bg-lime" : "bg-red text-paper"}`}>
          {ok ? "Crédito aprovado pelo analista" : "Crédito recusado pelo analista"}
        </p>
        <div className="p-5">
          <p className="label text-ink-2">Justificativa registrada · {review.analista}</p>
          <p className="mt-2">&ldquo;{review.justificativa}&rdquo;</p>
          <p className="mt-3 text-sm text-ink-2">
            {name.split(" ")[0]} vê a decisão e a justificativa na tela do pedido.
          </p>
          {error && <p className="mt-3 text-sm text-red-ink">{error}</p>}
          <button
            onClick={() => run(() => banco.desfazer(id))}
            disabled={busy}
            className="mt-4 text-sm font-semibold underline hover:no-underline disabled:opacity-50"
          >
            Desfazer
          </button>
        </div>
      </div>
    );
  }

  const ready = note.trim().length >= 10 && !busy;

  return (
    <div className={`border ${needsReview ? "border-ink border-2" : "border-ink"}`}>
      <div className={`px-5 py-3 border-b border-ink ${needsReview ? "bg-ink text-paper" : "bg-tint"}`}>
        <h2 className="font-bold">{needsReview ? "Sua decisão é necessária" : "Revisar decisão do agente"}</h2>
        <p className={`text-sm mt-0.5 ${needsReview ? "text-paper/75" : "text-ink-2"}`}>
          {needsReview
            ? "O agente não decide sozinho neste caso."
            : "Analistas podem sobrepor qualquer decisão automática, com justificativa."}
        </p>
      </div>
      <div className="p-5">
        {needsReview && reasons.length > 0 && (
          <ul className="mb-4 text-sm space-y-1">
            {reasons.map((r) => (
              <li key={r}>· {r}</li>
            ))}
          </ul>
        )}
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
        {error && <p className="mt-2 text-sm text-red-ink">{error}</p>}
        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            disabled={!ready}
            onClick={() => run(() => banco.decidir(id, { veredito: "aprovar", justificativa: note.trim() }))}
            className="bg-ink text-paper py-3 text-sm font-semibold hover:bg-cobalt transition-colors disabled:opacity-35 disabled:hover:bg-ink disabled:cursor-not-allowed"
          >
            Aprovar
          </button>
          <button
            disabled={!ready}
            onClick={() => run(() => banco.decidir(id, { veredito: "recusar", justificativa: note.trim() }))}
            className="border border-red-ink text-red-ink py-3 text-sm font-semibold hover:bg-red hover:text-paper hover:border-red transition-colors disabled:opacity-35 disabled:hover:bg-transparent disabled:hover:text-red-ink disabled:cursor-not-allowed"
          >
            Recusar
          </button>
        </div>
      </div>
    </div>
  );
}
