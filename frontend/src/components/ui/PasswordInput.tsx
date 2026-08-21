import { forwardRef, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input, type InputProps } from "@/components/ui/Input";
import { cn } from "@/lib/utils";

/** A password Input with a show/hide toggle. Same props as Input; the
 * `type` prop is ignored (always starts as "password") since that's the
 * whole point of this component. */
export const PasswordInput = forwardRef<HTMLInputElement, Omit<InputProps, "type">>(
  ({ className, ...props }, ref) => {
    const [visible, setVisible] = useState(false);

    return (
      <div className="relative">
        <Input
          ref={ref}
          type={visible ? "text" : "password"}
          className={cn("pr-11", className)}
          {...props}
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
          className="absolute right-0 top-0 flex h-11 w-11 items-center justify-center text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    );
  },
);
PasswordInput.displayName = "PasswordInput";
