// Pure grouping of the compliance checklist into methodology groups, so the
// verifier reads field / lab / annual / project / security evidence separately.
// Kept framework-free and exported for unit testing.
import type { ChecklistItem } from "./api";

export type Group = "field" | "lab" | "annual" | "project" | "security";

export const GROUP_ORDER: Group[] = [
  "field",
  "lab",
  "project",
  "annual",
  "security",
];

export const GROUP_LABEL: Record<Group, string> = {
  field: "Field evidence (per run / batch)",
  lab: "Lab results",
  project: "Project registry",
  annual: "Annual verification",
  security: "Device security",
};

// Derive the display group from the catalog's `section` string, which carries
// the methodology bucket, e.g. "per-run (C1)", "lab (C7)", "project (C8)",
// "annual (C9)", "security".
export function groupOf(item: ChecklistItem): Group {
  const s = item.section.toLowerCase();
  if (s.includes("lab")) return "lab";
  if (s.includes("project")) return "project";
  if (s.includes("annual")) return "annual";
  if (s.includes("security")) return "security";
  return "field";
}

export type ItemStatus = "ok" | "blocking" | "inert";

// Green when passed; amber (blocking) when failed AND actually enforced for
// this batch; grey (inert) when the gate doesn't apply (no linkage) or is still
// flag-gated pending methodology sign-off.
export function statusOf(item: ChecklistItem): ItemStatus {
  if (item.ok) return "ok";
  if (item.enforcement === "enforced") return "blocking";
  return "inert";
}

export interface GroupedChecklist {
  group: Group;
  label: string;
  items: ChecklistItem[];
  okCount: number;
  blockingCount: number;
}

export function groupChecklist(checklist: ChecklistItem[]): GroupedChecklist[] {
  const buckets = new Map<Group, ChecklistItem[]>();
  for (const item of checklist) {
    const g = groupOf(item);
    if (!buckets.has(g)) buckets.set(g, []);
    buckets.get(g)!.push(item);
  }
  return GROUP_ORDER.filter((g) => buckets.has(g)).map((g) => {
    const items = buckets.get(g)!;
    return {
      group: g,
      label: GROUP_LABEL[g],
      items,
      okCount: items.filter((i) => i.ok).length,
      blockingCount: items.filter((i) => statusOf(i) === "blocking").length,
    };
  });
}
