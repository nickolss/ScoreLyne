"use client";

import { useActionState, useState } from "react";
import { type EstadoForm, cadastrarConsumidor, entrarConsumidor } from "@/app/acoes";
import type { PersonaDemo } from "@/lib/api";
import { CaixaDeErro } from "./form-login";
import { btnPrimary, campo } from "./ui";

// Senha só da demonstração: é a que `uv run consumidor semear` grava nas pessoas de teste.
export const SENHA_DEMO = "scorelyne123";

const fmtCpf = (c: string) => c.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, "$1.$2.$3-$4");
const fmtTel = (t: string) => t.replace(/^(\d{2})(\d{4,5})(\d{4})$/, "($1) $2-$3");

function EscolhaDeDemo({
  personas,
  escolhida,
  onEscolher,
  titulo,
}: {
  personas: PersonaDemo[];
  escolhida: string | null;
  onEscolher: (p: PersonaDemo) => void;
  titulo: string;
}) {
  if (!personas.length) return null;
  return (
    <fieldset className="mt-8 border border-dashed border-ink p-4">
      <legend className="label px-2">{titulo}</legend>
      <p className="text-sm text-ink-2">
        Dados de teste da operadora simulada. Só quem existe nela tem histórico para calcular o score.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {personas.map((p) => (
          <button
            key={p.cpf}
            type="button"
            onClick={() => onEscolher(p)}
            aria-pressed={escolhida === p.cpf}
            className={`border border-ink px-3 py-1.5 text-sm text-left ${escolhida === p.cpf ? "bg-ink text-paper" : "hover:bg-lime"}`}
          >
            {p.titular.split(" ")[0]}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function Campo({
  name,
  label,
  value,
  onChange,
  ...resto
}: {
  name: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  autoComplete?: string;
  inputMode?: "numeric" | "text" | "tel";
  required?: boolean;
  maxLength?: number;
  minLength?: number;
}) {
  return (
    <div>
      <label htmlFor={name} className="label">
        {label}
      </label>
      <input
        id={name}
        name={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={campo}
        {...resto}
      />
    </div>
  );
}

export function EntrarConsumidorForm({ personas }: { personas: PersonaDemo[] }) {
  const [estado, action, enviando] = useActionState<EstadoForm, FormData>(entrarConsumidor, {});
  const [cpf, setCpf] = useState("");
  const [senha, setSenha] = useState("");

  return (
    <form action={action}>
      <EscolhaDeDemo
        personas={personas}
        escolhida={cpf.replace(/\D/g, "")}
        titulo="Entrar como pessoa de demonstração"
        onEscolher={(p) => {
          setCpf(fmtCpf(p.cpf));
          setSenha(SENHA_DEMO);
        }}
      />
      <div className="mt-8 space-y-5">
        <Campo name="cpf" label="CPF" value={cpf} onChange={setCpf} inputMode="numeric" autoComplete="username" required maxLength={14} />
        <Campo name="senha" label="Senha" value={senha} onChange={setSenha} type="password" autoComplete="current-password" required />
      </div>
      {estado.erro && <CaixaDeErro mensagem={estado.erro} />}
      <button type="submit" disabled={enviando} className={`${btnPrimary} mt-8 w-full sm:w-auto`}>
        {enviando ? "Entrando…" : "Entrar"}
      </button>
    </form>
  );
}

export function CadastroConsumidorForm({ personas }: { personas: PersonaDemo[] }) {
  const [estado, action, enviando] = useActionState<EstadoForm, FormData>(cadastrarConsumidor, {});
  const [v, setV] = useState({ nome: "", cpf: "", telefone: "", ocupacao: "", cidade: "", uf: "", senha: "", confirmacao: "" });
  const set = (k: keyof typeof v) => (valor: string) => setV((a) => ({ ...a, [k]: valor }));

  return (
    <form action={action}>
      <EscolhaDeDemo
        personas={personas}
        escolhida={v.cpf.replace(/\D/g, "")}
        titulo="Preencher com uma pessoa de demonstração"
        onEscolher={(p) =>
          setV((a) => ({ ...a, nome: p.titular, cpf: fmtCpf(p.cpf), telefone: fmtTel(p.telefone), cidade: p.cidade, uf: p.uf }))
        }
      />
      <div className="mt-8 grid sm:grid-cols-2 gap-x-5 gap-y-5">
        <div className="sm:col-span-2">
          <Campo name="nome" label="Nome completo" value={v.nome} onChange={set("nome")} autoComplete="name" required maxLength={120} />
        </div>
        <Campo name="cpf" label="CPF" value={v.cpf} onChange={set("cpf")} inputMode="numeric" required maxLength={14} />
        <Campo name="telefone" label="Celular com DDD" value={v.telefone} onChange={set("telefone")} inputMode="tel" autoComplete="tel" required maxLength={15} />
        <Campo name="ocupacao" label="Ocupação (opcional)" value={v.ocupacao} onChange={set("ocupacao")} maxLength={120} />
        <div className="grid grid-cols-[1fr_5rem] gap-3">
          <Campo name="cidade" label="Cidade (opcional)" value={v.cidade} onChange={set("cidade")} maxLength={80} />
          <Campo name="uf" label="UF" value={v.uf} onChange={(x) => set("uf")(x.toUpperCase())} maxLength={2} />
        </div>
        <Campo name="senha" label="Senha (mín. 8)" value={v.senha} onChange={set("senha")} type="password" autoComplete="new-password" required minLength={8} maxLength={72} />
        <Campo name="confirmacao" label="Repita a senha" value={v.confirmacao} onChange={set("confirmacao")} type="password" autoComplete="new-password" required minLength={8} maxLength={72} />
      </div>
      {estado.erro && <CaixaDeErro mensagem={estado.erro} />}
      <button type="submit" disabled={enviando} className={`${btnPrimary} mt-8 w-full sm:w-auto`}>
        {enviando ? "Criando conta…" : "Criar conta"}
      </button>
    </form>
  );
}
