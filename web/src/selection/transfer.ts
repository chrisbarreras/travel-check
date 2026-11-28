// The slider's setting in the address (ADR-0010; spec FR-003): ?transfer=<minutes>.
export const TRANSFER_MIN = 15;
export const TRANSFER_MAX = 120;
export const TRANSFER_STEP = 5;

/** A valid setting from the address, or null. */
export function parseTransfer(search: string): number | null {
  const raw = new URLSearchParams(search).get("transfer");
  if (raw === null || !/^\d+$/.test(raw)) return null;
  const value = Number(raw);
  return value >= TRANSFER_MIN && value <= TRANSFER_MAX && value % TRANSFER_STEP === 0
    ? value
    : null;
}

/** The query string with the setting, or without it at the default. */
export function withTransfer(search: string, value: number, defaultValue: number): string {
  const params = new URLSearchParams(search);
  if (value === defaultValue) params.delete("transfer");
  else params.set("transfer", String(value));
  const text = params.toString().replaceAll("%2C", ",");
  return text === "" ? "" : `?${text}`;
}
