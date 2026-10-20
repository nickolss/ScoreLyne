"use client";

import { useActionState } from "react";
import type { EstadoForm } from "@/app/acoes";
import { btnPrimary, campo } from "./ui";

export type Campo = {
  name: string;
  label: string;
  type?: string;
  autoComplete?: string;
  inputMode?: "numeric" | "text" | "tel" | "email";
  placeholder?: string;
  required?: boolean;
  maxLength?: number;
  defaultValue?: string;
};

export type AcaoForm = (estado: EstadoForm, dados: FormData) => Promise<EstadoForm>;

export function CaixaDeErro({ mensagem }: { mensagem: string }) {
  return (
    <div className="mt-6 border-2 border-red p-4" role="alert">
      <p className="font-semibold text-red-ink">Não foi possível continuar</p>
      <p className="mt-1 text-sm">{mensagem}</p>
    </div>
  );
}

// Formulário ligado a uma Server Action. O erro volta como estado, sem recarregar a página.
export function FormularioAcao({
  action,
  campos,
  enviar,
  pendente = "Enviando…",
}: {
  action: AcaoForm;
  campos: Campo[];
  enviar: string;
  pendente?: string;
}) {
  const [estado, formAction, enviando] = useActionState(action, {});

  return (
    <form action={formAction} className="mt-8">
      <div className="space-y-5">
        {campos.map((c) => (
          <div key={c.name}>
            <label htmlFor={c.name} className="label">
              {c.label}
            </label>
            <input
              id={c.name}
              name={c.name}
              type={c.type ?? "text"}
              autoComplete={c.autoComplete}
              inputMode={c.inputMode}
              placeholder={c.placeholder}
              required={c.required}
              maxLength={c.maxLength}
              defaultValue={c.defaultValue}
              className={campo}
            />
          </div>
        ))}
      </div>

      {estado.erro && <CaixaDeErro mensagem={estado.erro} />}

      <button type="submit" disabled={enviando} className={`${btnPrimary} mt-8 w-full sm:w-auto`}>
        {enviando ? pendente : enviar}
      </button>
    </form>
  );
}
