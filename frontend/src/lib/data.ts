// Constantes de apresentação e formatação. Score, decisão e oferta vêm do backend (src/lib/api.ts).

import type { Escopo, Plano, Status } from "./api";

// Limiares da política de crédito (backend/src/scorelyne/score/politica.py).
export const THRESHOLDS = { approve: 750, review: 550 };

export const DECISION_LABEL: Record<Status, string> = {
  aprovado: "Pré-aprovado",
  revisao: "Revisão humana",
  recusado: "Não aprovado",
  revogado: "Revogado",
};

export const PLAN_LABEL: Record<Plano, string> = {
  pre_pago: "Pré-pago",
  controle: "Controle",
  pos_pago: "Pós-pago",
};

export const FACTOR_LABEL: Record<Escopo, string> = {
  recargas: "Regularidade de recargas",
  permanencia: "Tempo de permanência na base",
  pontualidade: "Pontualidade de pagamento",
  estabilidade: "Estabilidade do número",
  consistencia: "Consistência do valor gasto",
};

export function band(score: number) {
  if (score >= 850) return "Excelente";
  if (score >= THRESHOLDS.approve) return "Bom";
  if (score >= THRESHOLDS.review) return "Regular";
  return "Em construção";
}

// Dados que o modelo nunca consome — parte do compromisso de equidade e LGPD.
export const EXCLUDED_DATA = [
  "Localização e CEP",
  "Contatos e ligações",
  "Conteúdo de mensagens",
  "Gênero, raça ou idade",
  "Apps instalados",
];

// Para quê cada consentimento foi dado, como aparece na tela de consentimentos.
export const FINALIDADE_LABEL: Record<string, string> = {
  autoconsulta_de_score: "Calcular o seu score",
  analise_de_credito: "Analisar o seu pedido de crédito",
};

// Por que um pedido foi encerrado, como aparece no histórico de pedidos.
export const ENCERRAMENTO_LABEL: Record<string, string> = {
  retirado_pelo_cliente: "Você retirou o pedido",
  consentimento_revogado: "Você revogou o consentimento",
  dados_alterados: "Você trocou o telefone",
};

export const dataHora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });

export const dataCurta = (iso: string) => new Date(iso).toLocaleDateString("pt-BR");

export const maskCpf = (c: string) => `${c.slice(0, 3)}.•••.•••-${c.slice(-2)}`;

export const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

export const brl2 = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const pct = (v: number, digits = 0) =>
  v.toLocaleString("pt-BR", { style: "percent", minimumFractionDigits: digits, maximumFractionDigits: digits });

export function fmtPts(v: number, signed = true) {
  const r = Math.round(v * 10) / 10 || 0; // evita "-0,0"
  return (signed && r > 0 ? "+" : "") + r.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

export const maskPhone = (t: string) => `(${t.slice(0, 2)}) ${t.slice(2, 3)}••••-${t.slice(-4)}`;

// --- Extrato ilustrativo da home -------------------------------------------------
// Retrato da análise real da Maria no modelo atual (POST /solicitacoes), fixado para a
// animação da página inicial não depender do backend estar no ar.

export type Recharge = { date: string; amount: number | null };

export const MARIA_SNAPSHOT = {
  name: "Maria Aparecida",
  phone: "(11) 9••••-4821",
  since: "07/2020",
  months: 74,
  base: 680.7,
  score: 896,
  factors: [
    { key: "pontualidade", label: FACTOR_LABEL.pontualidade, points: 151.7 },
    { key: "recargas", label: FACTOR_LABEL.recargas, points: 44.0 },
    { key: "permanencia", label: FACTOR_LABEL.permanencia, points: 30.5 },
    { key: "consistencia", label: FACTOR_LABEL.consistencia, points: -10.9 },
  ],
};

// Mesmo histórico da persona no backend: 74 meses a partir de agosto/2020, 3 sem recarga.
export const MARIA_RECHARGES: Recharge[] = (() => {
  const amounts = [20, 30, 25, 30, 20, 50, 30, 25];
  const missed = new Set([9, 27, 44]);
  const out: Recharge[] = [];
  for (let i = 0; i < 74; i++) {
    const month = (7 + i) % 12;
    const year = 2020 + Math.floor((7 + i) / 12);
    const day = 3 + ((i * 7) % 5);
    out.push({
      date: `${String(day).padStart(2, "0")}/${String(month + 1).padStart(2, "0")}/${year}`,
      amount: missed.has(i) ? null : amounts[i % amounts.length],
    });
  }
  return out.reverse(); // mais recente primeiro
})();
