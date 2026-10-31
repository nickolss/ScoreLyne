// Proxy do navegador para os backends. Lê o token do cookie httpOnly e o envia ao serviço certo.
//
// Não é um proxy aberto: só passam as rotas listadas abaixo. Fora da lista ficam o login, o cadastro e
// tudo que é chave de serviço ou de agente (criar/revogar solicitação, simulação do agente).

import type { NextRequest } from "next/server";
import { COOKIE, type Servico, URLS, tokenDe } from "@/lib/api-servidor";

type Regra = readonly [metodo: string, caminho: RegExp];

const PERMITIDAS: Record<Servico, Regra[]> = {
  consumidor: [
    ["GET", /^\/me$/],
    ["PATCH", /^\/meus-dados$/],
    ["POST", /^\/consentimentos$/],
    ["POST", /^\/meu-score$/],
    ["GET", /^\/meu-score$/],
    ["POST", /^\/revogar$/],
    ["POST", /^\/enviar-ao-credor$/],
    ["GET", /^\/minha-solicitacao$/],
    ["POST", /^\/retirar-do-credor$/],
    ["GET", /^\/assistente$/],
    ["POST", /^\/assistente$/],
    ["GET", /^\/formulas$/],
  ],
  credor: [
    ["GET", /^\/solicitacoes$/],
    ["GET", /^\/solicitacoes\/[\w-]+$/],
    ["POST", /^\/solicitacoes\/[\w-]+\/decisao$/],
    ["DELETE", /^\/solicitacoes\/[\w-]+\/decisao$/],
    ["GET", /^\/copiloto$/],
    ["POST", /^\/copiloto$/],
    ["GET", /^\/modelo$/],
    ["GET", /^\/formulas$/],
  ],
};

const resposta = (status: number, corpo: unknown) =>
  Response.json(corpo, { status, headers: { "Cache-Control": "no-store" } });

async function tratar(req: NextRequest, ctx: RouteContext<"/api/[servico]/[...caminho]">) {
  const { servico, caminho } = await ctx.params;
  if (servico !== "consumidor" && servico !== "credor") return resposta(404, { detail: "Serviço desconhecido" });

  const rota = `/${caminho.join("/")}`;
  if (!PERMITIDAS[servico].some(([m, r]) => m === req.method && r.test(rota))) {
    return resposta(404, { detail: "Rota não disponível" });
  }
  // Proteção contra CSRF: o cliente sempre manda este cabeçalho, e outro site não consegue enviá-lo.
  if (req.method !== "GET" && req.headers.get("x-scorelyne") !== "1") {
    return resposta(403, { detail: "Requisição recusada" });
  }

  const token = await tokenDe(servico);
  if (!token) return resposta(401, { detail: "Faça login para continuar" });

  const corpo = req.method === "GET" || req.method === "DELETE" ? undefined : await req.text();
  let r: Response;
  try {
    r = await fetch(`${URLS[servico]}${rota}${req.nextUrl.search}`, {
      method: req.method,
      cache: "no-store",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: corpo || undefined,
    });
  } catch {
    return resposta(502, { detail: "Não foi possível conectar ao serviço. Ele está no ar?" });
  }

  const resp = new Response(await r.text(), {
    status: r.status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
  // Token vencido ou inválido: apaga o cookie, para o navegador voltar ao login.
  if (r.status === 401) resp.headers.append("Set-Cookie", `${COOKIE[servico]}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax`);
  return resp;
}

export { tratar as GET, tratar as POST, tratar as PATCH, tratar as DELETE };
