import { ApiError } from "./api";

export const mensagemDeErro = (e: unknown) =>
  e instanceof ApiError ? e.message : "Erro inesperado. Tente de novo.";

/** O token venceu ou foi recusado: a pessoa precisa entrar de novo. */
export const sessaoExpirada = (e: unknown) => e instanceof ApiError && e.status === 401;
