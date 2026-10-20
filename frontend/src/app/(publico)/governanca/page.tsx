import type { Metadata } from "next";
import { Governanca } from "@/components/governanca";

export const metadata: Metadata = { title: "Governança" };

// Pesos, métricas, equidade e fórmulas vêm do que está em produção: renderiza no momento da requisição.
export const dynamic = "force-dynamic";

export default function GovernancaPage() {
  return <Governanca />;
}
