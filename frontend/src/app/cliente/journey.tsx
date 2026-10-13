"use client";

import { useEffect, useRef, useState } from "react";
import { Arrow } from "@/components/icons";
import { BaseLine, Barcode, DecisionBadge, FactorLines, ScoreScale, ScoreTotal } from "@/components/score";
import {
  type CartaoModelo,
  type Escopo,
  type PersonaDemo,
  type Solicitacao,
  ApiError,
  banco,
  operadora,
} from "@/lib/api";
import {
  EXCLUDED_DATA,
  FACTOR_LABEL,
  PERSONA_PEDIDOS,
  PLAN_LABEL,
  type PersonaPedido,
  brl,
  brl2,
  tenureLabel,
} from "@/lib/data";

type Step = "inicio" | "consentimento" | "analise" | "resultado";

type Persona = PersonaPedido & PersonaDemo;

const CONSENT_ITEMS: { key: Escopo; detail: string; required?: boolean }[] = [
  { key: "recargas", detail: "Datas das recargas dos últimos 24 meses", required: true },
  { key: "permanencia", detail: "Data de ativação da linha e histórico de planos", required: true },
  { key: "pontualidade", detail: "Pagamento de faturas ou recarga antes do saldo zerar", required: true },
  { key: "estabilidade", detail: "Trocas de chip e portabilidades do número" },
  { key: "consistencia", detail: "Totais mensais gastos com recarga ou fatura" },
];

const AGENT_STEPS = [
  "Registrando seu consentimento na operadora",
  "Recebendo só os dados autorizados",
  "Calculando fatores de comportamento",
  "Checando equidade: nenhuma variável sensível no modelo",
  "Gerando score e explicação da decisão",
];

const btnPrimary =
  "inline-flex items-center justify-center gap-3 bg-ink text-paper px-5 py-3.5 font-semibold hover:bg-cobalt transition-colors disabled:opacity-35 disabled:hover:bg-ink disabled:cursor-not-allowed";
const btnSecondary =
  "inline-flex items-center justify-center border border-ink px-5 py-3.5 font-semibold hover:bg-tint transition-colors";

const errorMessage = (e: unknown) => (e instanceof ApiError ? e.message : "Erro inesperado. Tente de novo.");

function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="border-2 border-red p-4" role="alert">
      <p className="font-semibold text-red-ink">Algo deu errado</p>
      <p className="mt-1 text-sm">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 text-sm font-semibold underline hover:no-underline">
          Tentar de novo
        </button>
      )}
    </div>
  );
}

export function Journey() {
  const [step, setStep] = useState<Step>("inicio");
  const [personas, setPersonas] = useState<Persona[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [modelo, setModelo] = useState<CartaoModelo | null>(null);
  const [personaId, setPersonaId] = useState("maria");
  const [consent, setConsent] = useState<Record<Escopo, boolean>>({
    recargas: true,
    permanencia: true,
    pontualidade: true,
    estabilidade: true,
    consistencia: true,
  });
  const [solicitacao, setSolicitacao] = useState<Solicitacao | null>(null);

  useEffect(() => {
    let alive = true;
    operadora
      .personas()
      .then((demo) => {
        if (!alive) return;
        const byKey = new Map(demo.map((p) => [p.chave, p]));
        setPersonas(
          PERSONA_PEDIDOS.flatMap((p) => {
            const d = byKey.get(p.chave);
            return d ? [{ ...d, ...p }] : [];
          }),
        );
        setLoadError(null);
      })
      .catch((e) => alive && setLoadError(errorMessage(e)));
    // O cartão do modelo só enriquece a tela de consentimento; sem ele a jornada segue.
    banco
      .modelo()
      .then((m) => alive && setModelo(m))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [attempt]);

  const persona = personas?.find((p) => p.chave === personaId) ?? personas?.[0];

  return (
    <div className="bg-paper border border-ink">
      <Progress step={step} />
      <div className="p-5 sm:p-10">
        {step === "inicio" && (
          <section className="feed">
            <h1 className="display text-4xl sm:text-5xl">Seu celular conta a sua história financeira.</h1>
            <p className="mt-5 text-ink-2 text-lg leading-relaxed">
              Sem conta em banco ou histórico no Serasa? Tudo bem. Com a sua autorização, usamos seu
              relacionamento com a operadora para calcular um score e buscar uma oferta de crédito.
            </p>

            <fieldset className="mt-10">
              <legend className="label text-ink-2">Escolha um perfil para simular</legend>
              {loadError && (
                <div className="mt-3">
                  <ErrorBox message={loadError} onRetry={() => setAttempt((n) => n + 1)} />
                </div>
              )}
              {!personas && !loadError && (
                <p className="mt-3 border border-dashed border-ink p-4 text-sm text-ink-2 animate-pulse">
                  Buscando perfis na operadora…
                </p>
              )}
              {personas && (
                <div className="mt-3 grid sm:grid-cols-3 lg:grid-cols-5 border border-ink">
                  {personas.map((p) => {
                    const active = p.chave === persona?.chave;
                    return (
                      <label
                        key={p.chave}
                        className={`cursor-pointer p-4 border-b border-r border-ink transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-cobalt has-[:focus-visible]:-outline-offset-4 ${
                          active ? "bg-cobalt text-on-cobalt" : "hover:bg-tint"
                        }`}
                      >
                        <input
                          type="radio"
                          name="persona"
                          value={p.chave}
                          checked={active}
                          onChange={() => setPersonaId(p.chave)}
                          className="sr-only"
                        />
                        <span className="block font-bold">{p.titular}</span>
                        <span className={`block text-sm ${active ? "text-on-cobalt-2" : "text-ink-2"}`}>
                          {p.occupation}
                        </span>
                        <span className={`num mt-4 block text-[11px] ${active ? "text-on-cobalt-2" : "text-ink-2"}`}>
                          {PLAN_LABEL[p.plano]} · {tenureLabel(p.tenureMonths)}
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            </fieldset>

            {persona && (
              <dl className="mt-6 grid grid-cols-2 border-t-2 border-ink">
                <div className="pt-3">
                  <dt className="label text-ink-2">Valor desejado</dt>
                  <dd className="num text-2xl mt-1">{brl(persona.requested)}</dd>
                </div>
                <div className="pt-3">
                  <dt className="label text-ink-2">Para quê</dt>
                  <dd className="mt-1.5">{persona.purpose}</dd>
                </div>
              </dl>
            )}

            <button
              onClick={() => setStep("consentimento")}
              disabled={!persona}
              className={`${btnPrimary} mt-10 w-full sm:w-auto`}
            >
              Continuar <Arrow />
            </button>
          </section>
        )}

        {step === "consentimento" && (
          <ConsentStep
            consent={consent}
            setConsent={setConsent}
            modelo={modelo}
            onBack={() => setStep("inicio")}
            onAccept={() => setStep("analise")}
          />
        )}

        {step === "analise" && persona && (
          <AnalysisStep
            persona={persona}
            consent={consent}
            onBack={() => setStep("consentimento")}
            onDone={(s) => {
              setSolicitacao(s);
              setStep("resultado");
            }}
          />
        )}

        {step === "resultado" && persona && solicitacao && (
          <ResultStep
            initial={solicitacao}
            persona={persona}
            onRestart={() => {
              setSolicitacao(null);
              setStep("inicio");
            }}
          />
        )}
      </div>
    </div>
  );
}

function Progress({ step }: { step: Step }) {
  const order: Step[] = ["inicio", "consentimento", "analise", "resultado"];
  const labels = ["Pedido", "Consentimento", "Análise", "Resultado"];
  const idx = order.indexOf(step);
  return (
    <ol className="grid grid-cols-4 border-b border-ink" aria-label="Etapas">
      {labels.map((l, i) => (
        <li
          key={l}
          aria-current={i === idx ? "step" : undefined}
          className={`px-2 sm:px-4 py-3 border-r border-ink last:border-r-0 ${
            i === idx ? "bg-cobalt text-on-cobalt" : i < idx ? "bg-tint" : ""
          }`}
        >
          <span className={`num block text-[10px] ${i === idx ? "text-on-cobalt-2" : "text-ink-2"}`}>
            {i + 1}/4
          </span>
          <span className="block text-xs sm:text-sm font-semibold truncate">{l}</span>
        </li>
      ))}
    </ol>
  );
}

function ConsentStep({
  consent,
  setConsent,
  modelo,
  onBack,
  onAccept,
}: {
  consent: Record<Escopo, boolean>;
  setConsent: (c: Record<Escopo, boolean>) => void;
  modelo: CartaoModelo | null;
  onBack: () => void;
  onAccept: () => void;
}) {
  const [read, setRead] = useState(false);
  const loss = (key: Escopo) => modelo?.fatores.find((f) => f.chave === key)?.perda_maxima_se_omitir;

  return (
    <section className="feed">
      <h1 className="display text-4xl sm:text-5xl">O que você autoriza.</h1>
      <p className="mt-5 text-ink-2 leading-relaxed">
        Finalidade única: calcular seu score de crédito para esta solicitação. Válido por 30 dias e
        revogável a qualquer momento. Os três primeiros itens são necessários. Os outros são opcionais,
        mas quem não autoriza entra com o pior valor naquele fator: esconder dados nunca aumenta o score.
      </p>

      <ul className="mt-8 border-t-2 border-ink">
        {CONSENT_ITEMS.map((item) => {
          const points = loss(item.key);
          return (
            <li key={item.key} className="border-b border-rule">
              <label className={`flex items-start gap-4 py-4 ${item.required ? "" : "cursor-pointer"}`}>
                <input
                  type="checkbox"
                  className="mt-1 size-4 accent-[var(--cobalt)]"
                  checked={consent[item.key]}
                  disabled={item.required}
                  onChange={(e) => setConsent({ ...consent, [item.key]: e.target.checked })}
                />
                <span className="flex-1">
                  <span className="font-semibold">{FACTOR_LABEL[item.key]}</span>
                  {item.required && <span className="label ml-2 border border-ink px-1.5 py-0.5">necessário</span>}
                  <span className="block text-sm text-ink-2 mt-1">{item.detail}</span>
                  {!item.required && points !== undefined && (
                    <span className={`block text-xs mt-1.5 ${consent[item.key] ? "text-ink-2" : "font-semibold text-red-ink"}`}>
                      {points > 0
                        ? `Se não autorizar, seu score pode cair até ${points} pontos.`
                        : "Hoje este fator não altera o score: pode deixar de fora sem custo."}
                    </span>
                  )}
                </span>
              </label>
            </li>
          );
        })}
      </ul>

      <div className="mt-6 border border-dashed border-ink p-4">
        <p className="label">Nunca usamos</p>
        <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-ink-2">
          {EXCLUDED_DATA.map((d) => (
            <li key={d} className="line-through decoration-red decoration-2">
              {d}
            </li>
          ))}
        </ul>
      </div>

      <label className="mt-8 flex items-start gap-3 text-sm cursor-pointer bg-tint p-4">
        <input
          type="checkbox"
          className="mt-0.5 size-4 accent-[var(--cobalt)]"
          checked={read}
          onChange={(e) => setRead(e.target.checked)}
        />
        <span>
          Li e autorizo o compartilhamento dos dados acima entre a operadora e a instituição
          financeira, nos termos da LGPD.
        </span>
      </label>

      <div className="mt-8 flex gap-3">
        <button onClick={onBack} className={btnSecondary}>
          Voltar
        </button>
        <button onClick={onAccept} disabled={!read} className={`${btnPrimary} flex-1 sm:flex-none`}>
          Autorizar e calcular <Arrow />
        </button>
      </div>
    </section>
  );
}

function AnalysisStep({
  persona,
  consent,
  onBack,
  onDone,
}: {
  persona: Persona;
  consent: Record<Escopo, boolean>;
  onBack: () => void;
  onDone: (s: Solicitacao) => void;
}) {
  const [done, setDone] = useState(0);
  const [result, setResult] = useState<Solicitacao | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Guarda a requisição para o StrictMode (que roda o efeito duas vezes) não criar dois pedidos.
  const request = useRef<Promise<Solicitacao> | null>(null);

  useEffect(() => {
    if (!request.current) {
      const escopos = (Object.keys(consent) as Escopo[]).filter((k) => consent[k]);
      request.current = operadora
        .consentir({ telefone: persona.telefone, cpf: persona.cpf, escopos })
        .then((c) =>
          banco.criar({
            nome: persona.titular,
            telefone: persona.telefone,
            consentimento_id: c.id,
            valor_solicitado: persona.requested,
            finalidade: persona.purpose,
            ocupacao: persona.occupation,
            cidade: persona.cidade,
            uf: persona.uf,
          }),
        );
    }
    let alive = true;
    request.current.then(
      (s) => alive && setResult(s),
      (e) => alive && setError(errorMessage(e)),
    );
    return () => {
      alive = false;
    };
  }, [persona, consent]);

  // A animação avança sozinha até a última etapa, que espera a resposta do agente.
  useEffect(() => {
    if (error) return;
    const last = AGENT_STEPS.length - 1;
    if (done >= AGENT_STEPS.length) {
      const t = setTimeout(() => result && onDone(result), 400);
      return () => clearTimeout(t);
    }
    if (done === last && !result) return;
    const t = setTimeout(() => setDone((d) => d + 1), 650);
    return () => clearTimeout(t);
  }, [done, result, error, onDone]);

  return (
    <section aria-live="polite">
      <h1 className="display text-4xl sm:text-5xl">O agente está analisando.</h1>
      <p className="mt-4 text-ink-2">Leva só alguns segundos.</p>
      <ol className="mt-8 border-t-2 border-ink">
        {AGENT_STEPS.map((s, i) => {
          const state = i < done ? "done" : i === done && !error ? "doing" : "todo";
          return (
            <li
              key={s}
              className={`flex items-center gap-3 py-3 border-b border-rule transition-opacity ${state === "todo" ? "opacity-35" : ""}`}
            >
              <span className="num text-xs text-ink-2 w-8">{String(i + 1).padStart(2, "0")}</span>
              <span className="flex-1">{s}</span>
              <span className="num text-xs w-16 text-right">
                {state === "done" && <span className="bg-lime px-1">ok</span>}
                {state === "doing" && <span className="text-cobalt animate-pulse">lendo…</span>}
              </span>
            </li>
          );
        })}
      </ol>
      {error && (
        <div className="mt-6">
          <ErrorBox message={error} />
          <button onClick={onBack} className={`${btnSecondary} mt-4`}>
            Voltar ao consentimento
          </button>
        </div>
      )}
    </section>
  );
}

function ResultStep({
  initial,
  persona,
  onRestart,
}: {
  initial: Solicitacao;
  persona: Persona;
  onRestart: () => void;
}) {
  const [sol, setSol] = useState(initial);
  const [term, setTerm] = useState(12);
  const [error, setError] = useState<string | null>(null);
  const [revoking, setRevoking] = useState(false);

  // Enquanto estiver com um analista, acompanha a decisão em tempo real.
  useEffect(() => {
    if (sol.status !== "revisao") return;
    const t = setInterval(() => {
      banco.obter(sol.id).then(setSol).catch(() => {});
    }, 4000);
    return () => clearInterval(t);
  }, [sol.id, sol.status]);

  async function revoke() {
    setRevoking(true);
    setError(null);
    try {
      setSol(await banco.revogar(sol.id));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setRevoking(false);
    }
  }

  const a = sol.analise;
  if (sol.status === "revogado" || !a) {
    return (
      <section className="feed">
        <h1 className="display text-4xl sm:text-5xl">Consentimento revogado.</h1>
        <p className="mt-5 text-ink-2 leading-relaxed">
          A operadora bloqueou novos acessos aos seus dados, e o banco apagou o score e a análise desta
          solicitação. Fica registrado só que ela existiu. Você pode simular de novo quando quiser.
        </p>
        <button onClick={onRestart} className={`${btnPrimary} mt-8`}>
          Nova simulação
        </button>
      </section>
    );
  }

  const status = sol.status;
  const first = persona.titular.split(" ")[0];
  const offer = a.oferta;
  const parcela = offer?.parcelas.find((p) => p.prazo_meses === term) ?? offer?.parcelas[0];
  const skipped = a.fatores.filter((f) => f.status === "nao_autorizado").length;
  const review = sol.revisao_humana;

  return (
    <section className="feed">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="label text-ink-2">Resultado da análise · {persona.titular}</p>
        <DecisionBadge decision={status} />
      </div>
      <h1 className="display text-3xl sm:text-4xl mt-5">
        {status === "aprovado" && (review ? `${first}, um analista aprovou seu crédito.` : `${first}, seu crédito foi pré-aprovado.`)}
        {status === "revisao" && "Seu pedido está com um analista."}
        {status === "recusado" && "Ainda não deu desta vez."}
      </h1>
      <p className="mt-3 text-ink-2 leading-relaxed">
        {status === "aprovado" && !review && a.pontos_fortes[0] && `O que mais contou a seu favor: ${a.pontos_fortes[0].toLowerCase()}.`}
        {status === "revisao" &&
          "Uma pessoa do banco revisa em até 1 dia útil. Nesta faixa, o agente nunca decide sozinho. Esta tela atualiza quando houver decisão."}
        {status === "recusado" && "Mas você não sai de mãos vazias: veja abaixo exatamente o que fazer para chegar lá."}
      </p>

      {review && (
        <div className="mt-6 border border-ink">
          <p className={`label px-4 py-2 ${review.veredito === "aprovar" ? "bg-lime" : "bg-red text-paper"}`}>
            Decisão do analista
          </p>
          <p className="p-4 text-sm">&ldquo;{review.justificativa}&rdquo;</p>
        </div>
      )}

      {status === "revisao" && a.motivos_revisao.length > 0 && (
        <ul className="mt-6 border border-dashed border-ink p-4 text-sm space-y-1">
          {a.motivos_revisao.map((m) => (
            <li key={m}>· {m}</li>
          ))}
        </ul>
      )}

      <div className="mt-8 border-t-2 border-ink pt-5">
        <ScoreTotal score={a.score} faixa={a.faixa} />
        <ScoreScale score={a.score} />
      </div>

      {status !== "recusado" && offer && parcela && (
        <div className="mt-4 border border-ink">
          <div className="px-5 py-3 border-b border-ink bg-tint flex justify-between gap-3">
            <h2 className="font-bold">{status === "aprovado" ? "Sua oferta" : "Oferta prevista, sujeita à revisão"}</h2>
            {offer.valor_ofertado < sol.valor_solicitado && (
              <span className="label text-ink-2 self-center">limite {brl(offer.limite)}</span>
            )}
          </div>
          <dl className="grid grid-cols-2 sm:grid-cols-3">
            {[
              ["Valor", brl(offer.valor_ofertado)],
              ["Taxa", `${offer.taxa_mensal.toFixed(2).replace(".", ",")}% a.m.`],
              [`${parcela.prazo_meses}x de`, brl2(parcela.valor_parcela)],
            ].map(([k, v], i) => (
              <div
                key={k}
                className={`px-4 sm:px-5 py-4 border-rule ${i < 2 ? "border-r" : "col-span-2 sm:col-span-1 border-t sm:border-t-0"}`}
              >
                <dt className="label text-ink-2">{k}</dt>
                <dd className={`num text-lg sm:text-2xl mt-1 whitespace-nowrap ${i === 2 ? "font-semibold" : ""}`}>{v}</dd>
              </div>
            ))}
          </dl>
          <div className="px-5 pb-5">
            <div className="flex border border-ink w-fit" role="radiogroup" aria-label="Prazo">
              {offer.parcelas.map((p) => (
                <button
                  key={p.prazo_meses}
                  role="radio"
                  aria-checked={p.prazo_meses === parcela.prazo_meses}
                  onClick={() => setTerm(p.prazo_meses)}
                  className={`num whitespace-nowrap px-3 sm:px-4 py-2 text-xs border-r border-ink last:border-r-0 transition-colors ${
                    p.prazo_meses === parcela.prazo_meses ? "bg-ink text-paper" : "hover:bg-tint"
                  }`}
                >
                  {p.prazo_meses} meses
                </button>
              ))}
            </div>
            <p className="mt-4 text-xs text-ink-2">
              Para comparação: crédito informal costuma cobrar de 10% a 30% ao mês.
            </p>
          </div>
        </div>
      )}

      {status === "aprovado" && !offer && (
        <p className="mt-4 border border-ink p-4 text-sm">
          Seu score ficou abaixo da faixa de oferta automática, então o banco vai enviar o valor e as
          condições aprovadas pelo analista.
        </p>
      )}

      {status === "recusado" && a.plano_de_melhora.length > 0 && (
        <div className="mt-6 border border-ink">
          <h2 className="px-5 py-3 border-b border-ink bg-lime font-bold">Seu plano para chegar lá</h2>
          <ol className="p-5 space-y-2 text-sm list-decimal list-inside">
            {a.plano_de_melhora.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ol>
        </div>
      )}

      <div className="mt-10">
        <h2 className="display text-2xl">Por que esse score.</h2>
        <p className="mt-2 text-sm text-ink-2">
          Cada fator vai de 0 a 100. Os pontos mostram quanto ele soma ou tira em relação a um cliente
          médio, com a mesma régua para todas as pessoas.
          {skipped > 0 &&
            ` ${skipped} ${skipped === 1 ? "fator não autorizado entrou" : "fatores não autorizados entraram"} com o pior valor possível.`}
        </p>
        <div className="mt-4 border-t-2 border-ink">
          <BaseLine base={a.pontos_base} />
          <FactorLines factors={a.fatores} showTips={status !== "recusado"} />
        </div>
      </div>

      {error && (
        <div className="mt-6">
          <ErrorBox message={error} />
        </div>
      )}

      <div className="mt-10 -mx-5 sm:-mx-10 -mb-5 sm:-mb-10">
        <div className="perf text-ink" aria-hidden="true" />
        <div className="px-5 sm:px-10 py-5 bg-tint flex flex-wrap items-center gap-3">
          <button onClick={onRestart} className={`${btnSecondary} bg-paper`}>
            Simular outro perfil
          </button>
          <button
            onClick={revoke}
            disabled={revoking}
            className="px-5 py-3.5 font-semibold text-red-ink underline hover:no-underline disabled:opacity-50"
          >
            {revoking ? "Revogando…" : "Revogar consentimento"}
          </button>
          <Barcode value={sol.id} className="hidden sm:block ml-auto h-9 w-28" />
        </div>
      </div>
    </section>
  );
}
