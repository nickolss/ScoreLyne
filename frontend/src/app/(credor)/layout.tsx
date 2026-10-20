import { sair } from "@/app/acoes";
import { Rodape, SiteHeader } from "@/components/site-header";
import { tokenDe } from "@/lib/api-servidor";

// Módulo do operador de crédito: só fala com a API do credor (porta 8002), com login de analista.
export default async function CredorLayout({ children }: LayoutProps<"/">) {
  const logado = Boolean(await tokenDe("credor"));
  return (
    <>
      <SiteHeader persona="credor" onSair={logado ? sair.bind(null, "credor") : undefined} />
      <main className="flex-1">{children}</main>
      <Rodape />
    </>
  );
}
