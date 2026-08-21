import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
  /** Renders as a bottom sheet on small screens instead of a centred modal. */
  mobileSheet?: boolean;
}

export function Dialog({ open, onClose, title, description, children, className, mobileSheet = true }: DialogProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center md:items-center" role="dialog" aria-modal="true">
      <div
        className="absolute inset-0 animate-fade-in"
        style={{ background: "var(--bg-overlay)" }}
        onClick={onClose}
      />
      <div
        className={cn(
          "relative z-10 w-full max-h-[90dvh] overflow-y-auto bg-[var(--bg-surface)] p-6 animate-slide-up",
          mobileSheet
            ? "rounded-t-3xl md:rounded-2xl md:max-w-md md:m-4"
            : "rounded-2xl max-w-md m-4",
          className,
        )}
        style={{ boxShadow: "var(--shadow-elevated)" }}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 rounded-lg p-1.5 text-[var(--text-tertiary)] hover:bg-[var(--bg-inset)] hover:text-[var(--text-primary)]"
        >
          <X className="h-5 w-5" />
        </button>
        {title && <h2 className="pr-8 text-lg font-semibold text-[var(--text-primary)]">{title}</h2>}
        {description && <p className="mt-1 text-sm text-[var(--text-secondary)]">{description}</p>}
        <div className={cn(title || description ? "mt-5" : "")}>{children}</div>
      </div>
    </div>,
    document.body,
  );
}
