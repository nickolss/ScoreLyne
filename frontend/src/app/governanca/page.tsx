import type { Metadata } from "next";
import { ApiError, banco, type CartaoModelo } from "@/lib/api";
import { EXCLUDED_DATA, PLAN_LABEL, THRESHOLDS, pct } from "@/lib/data";

export const metadata: Metadata = { title: "Governança" };

// Pesos, métricas e equidade vêm do modelo em produção (GET /modelo).
export const dynamic = "force-dynamic";

const PRINCIPLES = [
  {
    title: "Equidade e antibias",
    body: "O modelo só consome fatores de comportamento de uso. A cada treino, as taxas de aprovação são medidas por região e por tipo de plano (regra dos 4/5), junto com a inadimplência dos aprovados de cada grupo.",
  },
  {
    title: "Transparência e explicabilidade",
    body: "Todo score vem com os pontos de cada fator, que somados à base dão exatamente o score. Quem é aprovado entende o porquê; quem é recusado recebe o que fazer para melhorar.",
  },
  {
    title: "Privacidade (LGPD)",
    body: "Consentimento explícito, granular e revogável antes de qualquer uso. O banco recebe só os blocos autorizados, com valores agregados por mês. Fator opcional não autorizado entra com o pior valor: esconder dados nunca aumenta o score. Revogar apaga a análise.",
  },
  {
    title: "Supervisão humana",
    body: `Scores entre ${THRESHOLDS.review} e ${THRESHOLDS.approve}, linhas com menos de 6 meses ou com poucos fatores sempre passam por um analista. Qualquer decisão automática pode ser sobreposta, com justificativa registrada na trilha de auditoria.`,
  },
  {
    title: "Conformidade",
    body: "Alinhado às diretrizes do Banco Central para concessão de crédito e da ANPD para tratamento de dados pessoais.",
  },
];

const GROUP_LABEL: Record<string, string> = { regiao: "Região", plano: "Tipo de plano" };

export default async function GovernancaPage() {
  let modelo: CartaoModelo | null = null;
  let error: string | null = null;
  try {
    modelo = await banco.modelo();
  } catch (e) {
    error = e instanceof ApiError ? e.message : "Erro ao carregar o modelo.";
  }

  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 py-16">
          <h1 className="display text-[clamp(2.5rem,6vw,4.75rem)] max-w-5xl">
            Decisões de crédito que dá para{" "}
            <span className="bg-lime text-ink px-2 box-decoration-clone">explicar, auditar e contestar.</span>
          </h1>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 sm:px-8 py-16 grid lg:grid-cols-[1.4fr_1fr] gap-12 lg:gap-16 items-start">
        <div className="space-y-16">
          <ol className="border-t-2 border-ink">
            {PRINCIPLES.map((p, i) => (
              <li key={p.title} className="py-7 grid grid-cols-[3.5rem_1fr] border-b border-rule">
                <span className="num text-sm text-cobalt pt-1.5">§ {i + 1}</span>
                <div>
                  <h2 className="text-2xl font-bold">{p.title}</h2>
                  <p className="mt-2 text-ink-2 leading-relaxed max-w-[62ch]">{p.body}</p>
                </div>
              </li>
            ))}
          </ol>

          {modelo && <Fairness modelo={modelo} />}
        </div>

        <aside className="space-y-8 lg:sticky lg:top-20">
          {error && (
            <div className="border-2 border-red p-5 text-sm" role="alert">
              <p className="font-semibold">Modelo indisponível</p>
              <p className="mt-1 text-ink-2">{error}</p>
            </div>
          )}
          {modelo && (
            <>
              <div className="border border-ink">
                <h2 className="px-5 py-3 border-b border-ink bg-tint font-bold">O que entra no modelo</h2>
                <ul className="px-5 py-2 text-sm">
                  {[...modelo.fatores]
                    .sort((a, b) => b.importancia - a.importancia)
                    .map((f) => (
                      <li key={f.chave} className="py-2">
                        <div className="flex items-baseline gap-2">
                          <span className={f.ativo ? "" : "text-ink-2"}>{f.rotulo}</span>
                          <span className="leader" aria-hidden="true" />
                          <span className="num">{f.ativo ? pct(f.importancia) : "sem peso"}</span>
                        </div>
                        <p className="text-xs text-ink-2 mt-0.5">
                          {f.obrigatorio ? "Necessário" : "Opcional"}
                          {!f.ativo && " · sem poder preditivo no treino atual, monitorado"}
                        </p>
                      </li>
                    ))}
                </ul>
                <p className="px-5 py-3 border-t border-rule text-xs text-ink-2">
                  Importância relativa no modelo {modelo.versao} (regressão logística monotônica).
                </p>
              </div>

              <div className="border border-ink">
                <h2 className="px-5 py-3 border-b border-ink bg-tint font-bold">Desempenho no teste</h2>
                <dl className="px-5 py-2 text-sm">
                  {[
                    ["AUC", modelo.metricas.auc.toFixed(2).replace(".", ",")],
                    ["KS", modelo.metricas.ks.toFixed(2).replace(".", ",")],
                    ["Aprovação automática", pct(modelo.metricas.taxa_aprovacao_automatica)],
                    ["Inadimplência dos aprovados", pct(modelo.metricas.inadimplencia_aprovados, 1)],
                    ["Vai para analista", pct(modelo.metricas.taxa_revisao)],
                    ["Inadimplência dos recusados", pct(modelo.metricas.inadimplencia_recusados, 1)],
                  ].map(([k, v]) => (
                    <div key={k} className="flex items-baseline gap-2 py-2">
                      <dt>{k}</dt>
                      <span className="leader" aria-hidden="true" />
                      <dd className="num">{v}</dd>
                    </div>
                  ))}
                </dl>
                <p className="px-5 py-3 border-t border-rule text-xs text-ink-2">
                  {THRESHOLDS.approve} pontos = {pct(modelo.escala.pd_aprovacao)} de chance de inadimplência;{" "}
                  {THRESHOLDS.review} = {pct(modelo.escala.pd_revisao)}. Dados sintéticos da operadora mock.
                </p>
              </div>
            </>
          )}

          <div className="border border-dashed border-ink">
            <h2 className="px-5 py-3 border-b border-dashed border-ink font-bold">O que nunca entra</h2>
            <ul className="px-5 py-4 space-y-2 text-sm text-ink-2">
              {EXCLUDED_DATA.map((d) => (
                <li key={d} className="line-through decoration-red decoration-2">
                  {d}
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </>
  );
}

function Fairness({ modelo }: { modelo: CartaoModelo }) {
  return (
    <section>
      <h2 className="display text-3xl">Monitor de equidade.</h2>
      <p className="mt-3 text-ink-2 leading-relaxed max-w-[62ch]">
        Aprovação automática por grupo. A regra dos 4/5 pede que o grupo com menor aprovação tenha pelo
        menos 80% da taxa do maior. Inadimplência parecida entre os aprovados mostra que o mesmo padrão
        de risco vale para todos.
      </p>
      <div className="mt-6 space-y-8">
        {Object.entries(modelo.equidade).map(([dim, r]) => (
          <div key={dim} className="border border-ink">
            <div className="px-5 py-3 border-b border-ink flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-bold">{GROUP_LABEL[dim] ?? dim}</h3>
              <span
                className={`label border px-2 py-0.5 ${r.passa_regra_4_5 ? "bg-lime border-ink" : "bg-red text-paper border-red"}`}
              >
                Razão {r.razao_impacto?.toFixed(2).replace(".", ",") ?? "—"} ·{" "}
                {r.passa_regra_4_5 ? "dentro da regra" : "atenção"}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[28rem]">
                <thead className="text-left">
                  <tr className="border-b border-rule">
                    <th className="label font-normal px-5 py-2">Grupo</th>
                    <th className="label font-normal px-5 py-2 text-right">Aprovação</th>
                    <th className="label font-normal px-5 py-2 text-right">Inad. dos aprovados</th>
                    <th className="label font-normal px-5 py-2 text-right">Linhas</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(r.grupos).map(([g, t]) => (
                    <tr key={g} className="border-b border-rule last:border-b-0">
                      <td className="px-5 py-2">{PLAN_LABEL[g as keyof typeof PLAN_LABEL] ?? g}</td>
                      <td className="px-5 py-2 text-right num">
                        <span className="inline-flex items-center gap-2">
                          <span className="hidden sm:block w-20 h-1.5 bg-tint" aria-hidden="true">
                            <span className="block h-full bg-cobalt" style={{ width: `${t.taxa_aprovacao * 100}%` }} />
                          </span>
                          {pct(t.taxa_aprovacao)}
                        </span>
                      </td>
                      <td className="px-5 py-2 text-right num">
                        {t.inadimplencia_aprovados === null ? "—" : pct(t.inadimplencia_aprovados, 1)}
                      </td>
                      <td className="px-5 py-2 text-right num text-ink-2">{t.n}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {dim === "plano" && !r.passa_regra_4_5 && (
              <p className="px-5 py-3 border-t border-rule text-sm text-ink-2">
                Ponto em aberto: o pré-pago tem menos informação por mês (recargas em vez de datas de
                pagamento de fatura), então o modelo separa menos os bons pagadores desse grupo. A
                inadimplência entre os aprovados é a mesma. Em estudo: limiares por segmento ou sinais mais
                ricos para o pré-pago.
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
