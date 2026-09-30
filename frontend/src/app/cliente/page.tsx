import type { Metadata } from "next";
import { Journey } from "./journey";

export const metadata: Metadata = { title: "Simular meu score" };

export default function ClientePage() {
  return (
    <div className="bg-tint min-h-full">
      <div className="mx-auto max-w-3xl px-4 sm:px-8 py-10 sm:py-14">
        <Journey />
      </div>
    </div>
  );
}
