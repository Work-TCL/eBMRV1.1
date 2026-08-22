"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, listAll, newIdempotencyKey, type MutationReceipt, type Product, type RecipeStep } from "@/lib/api";
import { PageHead } from "@/components/ui/PageHead";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

const emptyStep = (n: number): RecipeStep => ({
  step_number: n,
  name: "",
  instructions: "",
  requires_signature: false,
  signature_meaning: "",
});

export default function NewRecipePage() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [productId, setProductId] = useState("");
  const [version, setVersion] = useState(1);
  const [steps, setSteps] = useState<RecipeStep[]>([emptyStep(1)]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listAll<Product>("/products").then((ps) => {
      setProducts(ps);
      if (ps.length) setProductId(ps[0].id);
    });
  }, []);

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
    setBusy(true);
    setError(null);
    try {
      const receipt = await api.post<MutationReceipt>("/recipes", {
        idempotency_key: newIdempotencyKey(),
        product_id: productId,
        version,
        steps: steps.map((s) => ({
          step_number: s.step_number,
          name: s.name,
          instructions: s.instructions || null,
          requires_signature: s.requires_signature,
          signature_meaning: s.requires_signature ? s.signature_meaning || "Performed" : null,
        })),
      });
      router.push(`/recipes?created=${receipt.aggregate_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create recipe");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHead title="New recipe" subtitle="Define the product, the version, and the steps an operator will execute." />

      <form onSubmit={onSubmit}>
        <Card pad className="mb-4">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Product" required>
              <Select value={productId} onChange={(e) => setProductId(e.target.value)} required>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.code})
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Version" required>
              <Input
                type="number"
                min={1}
                value={version}
                onChange={(e) => setVersion(Number(e.target.value))}
              />
            </Field>
          </div>
        </Card>

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
        <Button type="submit" variant="primary" size="lg" disabled={busy || !productId}>
          <Icon name="database" /> {busy ? "Creating…" : "Create recipe"}
        </Button>
      </form>
    </div>
  );
}
