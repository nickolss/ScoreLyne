import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { BackendDown } from "@/components/backend-down";
import { RevogarAcao } from "@/components/consentimento-acoes";
import { btnPrimary } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { consumidorLogado } from "@/lib/api-servidor";
import { FACTOR_LABEL, FINALIDADE_LABEL, dataCurta, dataHora } from "@/lib/data";

export const metadata: Metadata = { title: "Consentimentos" };

export const dynamic = "force-dynamic";

export default async function ConsentimentosPage() {
  const api = await consumidorLogado();
  if (!api) redirect("/cliente/entrar");

  let lista;
  try {
    lista = await api.meusConsentimentos();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/cliente/entrar");
    return <BackendDown service="consumidor" message={e instanceof ApiError ? e.message : "Erro ao carregar seus consentimentos."} />;
  }

  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-12 pb-10">
          <p className="num text-sm text-on-cobalt-2">Persona · Consumidor</p>
          <h1 className="display text-5xl sm:text-6xl mt-3">Consentimentos.</h1>
          <p className="mt-5 text-on-cobalt-2 max-w-2xl leading-relaxed">
            O que você autorizou, para quem, e cada vez que seus dados foram lidos. Você pode revogar quando quiser.
          </p>
        </div>
      </section>

      <div className="bg-tint">
        <div className="mx-auto max-w-4xl px-4 sm:px-8 py-10 space-y-6">
          {lista.length === 0 && (
            <div className="border border-dashed border-ink bg-paper p-8 text-center">
              <p className="font-semibold">Você não tem nenhuma autorização ativa.</p>
              <p className="mt-2 text-sm text-ink-2">Nenhum dado seu está sendo lido por ninguém.</p>
              <Link href="/cliente/score" className={`${btnPrimary} mt-5`}>
                Calcular meu score
              </Link>
            </div>
          )}

          {lista.map((c) => {
            const doBanco = c.destinatario !== "ScoreLyne";
            const acessos = [...c.acessos].sort((a, b) => b.em.localeCompare(a.em));
            return (
              <article key={c.id} className="border border-ink bg-paper" aria-labelledby={`c-${c.id}`}>
                <header className="px-5 py-3 border-b border-ink bg-tint flex flex-wrap items-baseline justify-between gap-2">
                  <h2 id={`c-${c.id}`} className="font-bold text-lg">
                    {c.destinatario}
                  </h2>
                  <p className="label text-ink-2">válido até {dataCurta(c.expira_em)}</p>
                </header>

                <div className="p-5">
                  <p className="text-sm">
                    <span className="font-semibold">Para quê:</span> {FINALIDADE_LABEL[c.finalidade] ?? c.finalidade}.
                  </p>
                  <p className="mt-1 text-sm text-ink-2">Autorizado em {dataHora(c.criado_em)}.</p>
                  <ul className="mt-4 flex flex-wrap gap-2">
                    {c.escopos.map((e) => (
                      <li key={e} className="border border-ink px-2.5 py-1 text-sm">
                        {FACTOR_LABEL[e]}
                      </li>
                    ))}
                  </ul>

                  <details className="mt-5 border border-rule" open={acessos.length > 0 && acessos.length <= 3}>
                    <summary className="cursor-pointer px-4 py-3 font-semibold">
                      Quem leu meus dados:{" "}
                      <span className="num">{acessos.length}</span> {acessos.length === 1 ? "leitura" : "leituras"}
                    </summary>
                    {acessos.length === 0 ? (
                      <p className="px-4 pb-4 text-sm text-ink-2">Ninguém leu seus dados com esta autorização ainda.</p>
                    ) : (
                      <table className="w-full text-sm border-t border-rule">
                        <thead className="text-left">
                          <tr className="border-b border-rule">
                            <th className="label font-normal px-4 py-2">Quando</th>
                            <th className="label font-normal px-4 py-2">Quem</th>
                            <th className="label font-normal px-4 py-2">O que foi lido</th>
                          </tr>
                        </thead>
                        <tbody>
                          {acessos.map((a) => (
                            <tr key={a.em} className="border-b border-rule last:border-b-0 align-top">
                              <td className="px-4 py-2 num whitespace-nowrap">{dataHora(a.em)}</td>
                              <td className="px-4 py-2">{c.destinatario}</td>
                              <td className="px-4 py-2 text-ink-2">{a.escopos.map((e) => FACTOR_LABEL[e]).join(", ")}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </details>

                  <div className="mt-5">
                    {doBanco ? (
                      <RevogarAcao
                        tipo="credor"
                        rotulo="Retirar o pedido e revogar o acesso do banco"
                        consequencia="O banco perde o acesso aos seus dados e apaga a análise do pedido. Seu score na ScoreLyne continua."
                      />
                    ) : (
                      <RevogarAcao
                        tipo="tudo"
                        rotulo="Revogar tudo"
                        consequencia="A ScoreLyne para de ler seus dados e apaga o seu score. Se houver um pedido no banco, ele também é retirado e o acesso do banco é revogado."
                      />
                    )}
                  </div>
                </div>
              </article>
            );
          })}

          <p className="text-sm text-ink-2">
            Os registros de leitura vêm da operadora, que anota cada vez que alguém pede seus dados com uma
            autorização. Para apagar também o cadastro, use a opção de excluir a conta no{" "}
            <Link href="/cliente/perfil" className="font-semibold underline hover:no-underline">
              perfil
            </Link>
            .
          </p>
        </div>
      </div>
    </>
  );
}
