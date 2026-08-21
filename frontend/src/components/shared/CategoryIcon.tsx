import * as icons from "lucide-react";
import { Circle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/** lucide-react exports PascalCase names; our backend stores kebab-case
 * icon slugs (e.g. "shopping-bag"), so convert before lookup. */
function toPascalCase(slug: string): string {
  return slug
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join("");
}

export function resolveIcon(slug: string | null | undefined): LucideIcon {
  if (!slug) return Circle;
  const name = toPascalCase(slug);
  const icon = (icons as unknown as Record<string, LucideIcon>)[name];
  return icon ?? Circle;
}

export function CategoryIcon({ icon, color, className = "h-4 w-4" }: { icon?: string | null; color?: string | null; className?: string }) {
  const Icon = resolveIcon(icon);
  return <Icon className={className} style={color ? { color } : undefined} />;
}
