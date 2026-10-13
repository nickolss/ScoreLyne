// Cliente das APIs do backend. Os tipos espelham os modelos Pydantic de backend/src/scorelyne.
//   operadora (porta 8001): personas da demo e consentimento
//   banco     (porta 8002): solicitações, revisão humana e cartão do modelo

export const OPERADORA_URL = process.env.NEXT_PUBLIC_OPERADORA_URL ?? "http://localhost:8001";
export const BANCO_URL = process.env.NEXT_PUBLIC_BANCO_URL ?? "http://localhost:8002";

export type Escopo = "recargas" | "permanencia" | "pontualidade" | "estabilidade" | "consistencia";
export type Decisao = "aprovado" | "revisao" | "recusado";
export type Status = Decisao | "revogado";
export type StatusFator = "calculado" | "nao_autorizado" | "nao_se_aplica";
export type Plano = "pre_pago" | "controle" | "pos_pago";

export type PersonaDemo = {
  chave: string | null;
  telefone: string;
  titular: string;
  cpf: string;
  plano: Plano;
  cidade: string;
  uf: string;
};

export type Consentimento = {
  id: string;
  telefone: string;
  escopos: Escopo[];
  expira_em: string;
  revogado_em: string | null;
};

export type FatorExplicado = {
  chave: Escopo;
  rotulo: string;
  status: StatusFator;
  valor: number | null;
  evidencia: string;
  dica: string | null;
  pontos: number;
  valor_usado: number;
};

export type Parcela = { prazo_meses: number; valor_parcela: number; total: number };

export type Oferta = {
  limite: number;
  valor_ofertado: number;
  taxa_mensal: number;
  parcelas: Parcela[];
};

export type ResultadoAnalise = {
  telefone: string;
  score: number;
  faixa: string;
  decisao: Decisao;
  decisao_pelo_score: Decisao;
  confianca: "alta" | "baixa";
  probabilidade_inadimplencia: number;
  pontos_base: number;
  fatores: FatorExplicado[];
  pontos_fortes: string[];
  pontos_de_atencao: string[];
  motivos_revisao: string[];
  plano_de_melhora: string[];
  oferta: Oferta | null;
  modelo_versao: string;
};

export type Evento = {
  em: string;
  ator: "cliente" | "agente" | "analista" | "sistema";
  tipo: string;
  titulo: string;
  detalhe: string | null;
};

export type RevisaoHumana = {
  veredito: "aprovar" | "recusar";
  justificativa: string;
  analista: string;
  em: string;
};

export type SolicitacaoResumo = {
  id: string;
  criado_em: string;
  nome: string;
  ocupacao: string | null;
  plano: Plano | null;
  valor_solicitado: number;
  score: number | null;
  decisao_agente: Decisao;
  status: Status;
};

export type Solicitacao = SolicitacaoResumo & {
  atualizado_em: string;
  telefone: string;
  cidade: string | null;
  uf: string | null;
  finalidade: string;
  consentimento_id: string;
  escopos: Escopo[];
  analise: ResultadoAnalise | null;
  revisao_humana: RevisaoHumana | null;
  revogado_em: string | null;
  eventos: Evento[];
};

export type GrupoEquidade = {
  n: number;
  taxa_aprovacao: number;
  inadimplencia_real: number;
  inadimplencia_aprovados: number | null;
};

export type CartaoModelo = {
  versao: string;
  fatores: {
    chave: Escopo;
    rotulo: string;
    importancia: number;
    obrigatorio: boolean;
    ativo: boolean;
    perda_maxima_se_omitir: number;
  }[];
  limiares: { aprovacao: number; revisao: number };
  escala: { pd_aprovacao: number; pd_revisao: number };
  metricas: Record<string, number>;
  equidade: Record<
    string,
    { grupos: Record<string, GrupoEquidade>; razao_impacto: number | null; passa_regra_4_5: boolean }
  >;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, `Não foi possível conectar a ${new URL(url).origin}. O serviço está no ar?`);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    // Erros de validação do FastAPI vêm como lista.
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail;
    throw new ApiError(res.status, message || `Erro ${res.status}`);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });

export const operadora = {
  personas: () => req<PersonaDemo[]>(`${OPERADORA_URL}/demo/personas`),
  consentir: (p: { telefone: string; cpf: string; escopos: Escopo[] }) =>
    req<Consentimento>(
      `${OPERADORA_URL}/consentimentos`,
      json({ ...p, finalidade: "analise_de_credito", solicitante: "Banco Parceiro S.A." }),
    ),
};

export const banco = {
  listar: () => req<SolicitacaoResumo[]>(`${BANCO_URL}/solicitacoes`),
  obter: (id: string) => req<Solicitacao>(`${BANCO_URL}/solicitacoes/${encodeURIComponent(id)}`),
  criar: (p: {
    nome: string;
    telefone: string;
    consentimento_id: string;
    valor_solicitado: number;
    finalidade: string;
    ocupacao?: string;
    cidade?: string;
    uf?: string;
  }) => req<Solicitacao>(`${BANCO_URL}/solicitacoes`, json(p)),
  decidir: (id: string, p: { veredito: "aprovar" | "recusar"; justificativa: string }) =>
    req<Solicitacao>(`${BANCO_URL}/solicitacoes/${encodeURIComponent(id)}/decisao`, json(p)),
  desfazer: (id: string) =>
    req<Solicitacao>(`${BANCO_URL}/solicitacoes/${encodeURIComponent(id)}/decisao`, { method: "DELETE" }),
  revogar: (id: string) =>
    req<Solicitacao>(`${BANCO_URL}/solicitacoes/${encodeURIComponent(id)}/revogar`, { method: "POST" }),
  modelo: () => req<CartaoModelo>(`${BANCO_URL}/modelo`),
};
