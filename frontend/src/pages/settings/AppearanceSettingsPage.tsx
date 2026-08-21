import { Sun, Moon, Monitor } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { useTheme, type ThemePreference } from "@/contexts/ThemeContext";
import { cn } from "@/lib/utils";

const OPTIONS: { value: ThemePreference; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

export function AppearanceSettingsPage() {
  const { theme, setTheme } = useTheme();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Theme</CardTitle>
        <CardDescription>Choose how Aura X looks on this device.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-3">
          {OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setTheme(option.value)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border-2 p-4 transition-colors",
                theme === option.value
                  ? "border-[var(--brand)] bg-[var(--brand-soft)]"
                  : "border-[var(--border-default)] hover:bg-[var(--bg-surface-hover)]",
              )}
            >
              <option.icon className={cn("h-5 w-5", theme === option.value ? "text-[var(--brand)]" : "text-[var(--text-secondary)]")} />
              <span className={cn("text-sm font-medium", theme === option.value ? "text-[var(--brand-soft-text)]" : "text-[var(--text-secondary)]")}>
                {option.label}
              </span>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
