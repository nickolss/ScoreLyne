import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { EntrarConsumidorForm } from "@/components/auth-consumidor";
import { operadoraPublica, tokenDe } from "@/lib/api-servidor";

export const metadata: Metadata = { title: "Entrar" };

export default async function EntrarConsumidorPage() {
  if (await tokenDe("consumidor")) redirect("/cliente");
  // A lista de pessoas de teste é só um atalho: se a operadora estiver fora do ar, o login segue normal.
  const personas = await operadoraPublica.personas().catch(() => []);

  return (
    <div className="bg-tint min-h-full">
      <div className="mx-auto max-w-xl px-4 sm:px-8 py-10 sm:py-14">
        <div className="bg-paper border border-ink p-5 sm:p-10">
          <p className="label text-ink-2">Persona · Consumidor</p>
          <h1 className="display text-4xl sm:text-5xl mt-3">Entrar.</h1>
          <p className="mt-4 text-ink-2 leading-relaxed">
            Veja o seu score, entenda por que ele ficou assim e peça crédito quando quiser.
          </p>
          <EntrarConsumidorForm personas={personas} />
          <p className="mt-8 text-sm">
            Ainda não tem conta?{" "}
            <Link href="/cliente/cadastro" className="font-semibold underline hover:no-underline">
              Criar conta
            </Link>
            . É operador de crédito?{" "}
            <Link href="/banco/entrar" className="font-semibold underline hover:no-underline">
              Entre no painel
            </Link>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
