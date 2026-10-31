"use client";

import { credorNoBrowser } from "@/lib/api-browser";
import { Chat, type Msg } from "./chat";

const paraApi = (h: Msg[]) =>
  h.map((m) => ({ papel: m.de === "usuario" ? ("analista" as const) : ("copiloto" as const), texto: m.texto }));

// Copiloto do analista: fila, scores e modelo. Consulta os dados do credor, mas não decide.
export function Copilot({ suggestions }: { suggestions?: string[] }) {
  return (
    <Chat
      id="copiloto"
      titulo="Copiloto de crédito"
      apresentacao="Pergunte sobre a fila, um score ou o modelo. O copiloto consulta os dados do banco, mas não decide: aprovar ou recusar continua sendo seu."
      placeholder="Ex.: e se a Ana pedisse R$ 400?"
      desligado="Configure WATSONX_APIKEY e ORCHESTRATE_URL / ORCHESTRATE_AGENT_ID no backend/.env para ligar o copiloto."
      carregarStatus={credorNoBrowser.copiloto}
      perguntar={(h) => credorNoBrowser.perguntar(paraApi(h))}
      sugestoes={suggestions}
    />
  );
}
