import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { BackendDown } from "@/components/backend-down";
import { Copilot } from "@/components/copilot";
import { BaseLine, DecisionBadge, FactorLines, ScoreScale, ScoreTotal } from "@/components/score";
import { ApiError, type Evento, type Solicitacao } from "@/lib/api";
import { credorLogado } from "@/lib/api-servidor";
import { DECISION_LABEL, PLAN_LABEL, brl, fmtPts, maskPhone, pct } from "@/lib/data";
import { ReviewPanel } from "./review-panel";

export const dynamic = "force-dynamic";

async function load(id: string): Promise<Solicitacao | ApiError> {
  const credor = await credorLogado();
  if (!credor) redirect("/banco/entrar");
  try {
    return await credor.obter(id);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/banco/entrar");
    if (e instanceof ApiError && e.status === 404) notFound();
    return e instanceof ApiError ? e : new ApiError(500, "Erro ao carregar a solicitação.");
  }
}

export async function generateMetadata(props: PageProps<"/banco/[id]">): Promise<Metadata> {
  const { id } = await props.params;
  const s = await load(id);
  return { title: s instanceof ApiError ? "Solicitação" : s.nome };
}

const ATOR: Record<Evento["ator"], string> = {
  cliente: "Cliente",
  agente: "Agente",
  analista: "Analista",
  sistema: "Sistema",
};

const timeFmt = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export default async function ApplicantPage(props: PageProps<"/banco/[id]">) {
  const { id } = await props.params;
  const s = await load(id);
  if (s instanceof ApiError) return <BackendDown message={s.message} />;

  const a = s.analise;
  const ranked = a ? [...a.fatores].sort((p, q) => q.pontos - p.pontos) : [];
  const strengths = ranked.filter((x) => x.pontos >= 5).slice(0, 2);
  const risks = ranked.filter((x) => x.pontos <= -5).reverse().slice(0, 2);
  const tenure = a?.fatores.find((f) => f.chave === "permanencia")?.evidencia.replace(" na mesma operadora", "");

  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-8 pb-10">
          <Link href="/banco" className="num text-xs text-on-cobalt-2 hover:text-on-cobalt underline">
            ← Solicitações
          </Link>
          <div className="mt-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="display text-5xl sm:text-6xl">{s.nome}</h1>
              <p className="mt-3 text-on-cobalt-2">
                {[s.ocupacao, s.cidade && `${s.cidade}, ${s.uf}`, maskPhone(s.telefone)].filter(Boolean).join(" · ")}
              </p>
            </div>
            <div className="text-right">
              <DecisionBadge decision={s.status} />
              {s.status !== s.decisao_agente && s.status !== "revogado" && (
                <p className="mt-2 text-xs text-on-cobalt-2">Agente: {DECISION_LABEL[s.decisao_agente]}</p>
              )}
            </div>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 sm:px-8 py-10 grid lg:grid-cols-[24rem_1fr] gap-8 items-start">
        <div className="space-y-8 lg:sticky lg:top-20">
          {a ? (
            <div className="border border-ink p-5">
              <ScoreTotal score={a.score} faixa={a.faixa} />
              <ScoreScale score={a.score} />
              <dl className="grid grid-cols-2 border-t border-ink text-sm">
                {[
                  ["Pedido", brl(s.valor_solicitado), true],
                  ["Limite sugerido", a.oferta ? brl(a.oferta.limite) : "—", true],
                  ["Plano", s.plano ? PLAN_LABEL[s.plano] : "—", false],
                  ["Na base há", tenure ?? "—", false],
                  ["Finalidade", s.finalidade, false],
                  ["Taxa indicativa", a.oferta ? `${a.oferta.taxa_mensal.toFixed(2).replace(".", ",")}% a.m.` : "—", true],
                  ["Prob. de inadimplência", pct(a.probabilidade_inadimplencia, 1), true],
                  ["Confiança", a.confianca === "alta" ? "Alta" : "Baixa", false],
                ].map(([k, v, mono], i) => (
                  <div key={k as string} className={`py-3 border-b border-rule ${i % 2 ? "pl-4" : "pr-4 border-r"}`}>
                    <dt className="label text-ink-2">{k}</dt>
                    <dd className={`mt-1 ${mono ? "num" : ""}`}>{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : (
            <div className="border border-dashed border-ink p-5 text-sm">
              <p className="font-semibold">Análise apagada</p>
              <p className="mt-2 text-ink-2">
                O cliente revogou o consentimento. Score e dados telecom foram descartados; fica só a trilha
                de auditoria.
              </p>
            </div>
          )}

          {s.status !== "revogado" && (
            <ReviewPanel
              id={s.id}
              name={s.nome}
              agentDecision={s.decisao_agente}
              review={s.revisao_humana}
              reasons={a?.motivos_revisao ?? []}
            />
          )}
        </div>

        <div className="space-y-10">
          {a && (
            <section>
              <h2 className="display text-2xl">Explicação do agente.</h2>
              <div className="mt-4 grid sm:grid-cols-2 border border-ink">
                <div className="p-5 sm:border-r border-b sm:border-b-0 border-ink">
                  <p className="label"><span className="bg-lime px-1">A favor</span></p>
                  {strengths.length ? (
                    <ul className="mt-3 space-y-3 text-sm">
                      {strengths.map((x) => (
                        <li key={x.chave}>
                          <span className="flex items-baseline gap-2">
                            <span className="font-semibold">{x.rotulo}</span>
                            <span className="leader" aria-hidden="true" />
                            <span className="num">{fmtPts(x.pontos)}</span>
                          </span>
                          <span className="block text-ink-2 mt-0.5">{x.evidencia}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-sm text-ink-2">Nenhum fator acima da média.</p>
                  )}
                </div>
                <div className="p-5">
                  <p className="label"><span className="bg-red text-paper px-1">Pontos de atenção</span></p>
                  {risks.length ? (
                    <ul className="mt-3 space-y-3 text-sm">
                      {risks.map((x) => (
                        <li key={x.chave}>
                          <span className="flex items-baseline gap-2">
                            <span className="font-semibold">{x.rotulo}</span>
                            <span className="leader" aria-hidden="true" />
                            <span className="num text-red-ink">{fmtPts(x.pontos)}</span>
                          </span>
                          <span className="block text-ink-2 mt-0.5">{x.evidencia}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-sm text-ink-2">Nenhum fator abaixo da média.</p>
                  )}
                </div>
              </div>
            </section>
          )}

          {a && (
            <section>
              <h2 className="display text-2xl">Fatores do score.</h2>
              <p className="mt-2 text-sm text-ink-2">
                Pontos em relação a um cliente médio. Modelo {a.modelo_versao}.
              </p>
              <div className="mt-4 border-t-2 border-ink">
                <BaseLine base={a.pontos_base} />
                <FactorLines factors={a.fatores} />
              </div>
            </section>
          )}

          {s.status !== "revogado" && (
            <section>
              <h2 className="display text-2xl">Pergunte ao copiloto.</h2>
              <div className="mt-4">
                <Copilot
                  suggestions={[
                    `Por que ${s.nome.split(" ")[0]} recebeu essa decisão? Explique fator por fator.`,
                    `Quais os argumentos a favor e contra aprovar ${s.nome.split(" ")[0]}?`,
                    `E se ${s.nome.split(" ")[0]} pedisse ${brl(s.valor_solicitado / 2)} em vez de ${brl(s.valor_solicitado)}?`,
                  ]}
                />
              </div>
            </section>
          )}

          <section>
            <h2 className="display text-2xl">Trilha de auditoria.</h2>
            <ol className="mt-4 border-t-2 border-ink">
              {s.eventos.map((e, i) => (
                <li key={i} className="grid grid-cols-[2.5rem_1fr_auto] gap-x-3 py-3 border-b border-rule">
                  <span className="num text-xs text-ink-2 pt-0.5">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <p className="font-semibold text-sm">
                      {e.titulo} <span className="label text-ink-2 font-normal ml-1">{ATOR[e.ator]}</span>
                    </p>
                    {e.detalhe && <p className="text-sm text-ink-2">{e.detalhe}</p>}
                  </div>
                  <span className="num text-xs text-ink-2 pt-0.5 whitespace-nowrap">{timeFmt.format(new Date(e.em))}</span>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </div>
    </>
  );
}
