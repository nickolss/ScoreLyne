import type { Metadata } from "next";
import { Governanca } from "@/components/governanca";

export const metadata: Metadata = { title: "Como é calculado" };

export const dynamic = "force-dynamic";

export default function ComoECalculadoPage() {
  return <Governanca origem="consumidor" />;
}
