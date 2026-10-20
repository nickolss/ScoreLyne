// Contratos e clientes das APIs do backend. Os tipos espelham os modelos Pydantic de backend/src/scorelyne.
//   consumidor (porta 8003): cadastro, consentimento, score próprio, assistente com IA, pedido ao credor
//   credor     (porta 8002): fila de solicitações, revisão humana, cartão do modelo e copiloto do analista
//
// Os clientes recebem um `Fetcher`, então servem aos dois mundos:
//   navegador -> lib/api-browser.ts (passa pelo proxy /api/<serviço>, que injeta o token do cookie httpOnly)
//   servidor  -> lib/api-servidor.ts (chama o backend direto, com o token do cookie)

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
  formula_versao: string;
};

export type Parcela = { prazo_meses: number; valor_parcela: number; total: number };

export type Oferta = {
  limite: number;
  valor_ofertado: number;
  taxa_mensal: number;
  parcelas: Parcela[];
};

export type ResultadoAnalise = {
  telefone?: string; // o credor recebe; o consumidor não precisa dele
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
  formulas_versao: string;
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

// O que o consumidor vê do próprio pedido: sem trilha interna nem dados de terceiros.
export type SituacaoSolicitacao = {
  id: string;
  status: Status;
  decisao_agente: Decisao;
  score: number | null;
  oferta: Oferta | null;
  motivos_revisao: string[];
  revisao_humana: RevisaoHumana | null;
  atualizado_em: string;
};

export type GrupoEquidade = {
  n: number;
  taxa_aprovacao: number;
  inadimplencia_real: number;
  inadimplencia_aprovados: number | null;
  pd_prevista: number;
  margem_95: number;
  calibrado: boolean;
};

export type DimensaoEquidade = {
  grupos: Record<string, GrupoEquidade>;
  razao_impacto: number | null;
  passa_regra_4_5: boolean;
  erro_calibracao_maximo: number | null;
  calibrado_em_todos_os_grupos: boolean;
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
  equidade: Record<string, DimensaoEquidade>;
};

export type FormulaFator = {
  id: Escopo;
  rotulo: string;
  versao: string;
  formula: string;
  entradas: string[];
  parametros: Record<string, unknown>;
  observacao: string;
};

export type RegistroFormulas = {
  versao: string;
  atualizado_em: string;
  fatores: FormulaFator[];
  modelo: {
    versao: string;
    formula_score: string;
    formula_pontos_fator: string;
    formula_escala: string;
    formula_probabilidade: string;
    parametros: Record<string, unknown>;
    observacao: string;
  };
  politica: {
    versao: string;
    parametros: Record<string, unknown>;
    formulas: Record<string, string>;
    regras_de_supervisao: string[];
  };
};

// --- Consumidor ---------------------------------------------------------------------

export type Cliente = {
  id: string;
  nome: string;
  cpf: string;
  telefone: string;
  ocupacao: string | null;
  cidade: string | null;
  uf: string | null;
  consentimento_ativo: boolean;
  escopos: Escopo[];
  enviado_ao_credor: boolean;
};

export type MeuScore = {
  valor_solicitado: number;
  finalidade: string;
  calculado_em: string;
  escopos: Escopo[];
  analise: ResultadoAnalise;
};

export type SessaoLogin = { token: string; tipo: string };
export type SessaoConsumidor = SessaoLogin & { cliente: Cliente };
export type SessaoAnalista = SessaoLogin & { nome: string };

export type Cadastro = {
  nome: string;
  cpf: string;
  telefone: string;
  senha: string;
  ocupacao?: string;
  cidade?: string;
  uf?: string;
};

export type AtualizarDados = { telefone?: string; ocupacao?: string; cidade?: string; uf?: string };

// --- Chat com IA (assistente do consumidor e copiloto do analista) ---------------------

export type StatusChat = {
  disponivel: boolean;
  provedor: string | null;
  modelo: string | null;
  perguntas: string[];
};

export type RespostaChat = {
  resposta: string;
  ferramentas: { nome: string; argumentos: Record<string, unknown>; erro: string | null }[];
  provedor: string;
  modelo: string;
};

export type MensagemCopiloto = { papel: "analista" | "copiloto"; texto: string };
export type MensagemAssistente = { papel: "cliente" | "assistente"; texto: string };

// --- HTTP -----------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export type Fetcher = (caminho: string, init?: RequestInit) => Promise<Response>;

async function chamar<T>(f: Fetcher, caminho: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await f(caminho, init);
  } catch {
    throw new ApiError(0, "Não foi possível conectar ao serviço. Ele está no ar?");
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

const enviar = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export function criarCredor(f: Fetcher) {
  const get = <T>(caminho: string) => chamar<T>(f, caminho);
  const id = (x: string) => encodeURIComponent(x);
  return {
    login: (p: { email: string; senha: string }) =>
      chamar<SessaoAnalista>(f, "/login", enviar("POST", p)),
    listar: () => get<SolicitacaoResumo[]>("/solicitacoes"),
    obter: (x: string) => get<Solicitacao>(`/solicitacoes/${id(x)}`),
    decidir: (x: string, p: { veredito: "aprovar" | "recusar"; justificativa: string }) =>
      chamar<Solicitacao>(f, `/solicitacoes/${id(x)}/decisao`, enviar("POST", p)),
    desfazer: (x: string) => chamar<Solicitacao>(f, `/solicitacoes/${id(x)}/decisao`, enviar("DELETE")),
    modelo: () => get<CartaoModelo>("/modelo"),
    formulas: () => get<RegistroFormulas>("/formulas"),
    copiloto: () => get<StatusChat>("/copiloto"),
    perguntar: (mensagens: MensagemCopiloto[]) =>
      chamar<RespostaChat>(f, "/copiloto", enviar("POST", { mensagens })),
  };
}

export function criarConsumidor(f: Fetcher) {
  const get = <T>(caminho: string) => chamar<T>(f, caminho);
  return {
    cadastrar: (p: Cadastro) => chamar<Cliente>(f, "/cadastro", enviar("POST", p)),
    login: (p: { cpf: string; senha: string }) =>
      chamar<SessaoConsumidor>(f, "/login", enviar("POST", p)),
    eu: () => get<Cliente>("/me"),
    atualizar: (p: AtualizarDados) => chamar<Cliente>(f, "/meus-dados", enviar("PATCH", p)),
    consentir: (escopos: Escopo[]) => chamar<Consentimento>(f, "/consentimentos", enviar("POST", { escopos })),
    calcular: (p: { valor_solicitado: number; finalidade: string }) =>
      chamar<MeuScore>(f, "/meu-score", enviar("POST", p)),
    meuScore: () => get<MeuScore>("/meu-score"),
    revogar: () => chamar<Cliente>(f, "/revogar", enviar("POST")),
    enviarAoCredor: () => chamar<Cliente>(f, "/enviar-ao-credor", enviar("POST")),
    minhaSolicitacao: () => get<SituacaoSolicitacao>("/minha-solicitacao"),
    retirarDoCredor: () => chamar<Cliente>(f, "/retirar-do-credor", enviar("POST")),
    assistente: () => get<StatusChat>("/assistente"),
    perguntarAoAssistente: (mensagens: MensagemAssistente[]) =>
      chamar<RespostaChat>(f, "/assistente", enviar("POST", { mensagens })),
    formulas: () => get<RegistroFormulas>("/formulas"),
    modelo: () => get<CartaoModelo>("/modelo"),
  };
}

export function criarOperadora(f: Fetcher) {
  return { personas: () => chamar<PersonaDemo[]>(f, "/demo/personas") };
}

export type ApiConsumidor = ReturnType<typeof criarConsumidor>;
export type ApiCredor = ReturnType<typeof criarCredor>;
