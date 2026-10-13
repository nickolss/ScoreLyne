// Aviso para quando a API do backend não responde.
export function BackendDown({ message, service = "banco" }: { message: string; service?: "banco" | "operadora" }) {
  const cmd = service === "banco" ? "uv run banco servir" : "uv run operadora servir";
  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-8 py-16">
      <div className="border-2 border-red p-6" role="alert">
        <p className="display text-2xl">Serviço indisponível.</p>
        <p className="mt-3 text-ink-2">{message}</p>
        <p className="mt-4 text-sm">
          Suba o backend com <code className="num bg-tint px-1">docker compose up -d</code> na raiz e{" "}
          <code className="num bg-tint px-1">{cmd}</code> em <code className="num bg-tint px-1">backend/</code>.
        </p>
      </div>
    </div>
  );
}
