/**
 * Empty State Component
 * Displays system capabilities and one-click starter queries.
 */
import { LineChart, Search, ShoppingBag, Sparkles } from "lucide-react";

type EmptyStateProps = {
  examples: string[];
  onUseExample: (example: string) => void;
};

const highlights = [
  { label: "Schema-Aware RAG", icon: Search },
  { label: "AST Safety Validator", icon: LineChart },
  { label: "Enterprise Warehouse", icon: ShoppingBag },
];

export function EmptyState({ examples, onUseExample }: EmptyStateProps) {
  return (
    <div className="mx-auto flex min-h-full max-w-5xl flex-col justify-center px-4 py-12">
      <div className="mb-10 max-w-3xl">
        <div className="mb-5 inline-flex items-center gap-2 border border-moss/25 bg-moss/10 px-3 py-1.5 text-sm font-semibold text-moss">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          DataPilot Autonomous Analyst
        </div>
        <h1 className="text-balance text-4xl font-semibold leading-tight text-ink sm:text-6xl">
          Natural Language to SQL
        </h1>
        <p className="mt-4 text-base leading-relaxed text-ink/65 sm:text-lg">
          Ask questions in natural language. DataPilot automatically identifies schema relationships,
          synthesizes verified SQL queries across blind subagents, and safely executes them against the data warehouse.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {highlights.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="border border-ink/10 bg-white/55 px-4 py-4">
              <Icon className="mb-5 h-5 w-5 text-brass" aria-hidden="true" />
              <div className="text-sm font-semibold text-ink">{item.label}</div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {examples.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => onUseExample(example)}
            className="min-h-20 border border-ink/10 bg-[#fffaf1]/75 px-4 py-4 text-left text-[15px] leading-6 text-ink transition hover:-translate-y-0.5 hover:border-moss/35 hover:bg-white focus:outline-none focus:ring-2 focus:ring-moss/35"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
