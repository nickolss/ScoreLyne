"use client";

import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ApiError, type RespostaChat, type StatusChat } from "@/lib/api";

export type Msg = { de: "usuario" | "ia"; texto: string };

export type ChatProps = {
  /** Título e texto de apoio no cabeçalho do chat. */
  titulo: string;
  apresentacao: string;
  placeholder: string;
  /** Mensagem mostrada quando o backend não tem as credenciais da IBM configuradas. */
  desligado: string;
  /** Rótulo para leitores de tela e id único do campo. */
  id: string;
  carregarStatus: () => Promise<StatusChat>;
  perguntar: (historico: Msg[]) => Promise<RespostaChat>;
  sugestoes?: string[];
};

// Chat com a IA da IBM (watsonx Orchestrate ou watsonx.ai). O backend responde em markdown.
// Serve ao copiloto do analista e ao assistente do consumidor: cada um passa o seu cliente de API.
export function Chat({ titulo, apresentacao, placeholder, desligado, id, carregarStatus, perguntar, sugestoes }: ChatProps) {
  const [status, setStatus] = useState<StatusChat | null>(null);
  const [offline, setOffline] = useState(false);
  const [mensagens, setMensagens] = useState<Msg[]>([]);
  const [rascunho, setRascunho] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [via, setVia] = useState<string | null>(null);
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    carregarStatus()
      .then(setStatus)
      .catch(() => setOffline(true));
  }, [carregarStatus]);

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [mensagens, ocupado]);

  async function enviar(texto: string) {
    const pergunta = texto.trim();
    if (!pergunta || ocupado) return;
    const historico: Msg[] = [...mensagens, { de: "usuario", texto: pergunta }];
    setMensagens(historico);
    setRascunho("");
    setOcupado(true);
    setErro(null);
    try {
      const r = await perguntar(historico);
      setMensagens([...historico, { de: "ia", texto: r.resposta || "(sem resposta)" }]);
      setVia(`${r.provedor} · ${r.modelo}`);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Não foi possível falar com a IA.");
    } finally {
      setOcupado(false);
    }
  }

  const perguntas = sugestoes ?? status?.perguntas ?? [];
  const ligado = status?.disponivel && !offline;

  return (
    <section className="border border-ink" aria-labelledby={`${id}-titulo`}>
      <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-ink bg-tint px-5 py-3">
        <h2 id={`${id}-titulo`} className="font-semibold">
          {titulo}
        </h2>
        <p className="label text-ink-2">{ligado ? (via ?? `${status?.provedor} · ${status?.modelo}`) : "desligado"}</p>
      </header>

      <div className="max-h-[32rem] overflow-y-auto px-5 py-4 space-y-4" aria-live="polite">
        {!ligado && <p className="text-sm text-ink-2">{offline ? "Não foi possível consultar o serviço." : desligado}</p>}

        {ligado && mensagens.length === 0 && (
          <div>
            <p className="text-sm text-ink-2">{apresentacao}</p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {perguntas.map((p) => (
                <li key={p}>
                  <button onClick={() => enviar(p)} className="border border-ink px-3 py-1.5 text-left text-sm hover:bg-lime">
                    {p}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {mensagens.map((m, i) =>
          m.de === "usuario" ? (
            <div key={i} className="ml-auto max-w-[85%] w-fit bg-cobalt text-on-cobalt px-4 py-2">
              {m.texto}
            </div>
          ) : (
            <div key={i} className="md max-w-full border-l-2 border-cobalt pl-4">
              <Markdown remarkPlugins={[remarkGfm]}>{m.texto}</Markdown>
            </div>
          ),
        )}

        {ocupado && (
          <p className="label text-ink-2" role="status">
            Consultando o agente…
          </p>
        )}
        {erro && <p className="text-sm text-red-ink">{erro}</p>}
        <div ref={fim} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          enviar(rascunho);
        }}
        className="flex border-t border-ink"
      >
        <label htmlFor={`${id}-campo`} className="sr-only">
          {titulo}
        </label>
        <input
          id={`${id}-campo`}
          value={rascunho}
          onChange={(e) => setRascunho(e.target.value)}
          disabled={!ligado || ocupado}
          placeholder={ligado ? placeholder : "Desligado"}
          maxLength={4000}
          className="min-w-0 flex-1 bg-paper px-5 py-3 outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!ligado || ocupado || !rascunho.trim()}
          className="border-l border-ink bg-ink px-5 font-semibold text-paper hover:bg-cobalt disabled:opacity-40"
        >
          Enviar
        </button>
      </form>
    </section>
  );
}
