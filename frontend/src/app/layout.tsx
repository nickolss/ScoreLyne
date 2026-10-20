import type { Metadata } from "next";
import { Archivo, Martian_Mono } from "next/font/google";
import "./globals.css";

const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  axes: ["wdth"],
});

const martian = Martian_Mono({
  variable: "--font-martian",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: "ScoreLyne", template: "%s · ScoreLyne" },
  description:
    "Credit scoring alternativo baseado em padrões de uso de telecomunicações.",
};

// O cabeçalho e o rodapé ficam nos layouts de cada módulo: (publico), (consumidor) e (credor).
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${archivo.variable} ${martian.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
