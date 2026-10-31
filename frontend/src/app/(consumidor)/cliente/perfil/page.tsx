import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { trocarSenhaConsumidor } from "@/app/acoes";
import { BackendDown } from "@/components/backend-down";
import { FormularioAcao } from "@/components/form-login";
import { DadosForm, ExcluirContaForm } from "@/components/perfil-forms";
import { ApiError } from "@/lib/api";
import { consumidorLogado } from "@/lib/api-servidor";
import { maskCpf } from "@/lib/data";

export const metadata: Metadata = { title: "Perfil" };

export const dynamic = "force-dynamic";

export default async function PerfilPage() {
  const api = await consumidorLogado();
  if (!api) redirect("/cliente/entrar");

  let cliente;
  try {
    cliente = await api.eu();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/cliente/entrar");
    return <BackendDown service="consumidor" message={e instanceof ApiError ? e.message : "Erro ao carregar o seu perfil."} />;
  }

  return (
    <>
      <section className="on-cobalt bg-cobalt text-on-cobalt border-b border-ink">
        <div className="mx-auto max-w-7xl px-4 sm:px-8 pt-12 pb-10">
          <p className="num text-sm text-on-cobalt-2">Persona · Consumidor</p>
          <h1 className="display text-5xl sm:text-6xl mt-3">Perfil.</h1>
          <p className="mt-5 text-on-cobalt-2 max-w-2xl leading-relaxed">
            Seus dados de cadastro, sua senha e o direito de apagar tudo.
          </p>
        </div>
      </section>

      <div className="bg-tint">
        <div className="mx-auto max-w-3xl px-4 sm:px-8 py-10 space-y-6">
          <section className="border border-ink bg-paper p-5 sm:p-8" aria-labelledby="p-dados">
            <h2 id="p-dados" className="display text-3xl">
              Seus dados.
            </h2>
            <dl className="mt-5 grid sm:grid-cols-2 border-t-2 border-ink">
              <div className="py-3 sm:pr-4 sm:border-r border-rule border-b">
                <dt className="label text-ink-2">Nome</dt>
                <dd className="mt-1">{cliente.nome}</dd>
              </div>
              <div className="py-3 sm:pl-4 border-b border-rule">
                <dt className="label text-ink-2">CPF</dt>
                <dd className="num mt-1">{maskCpf(cliente.cpf)}</dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-ink-2">Nome e CPF não mudam aqui: eles identificam a linha na operadora.</p>
            <DadosForm cliente={cliente} />
          </section>

          <section className="border border-ink bg-paper p-5 sm:p-8" aria-labelledby="p-senha">
            <h2 id="p-senha" className="display text-3xl">
              Senha.
            </h2>
            <FormularioAcao
              action={trocarSenhaConsumidor}
              enviar="Alterar senha"
              pendente="Alterando…"
              campos={[
                { name: "senha_atual", label: "Senha atual", type: "password", autoComplete: "current-password", required: true },
                { name: "nova_senha", label: "Nova senha (mín. 8)", type: "password", autoComplete: "new-password", required: true, maxLength: 72 },
                { name: "confirmacao", label: "Repita a nova senha", type: "password", autoComplete: "new-password", required: true, maxLength: 72 },
              ]}
            />
          </section>

          <section className="border-2 border-red bg-paper p-5 sm:p-8" aria-labelledby="p-excluir">
            <h2 id="p-excluir" className="display text-3xl">
              Excluir minha conta.
            </h2>
            <p className="mt-3 text-sm text-ink-2 leading-relaxed max-w-[60ch]">
              Revoga todos os acessos aos seus dados, na ScoreLyne e no banco, e apaga o seu cadastro, o score e o
              histórico de pedidos. Se o banco estiver fora do ar, o acesso dele é bloqueado na operadora na hora e a
              análise que ele guardava é apagada quando ele voltar.
            </p>
            <ExcluirContaForm />
          </section>
        </div>
      </div>
    </>
  );
}
