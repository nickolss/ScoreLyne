"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export type Persona = "publico" | "consumidor" | "credor";

type Item = { href: string; label: string };

// Cada módulo tem o próprio menu e deixa à vista quem está usando: Consumidor ou Operador de crédito.
// O menu muda conforme a pessoa esteja logada ou não.
type Menu = { casa: string; rotulo: string | null; itens: Item[] };

function menuDe(persona: Persona, logado: boolean): Menu {
  if (persona === "consumidor") {
    return {
      casa: "/cliente",
      rotulo: "Consumidor",
      itens: logado
        ? [
            { href: "/cliente", label: "Início" },
            { href: "/cliente/score", label: "Meu score" },
            { href: "/cliente/consentimentos", label: "Consentimentos" },
            { href: "/cliente/pedidos", label: "Pedidos" },
            { href: "/cliente/perfil", label: "Perfil" },
            { href: "/cliente/como-e-calculado", label: "Como é calculado" },
          ]
        : [
            { href: "/cliente", label: "Início" },
            { href: "/cliente/como-e-calculado", label: "Como é calculado" },
            { href: "/cliente/entrar", label: "Entrar" },
          ],
    };
  }
  if (persona === "credor") {
    return {
      casa: "/banco",
      rotulo: "Operador de crédito",
      itens: logado
        ? [
            { href: "/banco", label: "Solicitações" },
            { href: "/banco/governanca", label: "Governança" },
            { href: "/banco/perfil", label: "Perfil" },
          ]
        : [{ href: "/banco/entrar", label: "Entrar" }],
    };
  }
  return {
    casa: "/",
    rotulo: null,
    itens: [
      { href: "/cliente", label: "Sou consumidor" },
      { href: "/banco", label: "Sou operador de crédito" },
      { href: "/governanca", label: "Governança" },
    ],
  };
}

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      {/* barras de sinal que terminam no total grifado */}
      <svg width="24" height="20" viewBox="0 0 24 20" aria-hidden="true">
        <rect x="0" y="13" width="4" height="7" fill="var(--cobalt)" />
        <rect x="6" y="9" width="4" height="11" fill="var(--cobalt)" />
        <rect x="12" y="5" width="4" height="15" fill="var(--cobalt)" />
        <rect x="18" y="0" width="6" height="20" fill="var(--ink)" />
        <rect x="18" y="14" width="6" height="3" fill="var(--lime)" />
      </svg>
      <span className={`display text-xl leading-none tracking-[-0.03em] ${compact ? "max-sm:hidden" : ""}`}>ScoreLyne</span>
    </span>
  );
}

export function SiteHeader({
  persona,
  logado = false,
  onSair,
}: {
  persona: Persona;
  logado?: boolean;
  onSair?: () => Promise<void>;
}) {
  const pathname = usePathname();
  const menu = menuDe(persona, logado);

  // O item ativo é o de caminho mais específico que combina com a página atual.
  const ativo = menu.itens
    .filter((i) => pathname === i.href || pathname.startsWith(`${i.href}/`))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;

  return (
    <header className="sticky top-0 z-30 bg-paper border-b border-ink">
      <div className="mx-auto max-w-7xl px-4 sm:px-8 h-14 flex items-stretch justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Link href={menu.casa} aria-label="ScoreLyne, início" className="flex items-center">
            <Logo compact />
          </Link>
          {menu.rotulo && (
            <span className="label border border-ink bg-lime px-2 py-1 whitespace-nowrap">
              <span className="sr-only">Persona: </span>
              {menu.rotulo}
            </span>
          )}
        </div>
        {/* Com seis itens o menu rola na horizontal em telas estreitas, em vez de quebrar o cabeçalho. */}
        <nav className="flex items-stretch overflow-x-auto text-[13px] sm:text-sm font-semibold" aria-label="Principal">
          {menu.itens.map((item) => {
            const atual = item.href === ativo;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={atual ? "page" : undefined}
                className={`flex items-center whitespace-nowrap px-2 sm:px-4 border-l border-rule last:border-r transition-colors ${
                  atual ? "bg-cobalt text-on-cobalt" : "hover:bg-tint"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
          {onSair && (
            <form action={onSair} className="flex items-stretch">
              <button
                type="submit"
                className="flex items-center whitespace-nowrap px-2 sm:px-4 border-r border-rule hover:bg-tint transition-colors"
              >
                Sair
              </button>
            </form>
          )}
        </nav>
      </div>
    </header>
  );
}

export function Rodape() {
  return (
    <footer className="border-t border-ink">
      <div className="mx-auto max-w-7xl px-4 sm:px-8 py-8 flex flex-col sm:flex-row gap-4 sm:items-center justify-between">
        <Logo />
        <p className="label text-ink-2">Credit scoring a partir do seu histórico telecom</p>
      </div>
    </footer>
  );
}
