/**
 * Agent Execution Flow Graph Component
 * Visualizes the multi-stage LangGraph execution pipeline and node statuses.
 */
import { Check, Circle, LoaderCircle, X } from "lucide-react";
import { cn } from "../lib/format";
import type { ProgressStatus, StepState } from "../types/agent";

type FlowStatus = ProgressStatus | "pending";

type FlowNode = {
  step: string;
  x: number;
  y: number;
  w?: number;
};

const nodes: FlowNode[] = [
  { step: "Extract Keywords", x: 410, y: 20, w: 160 },
  { step: "Recall Columns", x: 150, y: 112, w: 150 },
  { step: "Recall Metrics", x: 410, y: 112, w: 150 },
  { step: "Recall Values", x: 670, y: 112, w: 150 },
  { step: "Merge Context", x: 410, y: 214, w: 160 },
  { step: "Filter Metrics", x: 290, y: 318, w: 150 },
  { step: "Filter Tables", x: 530, y: 318, w: 150 },
  { step: "Assemble Schema Context", x: 410, y: 422, w: 190 },
  { step: "Generate SQL", x: 410, y: 526, w: 160 },
  { step: "Validate SQL", x: 410, y: 630, w: 160 },
  { step: "Correct SQL", x: 670, y: 630, w: 150 },
  { step: "Execute SQL", x: 410, y: 724, w: 160 },
];

const connectors = [
  "M410 60 L410 84 L150 84 L150 106",
  "M410 60 L410 106",
  "M410 60 L410 84 L670 84 L670 106",
  "M150 152 L150 178 L410 178 L410 208",
  "M410 152 L410 208",
  "M670 152 L670 178 L410 178 L410 208",
  "M410 254 L410 282 L290 282 L290 312",
  "M410 254 L410 282 L530 282 L530 312",
  "M290 358 L290 386 L410 386 L410 416",
  "M530 358 L530 386 L410 386 L410 416",
  "M410 462 L410 520",
  "M410 566 L410 624",
  "M410 670 L410 718",
  "M488 650 L586 650",
  "M670 670 L670 696 L410 696 L410 718",
];

const branchLabels = [
  { text: "Error", x: 530, y: 642 },
  { text: "Valid", x: 366, y: 704 },
];

function getStatusMap(steps: StepState[]) {
  return steps.reduce<Record<string, StepState>>((map, item) => {
    map[item.step.toLowerCase()] = item;
    map[item.step] = item;
    return map;
  }, {});
}

function statusFor(step: string, map: Record<string, StepState>): FlowStatus {
  if (map[step]) return map[step].status;
  if (map[step.toLowerCase()]) return map[step.toLowerCase()].status;
  return "pending";
}

function NodeIcon({ status }: { status: FlowStatus }) {
  if (status === "running") {
    return <LoaderCircle className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />;
  }

  if (status === "success") {
    return <Check className="h-3.5 w-3.5" aria-hidden="true" />;
  }

  if (status === "error") {
    return <X className="h-3.5 w-3.5" aria-hidden="true" />;
  }

  return <Circle className="h-3.5 w-3.5" aria-hidden="true" />;
}

function FlowNodeCard({ node, status }: { node: FlowNode; status: FlowStatus }) {
  const width = node.w ?? 156;

  return (
    <div
      className="absolute -translate-x-1/2"
      style={{ left: node.x, top: node.y, width }}
    >
      <div
        className={cn(
          "flex h-10 items-center gap-2 border px-3 text-sm font-semibold shadow-line transition",
          status === "pending" && "border-ink/10 bg-white/55 text-ink/45",
          status === "running" && "border-brass/45 bg-brass/15 text-ink",
          status === "success" && "border-moss/25 bg-moss/10 text-ink",
          status === "error" && "border-tomato/35 bg-tomato/10 text-tomato",
        )}
      >
        <span
          className={cn(
            "grid h-5 w-5 shrink-0 place-items-center rounded-full text-[11px]",
            status === "pending" && "bg-ink/10 text-ink/45",
            status === "running" && "bg-brass/25 text-ink",
            status === "success" && "bg-moss text-white",
            status === "error" && "bg-tomato text-white",
          )}
        >
          <NodeIcon status={status} />
        </span>
        <span className="truncate">{node.step}</span>
      </div>
    </div>
  );
}

export function StepRail({ steps = [] }: { steps?: StepState[] }) {
  if (!steps || steps.length === 0) {
    return null;
  }

  const statusMap = getStatusMap(steps);

  return (
    <section className="mt-4 border border-ink/10 bg-[#efe6d8]/55 p-3">
      <div className="mb-2 flex items-center justify-between px-1 text-xs font-semibold uppercase tracking-[0.16em] text-ink/55">
        <span>Agent Execution Workflow</span>
        <span>{steps.length} Steps Active</span>
      </div>

      <div className="overflow-x-auto pb-2">
        <div className="relative mx-auto h-[780px] w-[820px]">
          <svg
            className="pointer-events-none absolute inset-0 h-full w-full"
            viewBox="0 0 820 780"
            fill="none"
            aria-hidden="true"
          >
            <defs>
              <marker
                id="flow-arrow"
                markerHeight="8"
                markerWidth="8"
                orient="auto"
                refX="6"
                refY="4"
              >
                <path d="M0 0 L8 4 L0 8 Z" fill="rgba(32,32,29,0.58)" />
              </marker>
            </defs>
            {connectors.map((path) => (
              <path
                key={path}
                d={path}
                stroke="rgba(32,32,29,0.5)"
                strokeWidth="1.5"
                markerEnd="url(#flow-arrow)"
              />
            ))}
            {branchLabels.map((label) => (
              <text
                key={label.text}
                x={label.x}
                y={label.y}
                fill="rgba(32,32,29,0.62)"
                fontSize="13"
                fontWeight="600"
              >
                {label.text}
              </text>
            ))}
          </svg>

          {nodes.map((node) => (
            <FlowNodeCard
              key={node.step}
              node={node}
              status={statusFor(node.step, statusMap)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
