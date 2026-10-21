import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { BackendDown } from "@/components/backend-down";
import { ApiError } from "@/lib/api";
import { consumidorLogado } from "@/lib/api-servidor";
import { Jornada } from "./jornada";

export const metadata: Metadata = { title: "Meu score" };

// Depende de quem está logado: renderiza sempre no momento da requisição.
export const dynamic = "force-dynamic";

export default async function ClientePage() {
  const api = await consumidorLogado();
  if (!api) redirect("/cliente/entrar");

  let dados;
  try {
    const [cliente, modelo] = await Promise.all([api.eu(), api.modelo().catch(() => null)]);
    // Ainda não calculou: 404 é o estado normal de quem acabou de se cadastrar.
    const score = await api.meuScore().catch((e) => {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    });
    // O pedido ao credor é opcional na tela: se o credor estiver fora do ar, o resto segue.
    const situacao = cliente.enviado_ao_credor ? await api.minhaSolicitacao().catch(() => null) : null;
    dados = { cliente, score, situacao, modelo };
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect("/cliente/entrar");
    return <BackendDown service="consumidor" message={e instanceof ApiError ? e.message : "Erro ao carregar seus dados."} />;
  }

  return (
    <div className="bg-tint min-h-full">
      <div className="mx-auto max-w-3xl px-4 sm:px-8 py-10 sm:py-14">
        <Jornada
          clienteInicial={dados.cliente}
          scoreInicial={dados.score}
          situacaoInicial={dados.situacao}
          modelo={dados.modelo}
        />
      </div>
    </div>
  );
}
