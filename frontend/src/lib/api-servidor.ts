// Clientes para o servidor do Next (server components, server actions e o proxy /api).
// Chamam o backend direto e levam o token do cookie httpOnly; o navegador nunca vê o token.
// Só importe este arquivo em código de servidor.

import { cookies } from "next/headers";
import { type Fetcher, criarConsumidor, criarCredor, criarOperadora } from "./api";

export type Servico = "consumidor" | "credor";

export const COOKIE: Record<Servico, string> = {
  consumidor: "sl_consumidor",
  credor: "sl_credor",
};

export const URLS = {
  consumidor: process.env.CONSUMIDOR_URL ?? "http://localhost:8003",
  credor: process.env.CREDOR_URL ?? "http://localhost:8002",
  operadora: process.env.OPERADORA_URL ?? "http://localhost:8001",
};

// O token do backend vale 60 minutos; o cookie expira junto.
export const DURACAO_SESSAO_S = 60 * 60;

export function fetcher(base: string, token?: string): Fetcher {
  return (caminho, init) =>
    fetch(`${base}${caminho}`, {
      ...init,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });
}

export async function tokenDe(servico: Servico): Promise<string | undefined> {
  return (await cookies()).get(COOKIE[servico])?.value;
}

/** Cliente do consumidor com o token da sessão, ou null se a pessoa não estiver logada. */
export async function consumidorLogado() {
  const token = await tokenDe("consumidor");
  return token ? criarConsumidor(fetcher(URLS.consumidor, token)) : null;
}

/** Cliente do credor com o token do analista, ou null se não houver sessão. */
export async function credorLogado() {
  const token = await tokenDe("credor");
  return token ? criarCredor(fetcher(URLS.credor, token)) : null;
}

// Rotas públicas dos backends: sem token.
export const consumidorPublico = criarConsumidor(fetcher(URLS.consumidor));
export const credorPublico = criarCredor(fetcher(URLS.credor));
export const operadoraPublica = criarOperadora(fetcher(URLS.operadora));
