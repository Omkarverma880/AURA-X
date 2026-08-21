/** Curated dial-code list for the phone input - common markets first
 * (India/Nepal, since Bahi Khata's reference audience is South Asian),
 * then other major regions. Not the full ISO-3166 list: a phone sign-in
 * field benefits more from a short, scannable list than from completeness. */
export interface Country {
  code: string; // ISO 3166-1 alpha-2, used only as a React key
  name: string;
  dial: string; // E.164 prefix, including "+"
  flag: string; // emoji flag
}

export const COUNTRIES: Country[] = [
  { code: "IN", name: "India", dial: "+91", flag: "🇮🇳" },
  { code: "NP", name: "Nepal", dial: "+977", flag: "🇳🇵" },
  { code: "US", name: "United States", dial: "+1", flag: "🇺🇸" },
  { code: "GB", name: "United Kingdom", dial: "+44", flag: "🇬🇧" },
  { code: "AE", name: "United Arab Emirates", dial: "+971", flag: "🇦🇪" },
  { code: "CA", name: "Canada", dial: "+1", flag: "🇨🇦" },
  { code: "AU", name: "Australia", dial: "+61", flag: "🇦🇺" },
  { code: "SG", name: "Singapore", dial: "+65", flag: "🇸🇬" },
  { code: "BD", name: "Bangladesh", dial: "+880", flag: "🇧🇩" },
  { code: "PK", name: "Pakistan", dial: "+92", flag: "🇵🇰" },
  { code: "LK", name: "Sri Lanka", dial: "+94", flag: "🇱🇰" },
  { code: "DE", name: "Germany", dial: "+49", flag: "🇩🇪" },
  { code: "FR", name: "France", dial: "+33", flag: "🇫🇷" },
  { code: "SA", name: "Saudi Arabia", dial: "+966", flag: "🇸🇦" },
  { code: "QA", name: "Qatar", dial: "+974", flag: "🇶🇦" },
  { code: "MY", name: "Malaysia", dial: "+60", flag: "🇲🇾" },
  { code: "JP", name: "Japan", dial: "+81", flag: "🇯🇵" },
  { code: "NZ", name: "New Zealand", dial: "+64", flag: "🇳🇿" },
];

export const DEFAULT_COUNTRY = COUNTRIES[0]; // India

/** Split a stored E.164 number back into {country, national} for editing -
 * best-effort, matched by longest dial-code prefix so +1 (US/CA) and other
 * shared-prefix codes still resolve to *a* sensible country. */
export function splitPhone(e164: string | null | undefined): { country: Country; national: string } {
  if (!e164) return { country: DEFAULT_COUNTRY, national: "" };
  const sorted = [...COUNTRIES].sort((a, b) => b.dial.length - a.dial.length);
  const match = sorted.find((c) => e164.startsWith(c.dial));
  if (!match) return { country: DEFAULT_COUNTRY, national: e164.replace(/^\+/, "") };
  return { country: match, national: e164.slice(match.dial.length) };
}
