import type { Metadata } from "next";
import { Governanca } from "@/components/governanca";

export const metadata: Metadata = { title: "Governança" };

export const dynamic = "force-dynamic";

export default function GovernancaDoCredorPage() {
  return <Governanca />;
}
