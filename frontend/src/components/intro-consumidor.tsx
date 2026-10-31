import Link from "next/link";
import { Arrow, Check } from "@/components/icons";
import { btnSecondary } from "@/components/ui";
import { EXCLUDED_DATA, FACTOR_LABEL } from "@/lib/data";

const LIDO = [
  ["recargas", "Datas das recargas dos últimos 24 meses"],
  ["permanencia", "Desde quando a linha existe e os planos que teve"],
  ["pontualidade", "Se as faturas foram pagas, ou a recarga feita, em dia"],
  ["estabilidade", "Trocas de chip e portabilidades do número"],
  ["consistencia", "Os totais mensais gastos, sem o detalhe de cada compra"],
] as const;

const PASSOS = [
  ["Crie sua conta", "Só nome, CPF, celular e senha. Nada é lido da operadora ainda."],
  ["Confira seus dados", "Você corrige o que estiver errado antes de qualquer cálculo."],
  ["Escolha o que autorizar", "Item por item, com a finalidade escrita. Três são necessários; dois são opcionais."],
  ["Veja seu score explicado", "Cada fator com os pontos que deu ou tirou, e um assistente para tirar dúvidas."],
  ["Só então, se quiser, peça crédito", "O banco só recebe algo se você enviar um pedido, com uma autorização separada."],
] as const;

// Página de chegada do consumidor, antes de qualquer cadastro: explica o que o produto faz e o que ele
// lê antes de pedir um único dado.
export function IntroConsumidor({ contaExcluida = false }: { contaExcluida?: boolean }) {
  return (
    <>
      {contaExcluida && (
        <div className="bg-lime border-b border-ink" role="status">
          <p className="mx-auto max-w-7xl px-4 sm:px-8 py-3 text-sm font-semibold">
            Sua conta foi excluída. Os acessos aos seus dados foram revogados e o cadastro, o score e o histórico
            de pedidos foram apagados.
          </p>
        </div>
      )}

      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 py-16 lg:py-20 max-w-5xl">
          <p className="num text-sm text-on-cobalt-2">Para quem busca crédito</p>
          <h1 className="display text-[clamp(2.5rem,6vw,4.75rem)] mt-3 max-w-4xl">
            Entenda seu score antes de{" "}
            <span className="bg-lime text-ink px-2 box-decoration-clone">pedir qualquer coisa.</span>
          </h1>
          <p className="mt-8 text-lg sm:text-xl text-on-cobalt-2 max-w-[40rem] leading-relaxed">
            A ScoreLyne transforma o seu histórico com a operadora de celular em uma nota de crédito explicada.
            Você vê o que pesou a favor e contra, conversa com um assistente e decide se quer pedir crédito.
          </p>
          <div className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-4">
            <Link
              href="/cliente/cadastro"
              className="inline-flex items-center gap-3 bg-paper text-ink px-5 py-3.5 font-semibold hover:bg-lime transition-colors"
            >
              Criar conta <Arrow />
            </Link>
            <Link href="/cliente/entrar" className="font-semibold underline hover:no-underline">
              Já tenho conta
            </Link>
          </div>
        </div>
      </section>

      <section className="border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 py-16">
          <h2 className="display text-4xl max-w-3xl">Como funciona, em cinco passos.</h2>
          <ol className="mt-8 border-t-2 border-ink">
            {PASSOS.map(([titulo, texto], i) => (
              <li key={titulo} className="grid grid-cols-[3rem_1fr] sm:grid-cols-[3rem_16rem_1fr] gap-x-4 gap-y-1 py-5 border-b border-rule">
                <span className="num text-sm text-cobalt pt-1">{String(i + 1).padStart(2, "0")}</span>
                <h3 className="font-bold text-lg">{titulo}</h3>
                <p className="text-ink-2 col-start-2 sm:col-start-3">{texto}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-b border-ink bg-tint">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 py-16 grid md:grid-cols-2 gap-10">
          <div>
            <h2 className="display text-3xl">O que lemos.</h2>
            <ul className="mt-6 border-t-2 border-ink bg-paper">
              {LIDO.map(([chave, detalhe]) => (
                <li key={chave} className="flex gap-3 px-4 py-3 border-b border-rule">
                  <Check />
                  <span>
                    <span className="block font-semibold">{FACTOR_LABEL[chave]}</span>
                    <span className="block text-sm text-ink-2">{detalhe}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h2 className="display text-3xl">O que nunca lemos.</h2>
            <ul className="mt-6 border-t-2 border-ink bg-paper">
              {EXCLUDED_DATA.map((d) => (
                <li key={d} className="px-4 py-3 border-b border-rule line-through decoration-red decoration-2 text-ink-2">
                  {d}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section>
        <div className="mx-auto max-w-7xl px-4 sm:px-8 py-16">
          <h2 className="display text-4xl max-w-3xl">Você no controle.</h2>
          <dl className="mt-8 grid md:grid-cols-3 border-t-2 border-ink">
            {[
              ["Veja quem leu seus dados", "Cada acesso fica registrado com data e hora, e você consulta na tela de consentimentos."],
              ["Revogue quando quiser", "O acesso é bloqueado na hora e o score guardado é apagado. Se havia um pedido no banco, ele é retirado."],
              ["Apague sua conta", "Um botão no perfil revoga tudo e apaga cadastro, score e histórico de pedidos."],
            ].map(([k, v], i) => (
              <div key={k} className={`py-6 md:px-6 border-b md:border-b-0 border-rule ${i > 0 ? "md:border-l" : "md:pl-0"}`}>
                <dt className="font-bold text-lg">{k}</dt>
                <dd className="mt-2 text-ink-2 leading-relaxed">{v}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-10 flex flex-wrap gap-3">
            <Link href="/cliente/como-e-calculado" className={btnSecondary}>
              Ver como o score é calculado
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
