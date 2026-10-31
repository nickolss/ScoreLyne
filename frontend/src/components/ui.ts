// Classes compartilhadas do sistema visual "Extrato da Linha": zero raio, régua de 1px, cobalto e lime.
// Ficam num módulo sem "use client" para servir a componentes de servidor e de navegador.

export const campo =
  "mt-2 w-full border border-ink bg-paper px-4 py-3 placeholder:text-ink-2 focus:outline-2 focus:outline-cobalt focus:-outline-offset-1";

export const btnPrimary =
  "inline-flex items-center justify-center gap-3 bg-ink text-paper px-5 py-3.5 font-semibold hover:bg-cobalt transition-colors disabled:opacity-35 disabled:hover:bg-ink disabled:cursor-not-allowed";

export const btnSecondary =
  "inline-flex items-center justify-center border border-ink px-5 py-3.5 font-semibold hover:bg-tint transition-colors";
