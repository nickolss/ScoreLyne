"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/cliente", label: "Para você" },
  { href: "/banco", label: "Para bancos" },
  { href: "/governanca", label: "Governança" },
];

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

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-30 bg-paper border-b border-ink">
      <div className="mx-auto max-w-7xl px-4 sm:px-8 h-14 flex items-stretch justify-between gap-3">
        <Link href="/" aria-label="ScoreLyne, início" className="flex items-center">
          <Logo compact />
        </Link>
        <nav className="flex items-stretch text-[13px] sm:text-sm font-semibold">
          {NAV.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center whitespace-nowrap px-2 sm:px-4 border-l border-rule last:border-r transition-colors ${
                  active ? "bg-cobalt text-on-cobalt" : "hover:bg-tint"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
