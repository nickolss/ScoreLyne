import { Rodape, SiteHeader } from "@/components/site-header";

export default function PublicoLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <SiteHeader persona="publico" />
      <main className="flex-1">{children}</main>
      <Rodape />
    </>
  );
}
