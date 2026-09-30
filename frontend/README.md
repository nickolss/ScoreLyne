# ScoreLyne — Frontend

Protótipo navegável em Next.js 16 (App Router, TypeScript, Tailwind v4). Todos os dados são fictícios e ficam em `src/lib/data.ts` até o backend existir.

```bash
npm install
npm run dev   # http://localhost:3000
```

## Telas

| Rota | O que mostra |
|---|---|
| `/` | Apresentação da ideia: problema, como funciona, atores e alternativas atuais |
| `/cliente` | Jornada do cliente: pedido → consentimento granular (LGPD) → análise do agente → score explicado, oferta e caminho de melhora; permite revogar o consentimento |
| `/banco` | Painel do banco: indicadores e lista de solicitações filtrável pela decisão do agente |
| `/banco/[id]` | Detalhe: score, fatores, explicação a favor/contra, revisão humana com justificativa obrigatória e trilha de auditoria |
| `/governanca` | Princípios de equidade, explicabilidade, LGPD e supervisão humana; o que entra e o que nunca entra no modelo |

## Modelo de score (mock)

Score de 0 a 1000 = soma ponderada de 5 fatores (0–100) × 10:
regularidade de recargas (30%), permanência na base (25%), pontualidade (20%), estabilidade do número (15%) e consistência do valor gasto (10%).

- **≥ 750** — pré-aprovação automática
- **550–749** — sempre vai para um analista humano
- **< 550** — não aprovado, com dicas de melhora por fator

Fatores que o cliente não autoriza saem do cálculo e os pesos restantes são renormalizados.
