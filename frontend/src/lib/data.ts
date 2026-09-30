// Dados mockados enquanto o backend e o modelo de scoring não existem.
// Escala de score: 0–1000, calculada a partir de fatores telecom ponderados.

export type FactorKey = "recargas" | "permanencia" | "pontualidade" | "estabilidade" | "consistencia";

export type Factor = {
  key: FactorKey;
  label: string;
  weight: number; // soma dos pesos = 1
  value: number; // 0–100
  evidence: string;
  tip?: string; // caminho de melhora para o cliente
};

export type Decision = "aprovado" | "revisao" | "recusado";

export type Applicant = {
  id: string;
  name: string;
  age: number;
  occupation: string;
  city: string;
  plan: "Pré-pago" | "Pós-pago" | "Controle";
  tenureMonths: number;
  requested: number;
  purpose: string;
  submittedAt: string;
  factors: Factor[];
};

export const FACTOR_META: Record<FactorKey, { label: string; weight: number }> = {
  recargas: { label: "Regularidade de recargas", weight: 0.3 },
  permanencia: { label: "Tempo de permanência na base", weight: 0.25 },
  pontualidade: { label: "Pontualidade de pagamento", weight: 0.2 },
  estabilidade: { label: "Estabilidade do número", weight: 0.15 },
  consistencia: { label: "Consistência do valor gasto", weight: 0.1 },
};

// Dados que o modelo nunca consome — parte do compromisso de equidade e LGPD.
export const EXCLUDED_DATA = [
  "Localização e CEP",
  "Contatos e ligações",
  "Conteúdo de mensagens",
  "Gênero, raça ou idade",
  "Apps instalados",
];

function f(key: FactorKey, value: number, evidence: string, tip?: string): Factor {
  return { key, ...FACTOR_META[key], value, evidence, tip };
}

export const APPLICANTS: Applicant[] = [
  {
    id: "maria",
    name: "Maria Aparecida",
    age: 38,
    occupation: "Cabeleireira autônoma",
    city: "Osasco, SP",
    plan: "Pré-pago",
    tenureMonths: 74,
    requested: 1500,
    purpose: "Equipamentos (secador e prancha)",
    submittedAt: "2026-09-28T14:12:00",
    factors: [
      f("recargas", 92, "71 de 74 meses com recarga; intervalo médio de 29 dias"),
      f("permanencia", 88, "6 anos e 2 meses na mesma operadora"),
      f(
        "pontualidade",
        70,
        "Pré-pago: sem faturas. Avaliada pela recarga antes do saldo zerar",
        "Migrar para o plano Controle cria histórico de fatura paga em dia",
      ),
      f("estabilidade", 95, "Mesmo número desde 2020, sem portabilidade"),
      f(
        "consistencia",
        64,
        "Recargas entre R$ 20 e R$ 50; variação alta em 2024",
        "Manter um valor de recarga parecido todo mês aumenta este fator",
      ),
    ],
  },
  {
    id: "joao",
    name: "João Batista",
    age: 45,
    occupation: "Motorista de aplicativo",
    city: "Recife, PE",
    plan: "Controle",
    tenureMonths: 38,
    requested: 3000,
    purpose: "Reparo do veículo",
    submittedAt: "2026-09-28T10:40:00",
    factors: [
      f("recargas", 80, "Plano Controle com complementos mensais regulares"),
      f("permanencia", 62, "3 anos e 2 meses na base"),
      f("pontualidade", 91, "37 de 38 faturas pagas até o vencimento"),
      f("estabilidade", 84, "Número único, uma troca de chip em 2025"),
      f("consistencia", 77, "Fatura estável entre R$ 45 e R$ 55"),
    ],
  },
  {
    id: "ana",
    name: "Ana Clara Souza",
    age: 24,
    occupation: "Vendedora ambulante",
    city: "Belém, PA",
    plan: "Pré-pago",
    tenureMonths: 14,
    requested: 800,
    purpose: "Capital de giro",
    submittedAt: "2026-09-27T18:05:00",
    factors: [
      f(
        "recargas",
        66,
        "10 de 14 meses com recarga",
        "Recarregar todo mês, mesmo valores pequenos, pesa mais que o valor",
      ),
      f(
        "permanencia",
        30,
        "1 ano e 2 meses na base",
        "Este fator cresce naturalmente com o tempo de relacionamento",
      ),
      f("pontualidade", 55, "Saldo zerado antes da recarga em 5 ocasiões"),
      f("estabilidade", 72, "Mesmo número desde a ativação"),
      f("consistencia", 61, "Recargas entre R$ 10 e R$ 30"),
    ],
  },
  {
    id: "carlos",
    name: "Carlos Henrique Lima",
    age: 52,
    occupation: "Pedreiro",
    city: "Contagem, MG",
    plan: "Pós-pago",
    tenureMonths: 112,
    requested: 5000,
    purpose: "Ferramentas",
    submittedAt: "2026-09-27T09:22:00",
    factors: [
      f("recargas", 70, "Pós-pago: sem recargas; linha suspensa 2 vezes por atraso"),
      f("permanencia", 97, "9 anos e 4 meses na base"),
      f("pontualidade", 30, "Atrasos acima de 15 dias em 6 das últimas 12 faturas"),
      f("estabilidade", 90, "Mesmo número há 9 anos"),
      f("consistencia", 70, "Fatura com picos de consumo em 3 meses"),
    ],
  },
  {
    id: "luciana",
    name: "Luciana Ferreira",
    age: 31,
    occupation: "Manicure",
    city: "Salvador, BA",
    plan: "Pré-pago",
    tenureMonths: 5,
    requested: 1000,
    purpose: "Materiais de trabalho",
    submittedAt: "2026-09-26T16:48:00",
    factors: [
      f("recargas", 60, "4 de 5 meses com recarga"),
      f("permanencia", 8, "5 meses na base"),
      f("pontualidade", 50, "Histórico curto demais para avaliar"),
      f("estabilidade", 40, "Número ativado há 5 meses"),
      f("consistencia", 55, "Poucos pontos de dados"),
    ],
  },
];

export function getApplicant(id: string) {
  return APPLICANTS.find((a) => a.id === id);
}

export function computeScore(factors: Factor[]) {
  return Math.round(factors.reduce((sum, x) => sum + x.weight * x.value, 0) * 10);
}

// Faixas de decisão do agente. A faixa intermediária sempre vai para um analista.
export const THRESHOLDS = { approve: 750, review: 550 };

export function decide(score: number): Decision {
  if (score >= THRESHOLDS.approve) return "aprovado";
  if (score >= THRESHOLDS.review) return "revisao";
  return "recusado";
}

export function band(score: number) {
  if (score >= 850) return "Excelente";
  if (score >= 750) return "Bom";
  if (score >= 550) return "Regular";
  return "Em construção";
}

// Limite sugerido cresce com o score; o valor pedido nunca é ultrapassado.
export function suggestedLimit(score: number) {
  if (score < THRESHOLDS.review) return 0;
  return Math.round(((score - 500) / 500) * 4000 / 100) * 100;
}

export function monthlyRate(score: number) {
  return Math.max(1.9, 5.5 - (score - 550) * 0.009);
}

export function installment(principal: number, ratePct: number, months: number) {
  const r = ratePct / 100;
  return (principal * r) / (1 - Math.pow(1 + r, -months));
}

export const brl = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

export const brl2 = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function tenureLabel(months: number) {
  const y = Math.floor(months / 12);
  const m = months % 12;
  const parts = [];
  if (y) parts.push(`${y} ${y === 1 ? "ano" : "anos"}`);
  if (m) parts.push(`${m} ${m === 1 ? "mês" : "meses"}`);
  return parts.join(" e ") || "menos de 1 mês";
}

export const DECISION_LABEL: Record<Decision, string> = {
  aprovado: "Pré-aprovado",
  revisao: "Revisão humana",
  recusado: "Não aprovado",
};

// Histórico ilustrativo de recargas da Maria: 74 meses, 3 sem recarga.
export type Recharge = { date: string; amount: number | null };

export const MARIA_PHONE = "(11) 9••••-4821";

export const MARIA_RECHARGES: Recharge[] = (() => {
  const amounts = [20, 30, 25, 30, 20, 50, 30, 25];
  const missed = new Set([9, 27, 44]);
  const out: Recharge[] = [];
  for (let i = 0; i < 74; i++) {
    const month = (6 + i) % 12; // começa em julho/2020
    const year = 2020 + Math.floor((6 + i) / 12);
    const day = 3 + ((i * 7) % 5);
    out.push({
      date: `${String(day).padStart(2, "0")}/${String(month + 1).padStart(2, "0")}/${year}`,
      amount: missed.has(i) ? null : amounts[i % amounts.length],
    });
  }
  return out.reverse(); // mais recente primeiro
})();

export const pts = (x: Factor) => x.value * x.weight * 10;

export const fmtPts = (v: number) =>
  v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
