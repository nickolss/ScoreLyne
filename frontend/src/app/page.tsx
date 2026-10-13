import Link from "next/link";
import { Arrow, Check } from "@/components/icons";
import { DecisionBadge } from "@/components/score";
import { MariaStatement } from "@/components/statement";

const PARTIES = [
  {
    who: "Cliente",
    gets: "Acesso a crédito justo a partir de um histórico que já constrói no dia a dia.",
  },
  {
    who: "Banco",
    gets: "Novo canal para aprovar crédito a um público antes recusado, com risco controlado.",
  },
  {
    who: "Operadora",
    gets: "Retenção de clientes e incentivo à migração do pré-pago para o pós-pago.",
  },
];

const ALTERNATIVES = [
  ["Score de birôs", "Escala e padronização", "Sem histórico bancário, sem score"],
  ["Cadastro Positivo", "Premia quem paga em dia", "Só registra quem já tem crédito formal"],
  ["Comprovante de renda", "Verifica capacidade de pagamento", "Não captura renda informal"],
  ["Microcrédito orientado", "Relacionamento próximo", "Caro de operar, difícil de escalar"],
  ["Open Finance", "Dados ricos, decisão rápida", "Depende de conta bancária"],
  ["Agiota e “fiado”", "Rápido e sem burocracia", "Juros abusivos, não gera histórico"],
];

export default function Home() {
  return (
    <>
      {/* 1 · o extrato que já existe */}
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-14 pb-16 lg:py-20 grid lg:grid-cols-[1.15fr_0.85fr] gap-12 lg:gap-16 items-center">
          <div>
            <h1 className="display text-[clamp(2.75rem,7vw,5.75rem)]">
              Seis anos de recarga em dia{" "}
              <span className="bg-lime text-ink px-2 box-decoration-clone">também é histórico.</span>
            </h1>
            <p className="mt-8 text-lg sm:text-xl text-on-cobalt-2 max-w-[34rem] leading-relaxed">
              O ScoreLyne lê o relacionamento com a operadora de telefonia e o transforma num score de
              crédito itemizado, para quem os birôs não enxergam: autônomos, informais e desbancados.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-4">
              <Link
                href="/cliente"
                className="inline-flex items-center gap-3 bg-paper text-ink px-5 py-3.5 font-semibold hover:bg-lime transition-colors"
              >
                Simular meu score <Arrow />
              </Link>
              <Link href="/banco" className="inline-flex items-center gap-3 font-semibold underline hover:no-underline">
                Ver o painel do banco
              </Link>
            </div>
            <dl className="mt-14 grid grid-cols-3 border-t border-on-cobalt/40 max-w-[34rem]">
              {[
                ["Conta em banco", "nenhuma"],
                ["Score em birô", "nenhum"],
                ["Meses com recarga", "71/74"],
              ].map(([k, v]) => (
                <div key={k} className="pt-3 pr-3">
                  <dt className="label text-on-cobalt-2">{k}</dt>
                  <dd className="num text-lg mt-1">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <MariaStatement />
        </div>
      </section>

      {/* 2 · do extrato à decisão */}
      <section className="border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-20 pb-6">
          <h2 className="display text-4xl sm:text-5xl max-w-3xl">Do extrato à decisão, sem caixa-preta.</h2>
        </div>
        <ol className="mx-auto max-w-7xl px-4 sm:px-8 pb-20 grid md:grid-cols-3">
          <li className="pt-10 md:pr-8 md:border-r border-rule">
            <p className="num text-sm text-cobalt">1/3</p>
            <h3 className="mt-3 text-2xl font-bold">O cliente autoriza</h3>
            <p className="mt-3 text-ink-2 leading-relaxed">
              Escolhe quais dados da operadora compartilhar, com finalidade explícita e revogável a
              qualquer momento (LGPD).
            </p>
            <ul className="mt-6 border border-ink p-4 space-y-2 text-sm">
              {["Recargas dos últimos 24 meses", "Data de ativação da linha", "Pontualidade de faturas"].map((t) => (
                <li key={t} className="flex gap-2.5">
                  <Check /> {t}
                </li>
              ))}
            </ul>
          </li>
          <li className="pt-10 md:px-8 md:border-r border-rule">
            <p className="num text-sm text-cobalt">2/3</p>
            <h3 className="mt-3 text-2xl font-bold">O agente itemiza</h3>
            <p className="mt-3 text-ink-2 leading-relaxed">
              Recargas, permanência, pontualidade e consistência viram notas de 0 a 100. Cada uma soma ou
              tira pontos em relação a um cliente médio, com a mesma régua para todo mundo.
            </p>
            <div className="mt-6 border border-ink p-4 text-sm">
              <div className="flex items-baseline gap-2">
                <span>Regularidade de recargas</span>
                <span className="leader" aria-hidden="true" />
              </div>
              <p className="num mt-2 text-right">
                <span className="text-ink-2">100/100 →</span> +44,0 pts
              </p>
            </div>
          </li>
          <li className="pt-10 md:pl-8">
            <p className="num text-sm text-cobalt">3/3</p>
            <h3 className="mt-3 text-2xl font-bold">A decisão vem explicada</h3>
            <p className="mt-3 text-ink-2 leading-relaxed">
              Casos limítrofes vão para um analista humano. Quem é recusado recebe o caminho exato para
              melhorar.
            </p>
            <div className="mt-6 border border-ink p-4 flex flex-wrap gap-2">
              <DecisionBadge decision="aprovado" />
              <DecisionBadge decision="revisao" />
              <DecisionBadge decision="recusado" />
            </div>
          </li>
        </ol>
      </section>

      {/* 3 · a ponte */}
      <section className="border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 py-20 grid lg:grid-cols-[0.8fr_1.2fr] gap-10 lg:gap-16">
          <div>
            <h2 className="display text-4xl sm:text-5xl">Uma ponte com três lados.</h2>
            <p className="mt-6 text-ink-2 text-lg leading-relaxed max-w-md">
              A operadora já conhece o comportamento do cliente. O banco precisa de um sinal confiável. O
              agente coordena os dois com consentimento, sem expor dados brutos.
            </p>
          </div>
          <dl className="border-t-2 border-ink">
            {PARTIES.map((p) => (
              <div key={p.who} className="grid sm:grid-cols-[11rem_1fr] gap-x-8 gap-y-2 py-6 border-b border-rule">
                <dt className="display text-3xl">{p.who}</dt>
                <dd className="text-lg leading-relaxed sm:pt-1">{p.gets}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* 4 · alternativas */}
      <section className="bg-tint border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 py-20">
          <h2 className="display text-4xl sm:text-5xl max-w-3xl">Por que as soluções atuais falham.</h2>
          <div className="mt-10 overflow-x-auto border border-ink bg-paper">
            <table className="w-full text-left min-w-[40rem]">
              <thead>
                <tr className="border-b-2 border-ink">
                  <th className="label px-5 py-3 font-normal">Solução</th>
                  <th className="label px-5 py-3 font-normal">Faz bem</th>
                  <th className="label px-5 py-3 font-normal">Onde falha</th>
                </tr>
              </thead>
              <tbody>
                {ALTERNATIVES.map(([name, good, bad]) => (
                  <tr key={name} className="border-b border-rule">
                    <td className="px-5 py-4 font-semibold">{name}</td>
                    <td className="px-5 py-4 text-ink-2">{good}</td>
                    <td className="px-5 py-4">
                      <span className="flex items-baseline gap-2.5">
                        <span className="size-2 bg-red shrink-0 -translate-y-px" aria-hidden="true" />
                        {bad}
                      </span>
                    </td>
                  </tr>
                ))}
                <tr className="bg-lime border-t-2 border-ink">
                  <td className="px-5 py-4 font-bold">ScoreLyne</td>
                  <td className="px-5 py-4" colSpan={2}>
                    Usa o histórico que o cliente já tem com a operadora, com consentimento e decisão
                    explicada.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 5 · fechamento */}
      <section className="on-cobalt bg-cobalt text-on-cobalt">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 py-24 grid lg:grid-cols-[1fr_auto] gap-10 items-end">
          <h2 className="display text-[clamp(2.5rem,6vw,5rem)] max-w-4xl">
            O histórico já existe.{" "}
            <span className="bg-lime text-ink px-2 box-decoration-clone">Só faltava alguém ler.</span>
          </h2>
          <div className="flex flex-col gap-4 items-start">
            <Link
              href="/cliente"
              className="inline-flex items-center gap-3 bg-paper text-ink px-5 py-3.5 font-semibold hover:bg-lime transition-colors"
            >
              Simular meu score <Arrow />
            </Link>
            <Link href="/governanca" className="font-semibold underline hover:no-underline">
              Como protegemos seus dados
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
