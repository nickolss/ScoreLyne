import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { CadastroConsumidorForm } from "@/components/auth-consumidor";
import { operadoraPublica, tokenDe } from "@/lib/api-servidor";

export const metadata: Metadata = { title: "Criar conta" };

export default async function CadastroConsumidorPage() {
  if (await tokenDe("consumidor")) redirect("/cliente");
  const personas = await operadoraPublica.personas().catch(() => []);

  return (
    <div className="bg-tint min-h-full">
      <div className="mx-auto max-w-2xl px-4 sm:px-8 py-10 sm:py-14">
        <div className="bg-paper border border-ink p-5 sm:p-10">
          <p className="label text-ink-2">Persona · Consumidor</p>
          <h1 className="display text-4xl sm:text-5xl mt-3">Criar conta.</h1>
          <p className="mt-4 text-ink-2 leading-relaxed">
            Seu cadastro fica só neste módulo. O banco só recebe algo seu se você decidir enviar um pedido, e
            com um consentimento próprio.
          </p>
          <CadastroConsumidorForm personas={personas} />
          <p className="mt-8 text-sm">
            Já tem conta?{" "}
            <Link href="/cliente/entrar" className="font-semibold underline hover:no-underline">
              Entrar
            </Link>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
