import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { BackendDown } from "@/components/backend-down";
import { Arrow } from "@/components/icons";
import { IntroConsumidor } from "@/components/intro-consumidor";
import { DecisionBadge, ScoreScale, ScoreTotal } from "@/components/score";
import { btnPrimary, btnSecondary } from "@/components/ui";
import { ApiError, type ConsentimentoDetalhe, type SituacaoSolicitacao } from "@/lib/api";
import { consumidorLogado } from "@/lib/api-servidor";
import { EXCLUDED_DATA, brl, dataCurta, dataHora } from "@/lib/data";

export const metadata: Metadata = { title: "Início" };

// Depende de quem está logado: renderiza sempre no momento da requisição.
export const dynamic = "force-dynamic";

export default async function ClienteInicioPage(props: PageProps<"/cliente">) {
  const { conta } = await props.searchParams;
  const api = await consumidorLogado();
  if (!api) return <IntroConsumidor contaExcluida={conta === "excluida"} />;

  const naoCalculou = (e: unknown) => {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  };

  let dados;
  try {
    const cliente = await api.eu();
    const [score, consentimentos] = await Promise.all([
      api.meuScore().catch(naoCalculou),
      // O histórico de acessos vem da operadora: se ela estiver fora do ar, o resto do painel segue.
      api.meusConsentimentos().catch((): ConsentimentoDetalhe[] => []),
    ]);
    const situacao = cliente.enviado_ao_credor
      ? await api.minhaSolicitacao().catch((): SituacaoSolicitacao | null => null)
      : null;
    dados = { cliente, score, consentimentos, situacao };
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/cliente/entrar");
    return <BackendDown service="consumidor" message={e instanceof ApiError ? e.message : "Erro ao carregar seus dados."} />;
  }

  const { cliente, score, consentimentos, situacao } = dados;
  const acessos = consentimentos.reduce((n, c) => n + c.acessos.length, 0);
  const ultimo = consentimentos.flatMap((c) => c.acessos).map((a) => a.em).sort().at(-1);

  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-12 pb-10">
          <p className="num text-sm text-on-cobalt-2">Persona · Consumidor</p>
          <h1 className="display text-5xl sm:text-6xl mt-3">Olá, {cliente.nome.split(" ")[0]}.</h1>
          <p className="mt-5 text-on-cobalt-2 max-w-2xl leading-relaxed">
            {score
              ? "Seu score está calculado. Veja o que pesou nele, converse com o assistente ou acompanhe o seu pedido."
              : "Você ainda não calculou o seu score. Leva alguns minutos e você decide o que autorizar."}
          </p>
        </div>
      </section>

      <div className="bg-tint">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 py-10 grid lg:grid-cols-3 gap-6 items-start">
          <section className="border border-ink bg-paper lg:col-span-2" aria-labelledby="card-score">
            <h2 id="card-score" className="px-5 py-3 border-b border-ink bg-tint font-bold">
              Meu score
            </h2>
            {score ? (
              <div className="p-5">
                <ScoreTotal score={score.analise.score} faixa={score.analise.faixa} />
                <ScoreScale score={score.analise.score} />
                <p className="mt-4 text-sm text-ink-2">
                  Calculado em {dataHora(score.calculado_em)}, para {brl(score.valor_solicitado)}.
                </p>
                <Link href="/cliente/score" className={`${btnPrimary} mt-5`}>
                  Ver detalhes e falar com o assistente <Arrow />
                </Link>
              </div>
            ) : (
              <div className="p-5">
                <p className="leading-relaxed">
                  {cliente.consentimento_ativo
                    ? "Você já autorizou a leitura dos dados. Falta só dizer quanto precisa para calcular."
                    : "Antes de calcular, você confere seus dados e escolhe o que autorizar."}
                </p>
                <Link href="/cliente/score" className={`${btnPrimary} mt-5`}>
                  Calcular meu score <Arrow />
                </Link>
              </div>
            )}
          </section>

          <div className="space-y-6">
            <section className="border border-ink bg-paper" aria-labelledby="card-pedido">
              <h2 id="card-pedido" className="px-5 py-3 border-b border-ink bg-tint font-bold">
                Meu pedido ao banco
              </h2>
              <div className="p-5 text-sm">
                {situacao ? (
                  <>
                    <DecisionBadge decision={situacao.status} />
                    <p className="mt-3 text-ink-2">
                      Pedido de {score ? brl(score.valor_solicitado) : "crédito"}, atualizado em{" "}
                      {dataHora(situacao.atualizado_em)}.
                    </p>
                    {situacao.revisao_humana && (
                      <p className="mt-2">&ldquo;{situacao.revisao_humana.justificativa}&rdquo;</p>
                    )}
                  </>
                ) : cliente.enviado_ao_credor ? (
                  <p className="text-ink-2">Pedido enviado. Não foi possível consultar a situação agora.</p>
                ) : (
                  <p className="text-ink-2">Você não tem nenhum pedido enviado. Só enviamos algo ao banco se você pedir.</p>
                )}
                <Link href="/cliente/pedidos" className="mt-4 inline-block font-semibold underline hover:no-underline">
                  Ver histórico de pedidos
                </Link>
              </div>
            </section>

            <section className="border border-ink bg-paper" aria-labelledby="card-consent">
              <h2 id="card-consent" className="px-5 py-3 border-b border-ink bg-tint font-bold">
                Meus dados autorizados
              </h2>
              <div className="p-5 text-sm">
                {consentimentos.length ? (
                  <>
                    <p>
                      <span className="num text-2xl">{consentimentos.length}</span>{" "}
                      {consentimentos.length === 1 ? "autorização ativa" : "autorizações ativas"},{" "}
                      <span className="num">{acessos}</span> {acessos === 1 ? "leitura registrada" : "leituras registradas"}.
                    </p>
                    <p className="mt-2 text-ink-2">
                      {ultimo ? `Última leitura em ${dataHora(ultimo)}.` : "Nenhuma leitura até agora."} Válidas até{" "}
                      {dataCurta(consentimentos[0].expira_em)}.
                    </p>
                  </>
                ) : (
                  <p className="text-ink-2">Você não autorizou nada. Nenhum dado seu é lido.</p>
                )}
                <Link href="/cliente/consentimentos" className="mt-4 inline-block font-semibold underline hover:no-underline">
                  Ver quem acessou e revogar
                </Link>
              </div>
            </section>
          </div>
        </div>

        {!cliente.consentimento_ativo && (
          <div className="mx-auto max-w-7xl px-4 sm:px-8 pb-12">
            <section className="border border-dashed border-ink bg-paper p-6 grid md:grid-cols-2 gap-6">
              <div>
                <h2 className="font-bold text-lg">Antes de começar: o que você vai autorizar</h2>
                <p className="mt-2 text-sm text-ink-2 leading-relaxed">
                  Cinco tipos de informação sobre a sua linha: recargas, tempo de linha, pontualidade, trocas de chip
                  e valor gasto por mês. Três são necessários e dois são opcionais. Você revoga quando quiser.
                </p>
                <Link href="/cliente/como-e-calculado" className={`${btnSecondary} mt-4`}>
                  Ver como é calculado
                </Link>
              </div>
              <div>
                <p className="label">Nunca usamos</p>
                <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-ink-2">
                  {EXCLUDED_DATA.map((d) => (
                    <li key={d} className="line-through decoration-red decoration-2">
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          </div>
        )}
      </div>
    </>
  );
}
