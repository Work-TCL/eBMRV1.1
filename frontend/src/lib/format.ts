/** `viable_air` -> `Viable air`, `STEAM_AUTOCLAVE` -> `Steam autoclave`. For a static enum-like value
 * (a hardcoded dropdown option, a raw state/type code) shown as its own display text with no separate
 * human label of its own — replaces underscores/hyphens with spaces and sentence-cases the result, so a
 * reader sees words instead of a code. Same convention three call sites had already each hand-rolled a
 * copy of (`StatePill.tsx`'s `labelFor`, `JsonPanel.tsx` and `DdcpDetailPanels.tsx`'s `humanize`) —
 * centralised here now that a fourth+ use (static `<option>` lists) would otherwise add yet another
 * copy. Never apply this to already-human text (a free-typed name, a description) — only to a code. */
export function humanizeLabel(value: string): string {
  const spaced = value.replace(/[_-]+/g, " ").trim().toLowerCase();
  if (!spaced) return spaced;
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
