"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError, newIdempotencyKey, type MutationReceipt, type RecipeDetail, type RecipeStep } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

const emptyStep = (n: number): RecipeStep => ({
  step_number: n,
  name: "",
  instructions: "",
  requires_signature: false,
  signature_meaning: "",
});

export default function EditRecipePage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [steps, setSteps] = useState<RecipeStep[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get<RecipeDetail>(`/recipes/${params.id}`)
      .then((r) => {
        setRecipe(r);
        setSteps(r.steps.length ? r.steps : [emptyStep(1)]);
      })
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Failed to load recipe"));
  }, [params.id]);

  function updateStep(i: number, patch: Partial<RecipeStep>) {
    setSteps((prev) => prev.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));
  }

  function addStep() {
    setSteps((prev) => [...prev, emptyStep(prev.length + 1)]);
  }

  function removeStep(i: number) {
    setSteps((prev) =>
      prev.filter((_, idx) => idx !== i).map((s, idx) => ({ ...s, step_number: idx + 1 }))
    );
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!recipe) return;
    setBusy(true);
    setError(null);
    try {
      await api.patch<MutationReceipt>(`/recipes/${recipe.id}`, {
        idempotency_key: newIdempotencyKey(),
        recipe_id: recipe.id,
        steps: steps.map((s) => ({
          step_number: s.step_number,
          name: s.name,
          instructions: s.instructions || null,
          requires_signature: s.requires_signature,
          signature_meaning: s.requires_signature ? s.signature_meaning || "Performed" : null,
        })),
      });
      router.push(`/recipes?updated=${recipe.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update recipe");
    } finally {
      setBusy(false);
    }
  }

  if (loadError) return <p className="error-text">{loadError}</p>;
  if (!recipe) return null;

  return (
    <div>
      <PageHead
        title="Edit recipe"
        subtitle={`Version ${recipe.version} — locked once any batch has used it; create a new version instead.`}
      />

      <form onSubmit={onSubmit}>
        <div className="flex flex-col gap-3 mb-4">
          {steps.map((step, i) => (
            <Card key={i} pad>
              <div className="flex gap-3 items-start">
                <span className="fs-2 text-muted" style={{ paddingTop: 9, whiteSpace: "nowrap" }}>
                  Step {step.step_number}
                </span>
                <div className="flex-1">
                  <Field label="Step name" required>
                    <Input value={step.name} onChange={(e) => updateStep(i, { name: e.target.value })} required />
                  </Field>
                  <Field label="Instructions" hint="Shown to the operator when the step is active.">
                    <textarea
                      className="input"
                      rows={2}
                      value={step.instructions ?? ""}
                      onChange={(e) => updateStep(i, { instructions: e.target.value })}
                    />
                  </Field>
                  <label className="checkbox-row fs-3">
                    <input
                      type="checkbox"
                      checked={step.requires_signature}
                      onChange={(e) => updateStep(i, { requires_signature: e.target.checked })}
                    />
                    <span>
                      Requires electronic signature
                      {step.requires_signature && (
                        <Input
                          className="mt-2"
                          placeholder="Meaning, e.g. Performed"
                          value={step.signature_meaning ?? ""}
                          onChange={(e) => updateStep(i, { signature_meaning: e.target.value })}
                        />
                      )}
                    </span>
                  </label>
                </div>
                {steps.length > 1 && (
                  <Button type="button" variant="ghost" size="sm" onClick={() => removeStep(i)}>
                    <Icon name="x" /> Remove
                  </Button>
                )}
              </div>
            </Card>
          ))}
          <Button type="button" variant="secondary" onClick={addStep} className="mt-1" style={{ alignSelf: "flex-start" }}>
            <Icon name="plus" /> Add step
          </Button>
        </div>

        {error && <p className="error-text mb-3">{error}</p>}
        <div className="flex gap-3">
          <Button type="button" variant="secondary" onClick={() => router.push("/recipes")}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" size="lg" disabled={busy}>
            <Icon name="database" /> {busy ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </div>
  );
}
