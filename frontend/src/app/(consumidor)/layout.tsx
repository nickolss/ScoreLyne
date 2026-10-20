import { sair } from "@/app/acoes";
import { Rodape, SiteHeader } from "@/components/site-header";
import { tokenDe } from "@/lib/api-servidor";

// Módulo do consumidor: só fala com a API do consumidor (porta 8003).
export default async function ConsumidorLayout({ children }: LayoutProps<"/">) {
  const logado = Boolean(await tokenDe("consumidor"));
  return (
    <>
      <SiteHeader persona="consumidor" onSair={logado ? sair.bind(null, "consumidor") : undefined} />
      <main className="flex-1">{children}</main>
      <Rodape />
    </>
  );
}
