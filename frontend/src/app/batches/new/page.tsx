"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, listAll, newIdempotencyKey, type MutationReceipt, type Product, type RecipeSummary } from "@/lib/api";
import { useSites } from "@/lib/hooks";
import { PageHead } from "@/components/ui/PageHead";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

export default function NewBatchPage() {
  const router = useRouter();
  const { sites } = useSites();
  const [products, setProducts] = useState<Product[]>([]);
  const [recipes, setRecipes] = useState<RecipeSummary[]>([]);
  const [productId, setProductId] = useState("");
  const [recipeId, setRecipeId] = useState("");
  const [batchNumber, setBatchNumber] = useState("");
  const [targetQuantity, setTargetQuantity] = useState("100");
  const [uom, setUom] = useState("kg");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listAll<Product>("/products").then(setProducts);
    listAll<RecipeSummary>("/recipes").then(setRecipes);
  }, []);

  const recipesForProduct = recipes.filter((r) => r.product_id === productId);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!sites.length || !recipeId) return;
    setBusy(true);
    setError(null);
    try {
      const recipe = recipes.find((r) => r.id === recipeId)!;
      const receipt = await api.post<MutationReceipt>("/batches", {
        idempotency_key: newIdempotencyKey(),
        site_id: sites[0].id,
        product_id: productId,
        recipe_id: recipeId,
        recipe_version: recipe.version,
        batch_number: batchNumber,
        target_quantity: targetQuantity,
        uom,
      });
      router.push(`/batches/${receipt.aggregate_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create batch");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHead title="New batch" subtitle="Issue a new batch record against a released recipe version." />

      <Card pad style={{ maxWidth: 480 }}>
        <form onSubmit={onSubmit}>
          <Field label="Product" required>
            <Select
              value={productId}
              onChange={(e) => {
                setProductId(e.target.value);
                setRecipeId("");
              }}
              required
            >
              <option value="">Select product</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Recipe version" required>
            <Select value={recipeId} onChange={(e) => setRecipeId(e.target.value)} required disabled={!productId}>
              <option value="">Select recipe version</option>
              {recipesForProduct.map((r) => (
                <option key={r.id} value={r.id}>
                  v{r.version}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Batch number" required>
            <Input value={batchNumber} onChange={(e) => setBatchNumber(e.target.value)} required />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Target quantity" required>
              <Input value={targetQuantity} onChange={(e) => setTargetQuantity(e.target.value)} required />
            </Field>
            <Field label="UOM" required>
              <Input value={uom} onChange={(e) => setUom(e.target.value)} required />
            </Field>
          </div>

          {error && <p className="error-text mb-3">{error}</p>}
          <Button type="submit" variant="primary" disabled={busy}>
            <Icon name="file-plus-2" /> {busy ? "Creating…" : "Create batch"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
