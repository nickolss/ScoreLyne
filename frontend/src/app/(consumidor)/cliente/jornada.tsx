"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AssistenteScore } from "@/components/assistente";
import { Arrow } from "@/components/icons";
import { BaseLine, Barcode, DecisionBadge, FactorLines, ScoreScale, ScoreTotal } from "@/components/score";
import { btnPrimary, btnSecondary, campo } from "@/components/ui";
import {
  type Cliente,
  type CartaoModelo,
  type Escopo,
  type MeuScore,
  type SituacaoSolicitacao,
} from "@/lib/api";
import { consumidorNoBrowser as api } from "@/lib/api-browser";
import { EXCLUDED_DATA, FACTOR_LABEL, brl, brl2 } from "@/lib/data";
import { mensagemDeErro, sessaoExpirada } from "@/lib/erros";

type Etapa = "dados" | "consentimento" | "pedido" | "analise" | "resultado" | "revogado";

const ETAPAS: { chave: Etapa[]; rotulo: string }[] = [
  { chave: ["dados"], rotulo: "Seus dados" },
  { chave: ["consentimento"], rotulo: "Consentimento" },
  { chave: ["pedido", "analise"], rotulo: "Pedido" },
  { chave: ["resultado", "revogado"], rotulo: "Resultado" },
];

const CONSENT_ITEMS: { key: Escopo; detail: string; required?: boolean }[] = [
  { key: "recargas", detail: "Datas das recargas dos últimos 24 meses", required: true },
  { key: "permanencia", detail: "Data de ativação da linha e histórico de planos", required: true },
  { key: "pontualidade", detail: "Pagamento de faturas ou recarga antes do saldo zerar", required: true },
  { key: "estabilidade", detail: "Trocas de chip e portabilidades do número" },
  { key: "consistencia", detail: "Totais mensais gastos com recarga ou fatura" },
];

const AGENT_STEPS = [
  "Lendo só os dados que você autorizou",
  "Calculando fatores de comportamento",
  "Checando equidade: nenhuma variável sensível no modelo",
  "Gerando score e explicação",
];

const FRASE_DECISAO = {
  aprovado: "o agente do banco pré-aprovaria o pedido",
  revisao: "o pedido iria para a análise de uma pessoa do banco",
  recusado: "o agente do banco não aprovaria o pedido agora",
} as const;

function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="border-2 border-red p-4" role="alert">
      <p className="font-semibold text-red-ink">Algo deu errado</p>
      <p className="mt-1 text-sm">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 text-sm font-semibold underline hover:underline-offset-4">
          Tentar de novo
        </button>
      )}
    </div>
  );
}

// Quem paga a plataforma e o que isso muda para quem pede crédito. Fica à vista antes do consentimento e
// antes do envio do pedido, porque é aí que um incentivo financeiro poderia pesar. Veja docs/MVP.md.
function AvisoRemuneracao({ className = "" }: { className?: string }) {
  return (
    <aside className={`border border-ink ${className}`} aria-labelledby="aviso-remuneracao">
      <h2 id="aviso-remuneracao" className="label px-4 py-2 bg-tint border-b border-ink">
        Como a ScoreLyne ganha dinheiro
      </h2>
      <ul className="p-4 space-y-1.5 text-sm">
        <li>· Você não paga nada.</li>
        <li>· O banco parceiro paga um valor fixo por análise, aprovada ou não.</li>
        <li>· Não ganhamos comissão se o seu crédito for aprovado, então não temos motivo para empurrar um pedido.</li>
        <li>· Hoje há um só banco parceiro e nenhum é destacado por pagar mais.</li>
      </ul>
    </aside>
  );
}

const maskCpf = (c: string) => `${c.slice(0, 3)}.•••.•••-${c.slice(-2)}`;

export function Jornada({
  clienteInicial,
  scoreInicial,
  situacaoInicial,
  modelo,
}: {
  clienteInicial: Cliente;
  scoreInicial: MeuScore | null;
  situacaoInicial: SituacaoSolicitacao | null;
  modelo: CartaoModelo | null;
}) {
  const router = useRouter();
  const [cliente, setCliente] = useState(clienteInicial);
  const [score, setScore] = useState(scoreInicial);
  const [situacao, setSituacao] = useState(situacaoInicial);
  const [pedido, setPedido] = useState<Pedido | null>(null);
  const [etapa, setEtapa] = useState<Etapa>(
    scoreInicial ? "resultado" : clienteInicial.consentimento_ativo ? "pedido" : "dados",
  );
  const [consent, setConsent] = useState<Record<Escopo, boolean>>({
    recargas: true,
    permanencia: true,
    pontualidade: true,
    estabilidade: true,
    consistencia: true,
  });

  // A sessão venceu (o token dura 1 hora): volta para o login.
  const expirou = () => router.replace("/cliente/entrar");

  return (
    <div className="bg-paper border border-ink">
      <Progresso etapa={etapa} />
      <div className="p-5 sm:p-10">
        {etapa === "dados" && (
          <DadosStep
            cliente={cliente}
            onExpirou={expirou}
            onSalvo={(c, mudouTelefone) => {
              setCliente(c);
              if (mudouTelefone) {
                setScore(null);
                setSituacao(null);
              }
              setEtapa(c.consentimento_ativo ? (score && !mudouTelefone ? "resultado" : "pedido") : "consentimento");
            }}
          />
        )}

        {etapa === "consentimento" && (
          <ConsentStep
            consent={consent}
            setConsent={setConsent}
            modelo={modelo}
            onBack={() => setEtapa("dados")}
            onExpirou={expirou}
            onAutorizado={(c) => {
              setCliente(c);
              setEtapa("pedido");
            }}
          />
        )}

        {etapa === "pedido" && (
          <PedidoStep
            padrao={score ?? undefined}
            onBack={() => setEtapa(score ? "resultado" : "dados")}
            onConfirmar={(p) => {
              setPedido(p);
              setEtapa("analise");
            }}
          />
        )}

        {etapa === "analise" && pedido && (
          <AnaliseStep
            pedido={pedido}
            onExpirou={expirou}
            onBack={() => setEtapa("pedido")}
            onDone={(s) => {
              setScore(s);
              setEtapa("resultado");
            }}
          />
        )}

        {etapa === "resultado" && score && (
          <ResultadoStep
            cliente={cliente}
            score={score}
            situacao={situacao}
            onExpirou={expirou}
            onCliente={setCliente}
            onSituacao={setSituacao}
            onEditarDados={() => setEtapa("dados")}
            onRecalcular={() => setEtapa("pedido")}
            onRevogado={(c) => {
              setCliente(c);
              setScore(null);
              setSituacao(null);
              setEtapa("revogado");
            }}
          />
        )}

        {etapa === "revogado" && (
          <section className="feed">
            <h1 className="display text-4xl sm:text-5xl">Consentimento revogado.</h1>
            <p className="mt-5 text-ink-2 leading-relaxed">
              A operadora bloqueou novos acessos aos seus dados e o score guardado foi apagado. Se você tinha
              enviado um pedido ao banco, ele também foi retirado: o banco apagou a análise e só fica o registro
              de que ela existiu. Seu cadastro continua, e você pode calcular de novo quando quiser.
            </p>
            <button onClick={() => setEtapa("consentimento")} className={`${btnPrimary} mt-8`}>
              Autorizar de novo
            </button>
          </section>
        )}
      </div>
    </div>
  );
}

function Progresso({ etapa }: { etapa: Etapa }) {
  const atual = ETAPAS.findIndex((e) => e.chave.includes(etapa));
  return (
    <ol className="grid grid-cols-4 border-b border-ink" aria-label="Etapas">
      {ETAPAS.map((e, i) => (
        <li
          key={e.rotulo}
          aria-current={i === atual ? "step" : undefined}
          className={`px-2 sm:px-4 py-3 border-r border-ink last:border-r-0 ${
            i === atual ? "bg-cobalt text-on-cobalt" : i < atual ? "bg-tint" : ""
          }`}
        >
          <span className={`num block text-[10px] ${i === atual ? "text-on-cobalt-2" : "text-ink-2"}`}>{i + 1}/4</span>
          <span className="block text-xs sm:text-sm font-semibold truncate">{e.rotulo}</span>
        </li>
      ))}
    </ol>
  );
}

// --- 1 · Seus dados: validar ou corrigir ----------------------------------------------

function DadosStep({
  cliente,
  onSalvo,
  onExpirou,
}: {
  cliente: Cliente;
  onSalvo: (c: Cliente, mudouTelefone: boolean) => void;
  onExpirou: () => void;
}) {
  const [v, setV] = useState({
    telefone: cliente.telefone,
    ocupacao: cliente.ocupacao ?? "",
    cidade: cliente.cidade ?? "",
    uf: cliente.uf ?? "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setV((a) => ({ ...a, [k]: k === "uf" ? e.target.value.toUpperCase() : e.target.value }));

  const telefone = v.telefone.replace(/\D/g, "");
  const mudouTelefone = telefone !== cliente.telefone;
  const mudou =
    mudouTelefone || v.ocupacao !== (cliente.ocupacao ?? "") || v.cidade !== (cliente.cidade ?? "") || v.uf !== (cliente.uf ?? "");

  async function continuar() {
    setBusy(true);
    setError(null);
    try {
      if (!mudou) return onSalvo(cliente, false);
      const c = await api.atualizar({
        ...(mudouTelefone ? { telefone } : {}),
        ...(v.ocupacao !== (cliente.ocupacao ?? "") && v.ocupacao ? { ocupacao: v.ocupacao } : {}),
        ...(v.cidade !== (cliente.cidade ?? "") && v.cidade ? { cidade: v.cidade } : {}),
        ...(v.uf !== (cliente.uf ?? "") && v.uf ? { uf: v.uf } : {}),
      });
      onSalvo(c, mudouTelefone);
    } catch (e) {
      if (sessaoExpirada(e)) return onExpirou();
      setError(mensagemDeErro(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="feed">
      <h1 className="display text-4xl sm:text-5xl">Seus dados estão certos?</h1>
      <p className="mt-5 text-ink-2 text-lg leading-relaxed">
        O score só é justo se partir de dados corretos. Confira o que temos sobre você e corrija o que for
        preciso antes de seguir.
      </p>

      <dl className="mt-8 grid sm:grid-cols-2 border-t-2 border-ink">
        <div className="py-3 sm:pr-4 sm:border-r border-rule border-b">
          <dt className="label text-ink-2">Nome</dt>
          <dd className="mt-1">{cliente.nome}</dd>
        </div>
        <div className="py-3 sm:pl-4 border-b border-rule">
          <dt className="label text-ink-2">CPF</dt>
          <dd className="num mt-1">{maskCpf(cliente.cpf)}</dd>
        </div>
      </dl>

      <div className="mt-6 grid sm:grid-cols-2 gap-x-5 gap-y-5">
        <div>
          <label htmlFor="telefone" className="label">
            Celular com DDD
          </label>
          <input id="telefone" value={v.telefone} onChange={set("telefone")} inputMode="tel" maxLength={15} className={campo} />
        </div>
        <div>
          <label htmlFor="ocupacao" className="label">
            Ocupação
          </label>
          <input id="ocupacao" value={v.ocupacao} onChange={set("ocupacao")} maxLength={120} className={campo} />
        </div>
        <div className="grid grid-cols-[1fr_5rem] gap-3 sm:col-span-2">
          <div>
            <label htmlFor="cidade" className="label">
              Cidade
            </label>
            <input id="cidade" value={v.cidade} onChange={set("cidade")} maxLength={80} className={campo} />
          </div>
          <div>
            <label htmlFor="uf" className="label">
              UF
            </label>
            <input id="uf" value={v.uf} onChange={set("uf")} maxLength={2} className={campo} />
          </div>
        </div>
      </div>

      {mudouTelefone && cliente.consentimento_ativo && (
        <p className="mt-5 border border-dashed border-ink p-4 text-sm">
          Trocar o celular muda a linha analisada. Por isso o seu consentimento atual será revogado, o score
          guardado apagado e, se houver, o pedido enviado ao banco será retirado. Você autoriza de novo na etapa
          seguinte.
        </p>
      )}
      {error && (
        <div className="mt-6">
          <ErrorBox message={error} />
        </div>
      )}

      <button onClick={continuar} disabled={busy} className={`${btnPrimary} mt-8 w-full sm:w-auto`}>
        {busy ? "Salvando…" : mudou ? "Salvar e continuar" : "Está tudo certo, continuar"} <Arrow />
      </button>
    </section>
  );
}

// --- 2 · Consentimento ------------------------------------------------------------------

function ConsentStep({
  consent,
  setConsent,
  modelo,
  onBack,
  onAutorizado,
  onExpirou,
}: {
  consent: Record<Escopo, boolean>;
  setConsent: (c: Record<Escopo, boolean>) => void;
  modelo: CartaoModelo | null;
  onBack: () => void;
  onAutorizado: (c: Cliente) => void;
  onExpirou: () => void;
}) {
  const [read, setRead] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loss = (key: Escopo) => modelo?.fatores.find((f) => f.chave === key)?.perda_maxima_se_omitir;

  async function autorizar() {
    setBusy(true);
    setError(null);
    try {
      const escopos = (Object.keys(consent) as Escopo[]).filter((k) => consent[k]);
      await api.consentir(escopos);
      onAutorizado(await api.eu());
    } catch (e) {
      if (sessaoExpirada(e)) return onExpirou();
      setError(mensagemDeErro(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="feed">
      <h1 className="display text-4xl sm:text-5xl">O que você autoriza.</h1>
      <p className="mt-5 text-ink-2 leading-relaxed">
        Finalidade única: calcular o seu score. Válido por 30 dias e revogável a qualquer momento. Os três
        primeiros itens são necessários. Os outros são opcionais, mas quem não autoriza entra com o pior valor
        naquele fator: esconder dados nunca aumenta o score.
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

      <AvisoRemuneracao className="mt-6" />

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
          Li e autorizo a ScoreLyne a ler os dados acima na operadora para calcular o meu score, nos termos da
          LGPD. O banco só recebe algo se eu decidir enviar um pedido, com um consentimento separado.
        </span>
      </label>

      {error && (
        <div className="mt-6">
          <ErrorBox message={error} />
        </div>
      )}

      <div className="mt-8 flex gap-3">
        <button onClick={onBack} className={btnSecondary}>
          Voltar
        </button>
        <button onClick={autorizar} disabled={!read || busy} className={`${btnPrimary} flex-1 sm:flex-none`}>
          {busy ? "Autorizando…" : "Autorizar"} <Arrow />
        </button>
      </div>
    </section>
  );
}

// --- 3 · Pedido e análise ---------------------------------------------------------------

type Pedido = { valor_solicitado: number; finalidade: string };

function PedidoStep({
  padrao,
  onConfirmar,
  onBack,
}: {
  padrao?: MeuScore;
  onConfirmar: (p: Pedido) => void;
  onBack: () => void;
}) {
  const [valor, setValor] = useState(String(padrao?.valor_solicitado ?? 1000));
  const [finalidade, setFinalidade] = useState(padrao?.finalidade ?? "Capital de giro");
  const numero = Number(valor.replace(",", "."));
  const valido = numero > 0 && numero <= 50000 && finalidade.trim().length >= 2;

  return (
    <section className="feed">
      <h1 className="display text-4xl sm:text-5xl">Quanto você precisa?</h1>
      <p className="mt-5 text-ink-2 text-lg leading-relaxed">
        Diga o valor e para quê. Ainda não é um pedido ao banco: primeiro você vê o seu score e a oferta
        prevista, e só envia se quiser.
      </p>
      <div className="mt-8 grid sm:grid-cols-2 gap-x-5 gap-y-5">
        <div>
          <label htmlFor="valor" className="label">
            Valor desejado (R$)
          </label>
          <input id="valor" value={valor} onChange={(e) => setValor(e.target.value)} inputMode="decimal" className={`${campo} num`} />
          <p className="mt-1 text-xs text-ink-2">Entre R$ 1 e R$ 50.000.</p>
        </div>
        <div>
          <label htmlFor="finalidade" className="label">
            Para quê
          </label>
          <input id="finalidade" value={finalidade} onChange={(e) => setFinalidade(e.target.value)} maxLength={200} className={campo} />
        </div>
      </div>
      <div className="mt-8 flex gap-3">
        <button onClick={onBack} className={btnSecondary}>
          Voltar
        </button>
        <button
          onClick={() => onConfirmar({ valor_solicitado: numero, finalidade: finalidade.trim() })}
          disabled={!valido}
          className={`${btnPrimary} flex-1 sm:flex-none`}
        >
          Calcular meu score <Arrow />
        </button>
      </div>
    </section>
  );
}

function AnaliseStep({
  pedido,
  onDone,
  onBack,
  onExpirou,
}: {
  pedido: Pedido;
  onDone: (s: MeuScore) => void;
  onBack: () => void;
  onExpirou: () => void;
}) {
  const [done, setDone] = useState(0);
  const [result, setResult] = useState<MeuScore | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Guarda a requisição para o StrictMode (que roda o efeito duas vezes) não calcular duas vezes.
  const request = useRef<Promise<MeuScore> | null>(null);

  useEffect(() => {
    request.current ??= api.calcular(pedido);
    let alive = true;
    request.current.then(
      (s) => alive && setResult(s),
      (e) => {
        if (!alive) return;
        if (sessaoExpirada(e)) return onExpirou();
        setError(mensagemDeErro(e));
      },
    );
    return () => {
      alive = false;
    };
  }, [pedido, onExpirou]);

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
            Voltar ao pedido
          </button>
        </div>
      )}
    </section>
  );
}

// --- 4 · Resultado, assistente e pedido ao banco ---------------------------------------

function ResultadoStep({
  cliente,
  score,
  situacao,
  onCliente,
  onSituacao,
  onEditarDados,
  onRecalcular,
  onRevogado,
  onExpirou,
}: {
  cliente: Cliente;
  score: MeuScore;
  situacao: SituacaoSolicitacao | null;
  onCliente: (c: Cliente) => void;
  onSituacao: (s: SituacaoSolicitacao | null) => void;
  onEditarDados: () => void;
  onRecalcular: () => void;
  onRevogado: (c: Cliente) => void;
  onExpirou: () => void;
}) {
  const [term, setTerm] = useState(12);
  const [error, setError] = useState<string | null>(null);
  const [acao, setAcao] = useState<"enviar" | "retirar" | "revogar" | null>(null);

  // `ativa` só existe se o pedido foi enviado e já temos a situação dele.
  const ativa = cliente.enviado_ao_credor ? situacao : null;
  const enviado = ativa !== null;
  const status = ativa?.status ?? null;

  // Pedido enviado mas situação ainda não carregada (ex.: a tela abriu com o credor fora do ar).
  useEffect(() => {
    if (cliente.enviado_ao_credor && !situacao) {
      api.minhaSolicitacao().then(onSituacao).catch(() => {});
    }
  }, [cliente.enviado_ao_credor, situacao, onSituacao]);

  // Enquanto estiver com um analista, acompanha a decisão em tempo real.
  useEffect(() => {
    if (status !== "revisao") return;
    const t = setInterval(() => {
      api.minhaSolicitacao().then(onSituacao).catch(() => {});
    }, 4000);
    return () => clearInterval(t);
  }, [status, onSituacao]);

  async function rodar(qual: NonNullable<typeof acao>, fn: () => Promise<void>) {
    setAcao(qual);
    setError(null);
    try {
      await fn();
    } catch (e) {
      if (sessaoExpirada(e)) return onExpirou();
      setError(mensagemDeErro(e));
    } finally {
      setAcao(null);
    }
  }

  const enviar = () =>
    rodar("enviar", async () => {
      onCliente(await api.enviarAoCredor());
      onSituacao(await api.minhaSolicitacao());
    });
  const retirar = () =>
    rodar("retirar", async () => {
      onCliente(await api.retirarDoCredor());
      onSituacao(null);
    });
  const revogar = () => rodar("revogar", async () => onRevogado(await api.revogar()));

  const a = score.analise;
  const first = cliente.nome.split(" ")[0];
  const offer = ativa ? ativa.oferta : a.oferta;
  const parcela = offer?.parcelas.find((p) => p.prazo_meses === term) ?? offer?.parcelas[0];
  const skipped = a.fatores.filter((f) => f.status === "nao_autorizado").length;
  const review = ativa?.revisao_humana ?? null;
  const decisaoAgente = a.decisao;

  return (
    <section className="feed">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="label text-ink-2">{enviado ? "Seu pedido ao banco" : "Seu score"} · {cliente.nome}</p>
        <DecisionBadge decision={status ?? decisaoAgente} />
      </div>

      <h1 className="display text-3xl sm:text-4xl mt-5">
        {!enviado && `${first}, seu score é ${a.score}.`}
        {status === "aprovado" && (review ? `${first}, um analista aprovou seu crédito.` : `${first}, seu crédito foi pré-aprovado.`)}
        {status === "revisao" && "Seu pedido está com um analista."}
        {status === "recusado" && "Ainda não deu desta vez."}
        {status === "revogado" && "Pedido retirado."}
      </h1>
      <p className="mt-3 text-ink-2 leading-relaxed">
        {!enviado && (
          <>
            Se você enviar o pedido agora, {FRASE_DECISAO[decisaoAgente]}.{" "}
            {decisaoAgente === "recusado" ? "Veja abaixo o plano para chegar lá. " : ""}
            Isto ainda é uma prévia: nada foi enviado ao banco.
          </>
        )}
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

      {(status === "revisao" || (!enviado && decisaoAgente === "revisao")) && a.motivos_revisao.length > 0 && (
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

      {(status ?? decisaoAgente) !== "recusado" && offer && parcela && (
        <div className="mt-4 border border-ink">
          <div className="px-5 py-3 border-b border-ink bg-tint flex justify-between gap-3">
            <h2 className="font-bold">
              {status === "aprovado" ? "Sua oferta" : enviado ? "Oferta prevista, sujeita à revisão" : "Oferta prevista"}
            </h2>
            {offer.valor_ofertado < score.valor_solicitado && (
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

      {enviado && status === "aprovado" && !offer && (
        <p className="mt-4 border border-ink p-4 text-sm">
          Seu score ficou abaixo da faixa de oferta automática, então o banco vai enviar o valor e as condições
          aprovadas pelo analista.
        </p>
      )}

      {(status ?? decisaoAgente) === "recusado" && a.plano_de_melhora.length > 0 && (
        <div className="mt-6 border border-ink">
          <h2 className="px-5 py-3 border-b border-ink bg-lime font-bold">Seu plano para chegar lá</h2>
          <ol className="p-5 space-y-2 text-sm list-decimal list-inside">
            {a.plano_de_melhora.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ol>
        </div>
      )}

      {!enviado && (
        <div className="mt-8 border-2 border-ink p-5">
          <h2 className="font-bold text-lg">Quer pedir esse crédito ao banco?</h2>
          <p className="mt-2 text-sm text-ink-2 leading-relaxed">
            Você dá ao Banco Parceiro S.A. um consentimento só dele, com os mesmos dados que já autorizou, e o
            pedido de {brl(score.valor_solicitado)} vai para a fila. Você acompanha a decisão aqui e pode
            retirar o pedido quando quiser.
          </p>
          <AvisoRemuneracao className="mt-4" />
          <button onClick={enviar} disabled={acao !== null} className={`${btnPrimary} mt-4 w-full sm:w-auto`}>
            {acao === "enviar" ? "Enviando…" : "Enviar pedido ao banco"} <Arrow />
          </button>
        </div>
      )}

      <div className="mt-10">
        <h2 className="display text-2xl">Por que esse score.</h2>
        <p className="mt-2 text-sm text-ink-2">
          Cada fator vai de 0 a 100. Os pontos mostram quanto ele soma ou tira em relação a um cliente médio, com
          a mesma régua para todas as pessoas.
          {skipped > 0 &&
            ` ${skipped} ${skipped === 1 ? "fator não autorizado entrou" : "fatores não autorizados entraram"} com o pior valor possível.`}{" "}
          <Link href="/cliente/como-e-calculado#formulas" className="font-semibold underline hover:no-underline">
            Ver as fórmulas
          </Link>
          .
        </p>
        <div className="mt-4 border-t-2 border-ink">
          <BaseLine base={a.pontos_base} />
          <FactorLines factors={a.fatores} showTips={(status ?? decisaoAgente) !== "recusado"} />
        </div>
        <p className="mt-3 label text-ink-2">
          Modelo {a.modelo_versao} · fórmulas v{a.formulas_versao}
        </p>
      </div>

      <div className="mt-10">
        <AssistenteScore />
      </div>

      {error && (
        <div className="mt-6">
          <ErrorBox message={error} />
        </div>
      )}

      <div className="mt-10 -mx-5 sm:-mx-10 -mb-5 sm:-mb-10">
        <div className="perf text-ink" aria-hidden="true" />
        <div className="px-5 sm:px-10 py-5 bg-tint flex flex-wrap items-center gap-3">
          {enviado ? (
            <button onClick={retirar} disabled={acao !== null} className={`${btnSecondary} bg-paper`}>
              {acao === "retirar" ? "Retirando…" : "Retirar pedido do banco"}
            </button>
          ) : (
            <>
              <button onClick={onEditarDados} className={`${btnSecondary} bg-paper`}>
                Corrigir meus dados
              </button>
              <button onClick={onRecalcular} className={`${btnSecondary} bg-paper`}>
                Pedir outro valor
              </button>
            </>
          )}
          <button
            onClick={revogar}
            disabled={acao !== null}
            className="px-5 py-3.5 font-semibold text-red-ink underline hover:no-underline disabled:opacity-50"
          >
            {acao === "revogar" ? "Revogando…" : "Revogar consentimento"}
          </button>
          <Barcode value={ativa?.id ?? cliente.id} className="hidden sm:block ml-auto h-9 w-28" />
        </div>
        {enviado && (
          <p className="px-5 sm:px-10 pb-5 bg-tint text-xs text-ink-2">
            Para corrigir dados ou pedir outro valor, retire o pedido do banco primeiro: o banco só analisa o que
            você enviou.
          </p>
        )}
      </div>
    </section>
  );
}
