"use server";

// Login, cadastro e saída. O token vai direto para um cookie httpOnly e nunca chega ao JavaScript do navegador.

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ApiError, criarConsumidor, criarCredor } from "@/lib/api";
import {
  COOKIE,
  DURACAO_SESSAO_S,
  type Servico,
  URLS,
  consumidorLogado,
  credorLogado,
  fetcher,
} from "@/lib/api-servidor";

export type EstadoForm = { erro?: string; ok?: string };

const texto = (fd: FormData, campo: string) => String(fd.get(campo) ?? "").trim();
const digitos = (fd: FormData, campo: string) => texto(fd, campo).replace(/\D/g, "");
const opcional = (fd: FormData, campo: string) => texto(fd, campo) || undefined;
const mensagem = (e: unknown) => (e instanceof ApiError ? e.message : "Erro inesperado. Tente de novo.");

async function guardarSessao(servico: Servico, token: string) {
  (await cookies()).set(COOKIE[servico], token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: DURACAO_SESSAO_S,
  });
}

export async function entrarConsumidor(_: EstadoForm, fd: FormData): Promise<EstadoForm> {
  try {
    const api = criarConsumidor(fetcher(URLS.consumidor));
    const sessao = await api.login({ cpf: digitos(fd, "cpf"), senha: String(fd.get("senha") ?? "") });
    await guardarSessao("consumidor", sessao.token);
  } catch (e) {
    return { erro: mensagem(e) };
  }
  redirect("/cliente");
}

export async function cadastrarConsumidor(_: EstadoForm, fd: FormData): Promise<EstadoForm> {
  const senha = String(fd.get("senha") ?? "");
  if (senha !== String(fd.get("confirmacao") ?? "")) return { erro: "As senhas não conferem." };
  try {
    const api = criarConsumidor(fetcher(URLS.consumidor));
    const cpf = digitos(fd, "cpf");
    await api.cadastrar({
      nome: texto(fd, "nome"),
      cpf,
      telefone: digitos(fd, "telefone"),
      senha,
      ocupacao: opcional(fd, "ocupacao"),
      cidade: opcional(fd, "cidade"),
      uf: opcional(fd, "uf")?.toUpperCase(),
    });
    const sessao = await api.login({ cpf, senha });
    await guardarSessao("consumidor", sessao.token);
  } catch (e) {
    return { erro: mensagem(e) };
  }
  redirect("/cliente");
}

export async function entrarCredor(_: EstadoForm, fd: FormData): Promise<EstadoForm> {
  try {
    const api = criarCredor(fetcher(URLS.credor));
    const sessao = await api.login({ email: texto(fd, "email"), senha: String(fd.get("senha") ?? "") });
    await guardarSessao("credor", sessao.token);
  } catch (e) {
    return { erro: mensagem(e) };
  }
  redirect("/banco");
}

export async function sair(servico: Servico) {
  if (!(servico in COOKIE)) return; // o argumento vem do cliente: ignora o que não for um serviço conhecido
  (await cookies()).delete(COOKIE[servico]);
  redirect(servico === "consumidor" ? "/cliente/entrar" : "/banco/entrar");
}

const confirmacaoDaSenha = (fd: FormData) => {
  const nova = String(fd.get("nova_senha") ?? "");
  return nova === String(fd.get("confirmacao") ?? "")
    ? { senha_atual: String(fd.get("senha_atual") ?? ""), nova_senha: nova }
    : null;
};

export async function trocarSenhaConsumidor(_: EstadoForm, fd: FormData): Promise<EstadoForm> {
  const troca = confirmacaoDaSenha(fd);
  if (!troca) return { erro: "As senhas novas não conferem." };
  const api = await consumidorLogado();
  if (!api) redirect("/cliente/entrar");
  try {
    await api.trocarSenha(troca);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/cliente/entrar");
    return { erro: mensagem(e) };
  }
  return { ok: "Senha alterada." };
}

export async function excluirContaConsumidor(_: EstadoForm, fd: FormData): Promise<EstadoForm> {
  const api = await consumidorLogado();
  if (!api) redirect("/cliente/entrar");
  try {
    await api.excluirConta(String(fd.get("senha") ?? ""));
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/cliente/entrar");
    return { erro: mensagem(e) };
  }
  (await cookies()).delete(COOKIE.consumidor);
  redirect("/cliente?conta=excluida");
}

export async function trocarSenhaCredor(_: EstadoForm, fd: FormData): Promise<EstadoForm> {
  const troca = confirmacaoDaSenha(fd);
  if (!troca) return { erro: "As senhas novas não conferem." };
  const api = await credorLogado();
  if (!api) redirect("/banco/entrar");
  try {
    await api.trocarSenha(troca);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/banco/entrar");
    return { erro: mensagem(e) };
  }
  return { ok: "Senha alterada." };
}
