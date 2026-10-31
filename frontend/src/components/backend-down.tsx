type Servico = "credor" | "consumidor" | "operadora";

const COMANDO: Record<Servico, string> = {
  credor: "uv run banco servir",
  consumidor: "uv run consumidor servir",
  operadora: "uv run operadora servir",
};

// Aviso para quando a API do backend não responde.
export function BackendDown({ message, service = "credor" }: { message: string; service?: Servico }) {
  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-8 py-16">
      <div className="border-2 border-red p-6" role="alert">
        <p className="display text-2xl">Serviço indisponível.</p>
        <p className="mt-3 text-ink-2">{message}</p>
        <p className="mt-4 text-sm">
          Suba o backend com <code className="num bg-tint px-1">docker compose up -d</code> na raiz e{" "}
          <code className="num bg-tint px-1">{COMANDO[service]}</code> em{" "}
          <code className="num bg-tint px-1">backend/</code> (a operadora e o outro módulo também precisam estar
          no ar).
        </p>
      </div>
    </div>
  );
}
