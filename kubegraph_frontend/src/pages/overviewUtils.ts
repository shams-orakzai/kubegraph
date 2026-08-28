import type { Remediation } from "../api/types";

export const BAND_TAG: Record<string, string> = {
  Low: "tag-ok", Medium: "tag-med", High: "tag-crit",
};

export function cutTag(cut: number, reaching: number): string {
  if (cut >= reaching && reaching > 0) return "tag-crit";
  if (cut > 0) return "tag-med";
  return "tag-low";
}

/** Width % for a remediation's impact meter, relative to the top fix. */
export function impactPct(r: Remediation, maxPaths: number): number {
  if (maxPaths <= 0) return 0;
  return Math.max(4, Math.round((r.paths_cut / maxPaths) * 100));
}
