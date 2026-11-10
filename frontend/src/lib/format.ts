/**
 * General Formatting Utilities
 * Provides className merging, time formatting, and query result summarization
 */
export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function formatTime(timestamp: number) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(timestamp);
}

export function summarizeResult(data: unknown) {
  if (Array.isArray(data)) {
    return data.length > 0
      ? `Query complete: ${data.length} row(s) returned.`
      : "Query complete: Result set is empty.";
  }

  if (data && typeof data === "object") {
    return "Query complete: Structured result returned.";
  }

  if (data === null || data === undefined || data === "") {
    return "Query complete: Result set is empty.";
  }

  return `Query complete: ${String(data)}`;
}

export function toClipboardText(value: unknown) {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}
