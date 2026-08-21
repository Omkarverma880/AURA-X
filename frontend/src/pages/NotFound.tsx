import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function NotFoundPage() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-[var(--bg-base)] px-6 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--brand-soft)]">
        <Compass className="h-8 w-8 text-[var(--brand)]" />
      </div>
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">Page not found</h1>
      <p className="max-w-sm text-sm text-[var(--text-secondary)]">
        The page you are looking for does not exist or has moved.
      </p>
      <Link to="/dashboard">
        <Button>Back to Dashboard</Button>
      </Link>
    </div>
  );
}
