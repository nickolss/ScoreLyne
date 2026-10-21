import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { BackendDown } from "@/components/backend-down";
import { DecisionBadge } from "@/components/score";
import { btnPrimary } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { consumidorLogado } from "@/lib/api-servidor";
import { ENCERRAMENTO_LABEL, brl, brl2, dataHora } from "@/lib/data";

export const metadata: Metadata = { title: "Pedidos" };

export const dynamic = "force-dynamic";

export default async function PedidosPage() {
  const api = await consumidorLogado();
  if (!api) redirect("/cliente/entrar");

  let pedidos;
  try {
    pedidos = await api.meusPedidos();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/cliente/entrar");
    return <BackendDown service="consumidor" message={e instanceof ApiError ? e.message : "Erro ao carregar seus pedidos."} />;
  }

  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-12 pb-10">
          <p className="num text-sm text-on-cobalt-2">Persona · Consumidor</p>
          <h1 className="display text-5xl sm:text-6xl mt-3">Pedidos.</h1>
          <p className="mt-5 text-on-cobalt-2 max-w-2xl leading-relaxed">
            Cada pedido de crédito que você enviou ao banco, do mais recente ao mais antigo, e o que aconteceu com ele.
          </p>
        </div>
      </section>

      <div className="bg-tint">
        <div className="mx-auto max-w-4xl px-4 sm:px-8 py-10 space-y-6">
          {pedidos.length === 0 && (
            <div className="border border-dashed border-ink bg-paper p-8 text-center">
              <p className="font-semibold">Você ainda não enviou nenhum pedido.</p>
              <p className="mt-2 text-sm text-ink-2">Primeiro você vê o seu score; só envia ao banco se quiser.</p>
              <Link href="/cliente/score" className={`${btnPrimary} mt-5`}>
                Calcular meu score
              </Link>
            </div>
          )}

          {pedidos.map((p) => {
            const aberto = p.encerrado_em === null;
            const s = p.situacao;
            return (
              <article key={p.id} className="border border-ink bg-paper">
                <header className="px-5 py-3 border-b border-ink bg-tint flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-bold text-lg">
                    {brl(p.valor_solicitado)} · {p.finalidade}
                  </h2>
                  {aberto && s ? (
                    <DecisionBadge decision={s.status} />
                  ) : aberto ? (
                    <span className="label text-ink-2">em andamento</span>
                  ) : (
                    <span className="label border border-ink px-2 py-0.5">encerrado</span>
                  )}
                </header>
                <div className="p-5 text-sm space-y-2">
                  <p className="text-ink-2">Enviado em {dataHora(p.enviado_em)}.</p>

                  {!aberto && (
                    <p>
                      <span className="font-semibold">{ENCERRAMENTO_LABEL[p.encerramento ?? ""] ?? "Pedido encerrado"}</span>{" "}
                      em {dataHora(p.encerrado_em!)}. O banco apagou a análise; fica só o registro de que ela existiu.
                    </p>
                  )}

                  {aberto && !s && (
                    <p className="text-ink-2">Não foi possível consultar a situação agora. Tente de novo em instantes.</p>
                  )}

                  {aberto && s?.status === "revisao" && (
                    <p>Está com um analista. Nesta faixa, o agente nunca decide sozinho.</p>
                  )}

                  {aberto && s?.revisao_humana && (
                    <div className="border border-ink mt-3">
                      <p className={`label px-4 py-2 ${s.revisao_humana.veredito === "aprovar" ? "bg-lime" : "bg-red text-paper"}`}>
                        Decisão do analista · {dataHora(s.revisao_humana.em)}
                      </p>
                      <p className="p-4">&ldquo;{s.revisao_humana.justificativa}&rdquo;</p>
                    </div>
                  )}

                  {aberto && s?.oferta && s.status !== "recusado" && (
                    <p className="num pt-1">
                      Oferta: {brl(s.oferta.valor_ofertado)} a {s.oferta.taxa_mensal.toFixed(2).replace(".", ",")}% a.m.,{" "}
                      {s.oferta.parcelas[0].prazo_meses}x de {brl2(s.oferta.parcelas[0].valor_parcela)}.
                    </p>
                  )}
                </div>
              </article>
            );
          })}

          {pedidos.some((p) => p.encerrado_em === null) && (
            <p className="text-sm text-ink-2">
              Para retirar um pedido em andamento, use a tela de{" "}
              <Link href="/cliente/consentimentos" className="font-semibold underline hover:no-underline">
                consentimentos
              </Link>
              .
            </p>
          )}
        </div>
      </div>
    </>
  );
}
