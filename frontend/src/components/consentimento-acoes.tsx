"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { consumidorNoBrowser as api } from "@/lib/api-browser";
import { mensagemDeErro, sessaoExpirada } from "@/lib/erros";
import { btnSecondary } from "./ui";

// Revogar é irreversível (apaga o score guardado), então o botão pede uma segunda confirmação na própria tela.
export function RevogarAcao({
  tipo,
  rotulo,
  consequencia,
}: {
  /** "tudo" revoga o consentimento da ScoreLyne e, junto, o pedido ao banco; "credor" retira só o pedido. */
  tipo: "tudo" | "credor";
  rotulo: string;
  consequencia: string;
}) {
  const router = useRouter();
  const [confirmando, setConfirmando] = useState(false);
  const [busy, setBusy] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function revogar() {
    setBusy(true);
    setErro(null);
    try {
      await (tipo === "tudo" ? api.revogar() : api.retirarDoCredor());
      router.refresh();
    } catch (e) {
      if (sessaoExpirada(e)) return router.replace("/cliente/entrar");
      setErro(mensagemDeErro(e));
      setBusy(false);
    }
  }

  if (!confirmando) {
    return (
      <button onClick={() => setConfirmando(true)} className={btnSecondary}>
        {rotulo}
      </button>
    );
  }

  return (
    <div className="border-2 border-red p-4" role="alertdialog" aria-label="Confirmar revogação">
      <p className="text-sm">{consequencia}</p>
      {erro && <p className="mt-2 text-sm text-red-ink">{erro}</p>}
      <div className="mt-3 flex flex-wrap gap-3">
        <button
          onClick={revogar}
          disabled={busy}
          className="bg-red-ink text-paper px-5 py-3 font-semibold hover:bg-ink transition-colors disabled:opacity-50"
        >
          {busy ? "Revogando…" : "Sim, revogar"}
        </button>
        <button onClick={() => setConfirmando(false)} disabled={busy} className={btnSecondary}>
          Cancelar
        </button>
      </div>
    </div>
  );
}
