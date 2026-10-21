import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { trocarSenhaCredor } from "@/app/acoes";
import { BackendDown } from "@/components/backend-down";
import { FormularioAcao } from "@/components/form-login";
import { ApiError } from "@/lib/api";
import { credorLogado } from "@/lib/api-servidor";

export const metadata: Metadata = { title: "Perfil do analista" };

export const dynamic = "force-dynamic";

export default async function PerfilAnalistaPage() {
  const api = await credorLogado();
  if (!api) redirect("/banco/entrar");

  let analista;
  try {
    analista = await api.eu();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/banco/entrar");
    return <BackendDown service="credor" message={e instanceof ApiError ? e.message : "Erro ao carregar o perfil."} />;
  }

  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-12 pb-10">
          <p className="num text-sm text-on-cobalt-2">Persona · Operador de crédito</p>
          <h1 className="display text-5xl sm:text-6xl mt-3">Perfil.</h1>
        </div>
      </section>

      <div className="bg-tint">
        <div className="mx-auto max-w-3xl px-4 sm:px-8 py-10 space-y-6">
          <section className="border border-ink bg-paper p-5 sm:p-8" aria-labelledby="a-dados">
            <h2 id="a-dados" className="display text-3xl">
              Sua conta.
            </h2>
            <dl className="mt-5 grid sm:grid-cols-2 border-t-2 border-ink">
              <div className="py-3 sm:pr-4 sm:border-r border-rule border-b">
                <dt className="label text-ink-2">Nome</dt>
                <dd className="mt-1">{analista.nome}</dd>
              </div>
              <div className="py-3 sm:pl-4 border-b border-rule">
                <dt className="label text-ink-2">E-mail</dt>
                <dd className="mt-1">{analista.email}</dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-ink-2">
              Seu nome é o que fica registrado na trilha de auditoria em cada decisão.
            </p>
          </section>

          <section className="border border-ink bg-paper p-5 sm:p-8" aria-labelledby="a-senha">
            <h2 id="a-senha" className="display text-3xl">
              Senha.
            </h2>
            <FormularioAcao
              action={trocarSenhaCredor}
              enviar="Alterar senha"
              pendente="Alterando…"
              campos={[
                { name: "senha_atual", label: "Senha atual", type: "password", autoComplete: "current-password", required: true },
                { name: "nova_senha", label: "Nova senha (mín. 8)", type: "password", autoComplete: "new-password", required: true, maxLength: 72 },
                { name: "confirmacao", label: "Repita a nova senha", type: "password", autoComplete: "new-password", required: true, maxLength: 72 },
              ]}
            />
          </section>
        </div>
      </div>
    </>
  );
}
