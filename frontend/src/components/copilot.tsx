"use client";

import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ApiError, banco, type MensagemCopiloto, type StatusCopiloto } from "@/lib/api";

// Chat com o copiloto do analista. O backend encaminha para o agente do watsonx Orchestrate
// (ou para um modelo do watsonx.ai) e devolve a resposta em markdown.
export function Copilot({ suggestions }: { suggestions?: string[] }) {
  const [status, setStatus] = useState<StatusCopiloto | null>(null);
  const [offline, setOffline] = useState(false);
  const [messages, setMessages] = useState<MensagemCopiloto[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [via, setVia] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    banco
      .copiloto()
      .then(setStatus)
      .catch(() => setOffline(true));
  }, []);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, busy]);

  async function ask(text: string) {
    const question = text.trim();
    if (!question || busy) return;
    const history: MensagemCopiloto[] = [...messages, { papel: "analista", texto: question }];
    setMessages(history);
    setDraft("");
    setBusy(true);
    setError(null);
    try {
      const r = await banco.perguntar(history);
      setMessages([...history, { papel: "copiloto", texto: r.resposta || "(sem resposta)" }]);
      setVia(`${r.provedor} · ${r.modelo}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Não foi possível falar com o copiloto.");
    } finally {
      setBusy(false);
    }
  }

  const prompts = suggestions ?? status?.perguntas ?? [];
  const enabled = status?.disponivel && !offline;

  return (
    <section className="border border-ink" aria-labelledby="copilot-title">
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-ink bg-tint px-5 py-3">
        <h2 id="copilot-title" className="font-semibold">
          Copiloto de crédito
        </h2>
        <p className="label text-ink-2">
          {enabled ? (via ?? `${status?.provedor} · ${status?.modelo}`) : "desligado"}
        </p>
      </header>

      <div className="max-h-[32rem] overflow-y-auto px-5 py-4 space-y-4" aria-live="polite">
        {!enabled && (
          <p className="text-sm text-ink-2">
            {offline
              ? "Não foi possível consultar o banco."
              : "Configure WATSONX_APIKEY e ORCHESTRATE_URL / ORCHESTRATE_AGENT_ID no backend/.env para ligar o copiloto."}
          </p>
        )}

        {enabled && messages.length === 0 && (
          <div>
            <p className="text-sm text-ink-2">
              Pergunte sobre a fila, um score ou o modelo. O copiloto consulta os dados do banco, mas não
              decide: aprovar ou recusar continua sendo seu.
            </p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {prompts.map((p) => (
                <li key={p}>
                  <button
                    onClick={() => ask(p)}
                    className="border border-ink px-3 py-1.5 text-left text-sm hover:bg-lime"
                  >
                    {p}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {messages.map((m, i) =>
          m.papel === "analista" ? (
            <div key={i} className="ml-auto max-w-[85%] w-fit bg-cobalt text-on-cobalt px-4 py-2">
              {m.texto}
            </div>
          ) : (
            <div key={i} className="md max-w-full border-l-2 border-cobalt pl-4">
              <Markdown remarkPlugins={[remarkGfm]}>{m.texto}</Markdown>
            </div>
          ),
        )}

        {busy && (
          <p className="label text-ink-2" role="status">
            Consultando o agente…
          </p>
        )}
        {error && <p className="text-sm text-red-ink">{error}</p>}
        <div ref={end} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(draft);
        }}
        className="flex border-t border-ink"
      >
        <label htmlFor="copilot-input" className="sr-only">
          Pergunta para o copiloto
        </label>
        <input
          id="copilot-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={!enabled || busy}
          placeholder={enabled ? "Ex.: e se a Ana pedisse R$ 400?" : "Copiloto desligado"}
          className="min-w-0 flex-1 bg-paper px-5 py-3 outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!enabled || busy || !draft.trim()}
          className="border-l border-ink bg-ink px-5 font-semibold text-paper hover:bg-cobalt disabled:opacity-40"
        >
          Enviar
        </button>
      </form>
    </section>
  );
}
