import type { Metadata } from "next";
import Link from "next/link";
import { BackendDown } from "@/components/backend-down";
import { Copilot } from "@/components/copilot";
import { ApiError, banco, type SolicitacaoResumo } from "@/lib/api";
import { THRESHOLDS, brl } from "@/lib/data";
import { ApplicantTable } from "./applicant-table";

export const metadata: Metadata = { title: "Painel do banco" };

// A fila muda a cada pedido e decisão: renderiza sempre no momento da requisição.
export const dynamic = "force-dynamic";

export default async function BancoPage() {
  let rows: SolicitacaoResumo[];
  try {
    rows = await banco.listar();
  } catch (e) {
    return <BackendDown message={e instanceof ApiError ? e.message : "Erro ao carregar as solicitações."} />;
  }

  const approved = rows.filter((r) => r.status === "aprovado");
  const review = rows.filter((r) => r.status === "revisao");
  const volume = approved.reduce((s, r) => s + r.valor_solicitado, 0);

  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-12 pb-10">
          <p className="num text-sm text-on-cobalt-2">Microcrédito · fila de solicitações</p>
          <h1 className="display text-5xl sm:text-6xl mt-3">Solicitações</h1>
          <p className="mt-5 text-on-cobalt-2 max-w-2xl leading-relaxed">
            Todos os solicitantes abaixo foram recusados ou não pontuam nos birôs tradicionais. O score
            ScoreLyne é complementar: acima de {THRESHOLDS.approve} o agente pré-aprova, entre{" "}
            {THRESHOLDS.review} e {THRESHOLDS.approve} ou com histórico curto a decisão é de um analista.
          </p>
          <dl className="mt-10 grid grid-cols-2 lg:grid-cols-4 border-t border-on-cobalt/40">
            {[
              ["Solicitações", String(rows.length)],
              ["Aprovadas", String(approved.length)],
              ["Aguardando analista", String(review.length)],
              ["Volume aprovado", brl(volume)],
            ].map(([k, v], i) => (
              <div key={k} className={`pt-4 pb-1 pr-4 ${i > 0 ? "lg:pl-6 lg:border-l border-on-cobalt/40" : ""}`}>
                <dt className="label text-on-cobalt-2">{k}</dt>
                <dd className="num text-3xl mt-2">
                  {k === "Aguardando analista" && review.length > 0 ? (
                    <span className="bg-lime text-ink px-1">{v}</span>
                  ) : (
                    v
                  )}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </section>
      <div className="mx-auto max-w-7xl px-4 sm:px-8 py-10 space-y-10">
        {rows.length ? (
          <ApplicantTable rows={rows} />
        ) : (
          <div className="border border-dashed border-ink p-8 text-center">
            <p className="font-semibold">Nenhuma solicitação ainda.</p>
            <p className="mt-2 text-sm text-ink-2">
              Faça uma simulação em <Link href="/cliente" className="underline">Para você</Link> ou rode{" "}
              <code className="num bg-tint px-1">uv run banco semear</code> para criar as personas da demo.
            </p>
          </div>
        )}
        <Copilot />
      </div>
    </>
  );
}
