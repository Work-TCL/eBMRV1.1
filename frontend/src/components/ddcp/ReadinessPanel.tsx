import { Banner } from "@/components/ui/Banner";
import { Icon } from "@/components/ui/Icon";

interface Blocker {
  code: string;
  message: string;
  [key: string]: unknown;
}

interface ReadinessResponse {
  ready: boolean;
  blockers?: Blocker[];
  [key: string]: unknown;
}

/** The one part of the readiness/genealogy/review-summary composition worth a dedicated, human-first
 * view: "is this batch ready, and if not, why not" (spec section 14 — every state gets clear feedback,
 * not a raw JSON dump). Everything else in the response still renders through `JsonPanel`, which
 * already labels flat key/value pairs — `blockers` is the one array-of-objects shape that would
 * otherwise fall back to a raw `<pre>` block. */
export function ReadinessPanel({ readiness }: { readiness: ReadinessResponse }) {
  if (readiness.ready) {
    return (
      <Banner tone="ok" title="Ready">
        Every readiness check for this batch is satisfied.
      </Banner>
    );
  }
  const blockers = readiness.blockers ?? [];
  return (
    <Banner tone="warn" title="Not ready yet">
      <div className="mt-1">
        {blockers.length === 0
          ? "This batch isn't ready, but no specific blocker was reported."
          : blockers.map((b, i) => (
              <div key={i} className="flex gap-2" style={{ padding: "3px 0" }}>
                <Icon name="alert-triangle" />
                <span>
                  {b.message} <span className="text-muted tabular">({b.code})</span>
                </span>
              </div>
            ))}
      </div>
    </Banner>
  );
}
