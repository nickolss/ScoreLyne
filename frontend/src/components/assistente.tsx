"use client";

import { consumidorNoBrowser } from "@/lib/api-browser";
import { Chat, type Msg } from "./chat";

const paraApi = (h: Msg[]) =>
  h.map((m) => ({ papel: m.de === "usuario" ? ("cliente" as const) : ("assistente" as const), texto: m.texto }));

// Assistente do consumidor: explica a nota da própria pessoa, só com os dados dela. Não decide crédito.
export function AssistenteScore() {
  return (
    <Chat
      id="assistente"
      titulo="Pergunte ao assistente"
      apresentacao="Quer entender sua nota? Pergunte por que ela ficou assim, o que dá para melhorar ou o que mudaria se você pedisse outro valor. O assistente só enxerga os seus dados e não decide crédito."
      placeholder="Ex.: por que minha pontualidade pesou tanto?"
      desligado="O assistente está desligado: configure WATSONX_APIKEY e WATSONX_PROJECT_ID (ou ORCHESTRATE_URL e ORCHESTRATE_CONSUMIDOR_AGENT_ID) no backend/.env."
      carregarStatus={consumidorNoBrowser.assistente}
      perguntar={(h) => consumidorNoBrowser.perguntarAoAssistente(paraApi(h))}
    />
  );
}
