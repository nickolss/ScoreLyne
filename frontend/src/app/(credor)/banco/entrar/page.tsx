import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { entrarCredor } from "@/app/acoes";
import { FormularioAcao } from "@/components/form-login";
import { tokenDe } from "@/lib/api-servidor";

export const metadata: Metadata = { title: "Entrar como operador de crédito" };

export default async function EntrarCredorPage() {
  if (await tokenDe("credor")) redirect("/banco");

  return (
    <div className="bg-tint min-h-full">
      <div className="mx-auto max-w-xl px-4 sm:px-8 py-10 sm:py-14">
        <div className="bg-paper border border-ink p-5 sm:p-10">
          <p className="label text-ink-2">Persona · Operador de crédito</p>
          <h1 className="display text-4xl sm:text-5xl mt-3">Entrar no painel.</h1>
          <p className="mt-4 text-ink-2 leading-relaxed">
            Acesso do analista de crédito. Aqui você valida as análises do agente, decide os casos
            intermediários e conversa com o copiloto.
          </p>
          <FormularioAcao
            action={entrarCredor}
            enviar="Entrar"
            pendente="Entrando…"
            campos={[
              { name: "email", label: "E-mail", type: "email", autoComplete: "username", required: true },
              { name: "senha", label: "Senha", type: "password", autoComplete: "current-password", required: true },
            ]}
          />
          <p className="mt-6 text-sm text-ink-2">
            Na demonstração, o analista vem do comando <code className="num bg-tint px-1">uv run banco semear</code>
            , que mostra o e-mail e a senha de teste.
          </p>
          <p className="mt-4 text-sm">
            Quer pedir crédito?{" "}
            <Link href="/cliente" className="font-semibold underline hover:no-underline">
              Entre como consumidor
            </Link>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
