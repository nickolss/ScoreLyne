import type { Metadata } from "next";
import { Archivo, Martian_Mono } from "next/font/google";
import { Logo, SiteHeader } from "@/components/site-header";
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

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${archivo.variable} ${martian.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans">
        <SiteHeader />
        <main className="flex-1">{children}</main>
        <footer className="border-t border-ink">
          <div className="mx-auto max-w-7xl px-4 sm:px-8 py-8 flex flex-col sm:flex-row gap-4 sm:items-center justify-between">
            <Logo />
            <p className="label text-ink-2">Credit scoring a partir do seu histórico telecom</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
