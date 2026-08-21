import { useState } from "react";
import { COUNTRIES, DEFAULT_COUNTRY, splitPhone, type Country } from "@/lib/countries";
import { cn } from "@/lib/utils";

interface PhoneInputProps {
  /** Full E.164 value, e.g. "+919876543210". Empty string while incomplete. */
  value: string;
  onChange: (e164: string) => void;
  id?: string;
  disabled?: boolean;
  autoFocus?: boolean;
}

/** Country-code select + national-number field, combined into one E.164
 * string. Defaults to India since that is Bahi Khata's primary market, but
 * covers Nepal/UK/US/UAE and a dozen more so sign-in isn't India-only. */
export function PhoneInput({ value, onChange, id, disabled, autoFocus }: PhoneInputProps) {
  const initial = splitPhone(value);
  const [country, setCountry] = useState<Country>(initial.country);
  const [national, setNational] = useState(initial.national);

  const emit = (nextCountry: Country, nextNational: string) => {
    const digits = nextNational.replace(/\D/g, "");
    onChange(digits ? `${nextCountry.dial}${digits}` : "");
  };

  return (
    <div className="flex gap-2">
      <select
        value={country.code}
        disabled={disabled}
        onChange={(e) => {
          const next = COUNTRIES.find((c) => c.code === e.target.value) ?? DEFAULT_COUNTRY;
          setCountry(next);
          emit(next, national);
        }}
        className={cn(
          "h-11 shrink-0 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] pl-2.5 pr-1 text-sm text-[var(--text-primary)]",
          "focus:outline-none focus:ring-2 focus:ring-[var(--brand)] focus:border-transparent",
        )}
        aria-label="Country code"
      >
        {COUNTRIES.map((c) => (
          <option key={c.code} value={c.code}>
            {c.flag} {c.dial}
          </option>
        ))}
      </select>
      <input
        id={id}
        type="tel"
        inputMode="numeric"
        autoFocus={autoFocus}
        disabled={disabled}
        placeholder="98765 43210"
        value={national}
        onChange={(e) => {
          const digits = e.target.value.replace(/\D/g, "").slice(0, 12);
          setNational(digits);
          emit(country, digits);
        }}
        className={cn(
          "h-11 w-full rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] px-3.5 text-sm",
          "text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] transition-colors",
          "focus:outline-none focus:ring-2 focus:ring-[var(--brand)] focus:border-transparent",
        )}
      />
    </div>
  );
}
