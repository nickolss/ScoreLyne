// Clientes para componentes de navegador. Nada aqui conhece o token: as chamadas vão para o proxy
// /api/<serviço> (app/api/[servico]/[...caminho]/route.ts), que lê o cookie httpOnly e repassa ao backend.

import { type Fetcher, criarConsumidor, criarCredor } from "./api";

const via =
  (servico: "consumidor" | "credor"): Fetcher =>
  (caminho, init) =>
    fetch(`/api/${servico}${caminho}`, {
      ...init,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        // Cabeçalho próprio: um site de fora não consegue enviá-lo sem passar por CORS (que não liberamos).
        "x-scorelyne": "1",
        ...init?.headers,
      },
    });

export const consumidorNoBrowser = criarConsumidor(via("consumidor"));
export const credorNoBrowser = criarCredor(via("credor"));
