import { useState } from "react";
import { Plus, Trash2, Tag } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { CategoryIcon } from "@/components/shared/CategoryIcon";
import { useCategories, useCreateCategory, useDeleteCategory } from "@/hooks/useExpenses";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

export function CategoriesSettingsPage() {
  const { data: categories } = useCategories({ kind: "expense" });
  const createCategory = useCreateCategory();
  const deleteCategory = useDeleteCategory();
  const { toast } = useToast();
  const [newName, setNewName] = useState("");

  const addCategory = async () => {
    if (!newName.trim()) return;
    try {
      await createCategory.mutateAsync({ name: newName.trim() });
      setNewName("");
    } catch (error) {
      toast({ title: "Could not add category", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Tag className="h-4 w-4" /> Expense categories</CardTitle>
        <CardDescription>Categories used across your expenses and budgets.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {categories?.map((cat) => (
          <div key={cat.id} className="flex items-center gap-3 rounded-xl bg-[var(--bg-inset)] p-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ backgroundColor: `${cat.color ?? "#94a3b8"}22` }}>
              <CategoryIcon icon={cat.icon} color={cat.color} className="h-4 w-4" />
            </div>
            <span className="flex-1 text-sm text-[var(--text-primary)]">{cat.name}</span>
            {cat.is_default && <span className="text-xs text-[var(--text-tertiary)]">Default</span>}
            {!cat.is_default && (
              <button
                onClick={async () => {
                  try {
                    await deleteCategory.mutateAsync(cat.id);
                  } catch (error) {
                    toast({ title: "Could not remove category", description: isApiError(error) ? error.message : undefined, variant: "error" });
                  }
                }}
                className="rounded-lg p-1.5 text-[var(--text-tertiary)] hover:bg-[var(--bg-surface)] hover:text-[var(--negative)]"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        ))}

        <div className="flex gap-2 pt-2">
          <Input
            placeholder="New category name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addCategory()}
          />
          <Button onClick={addCategory}><Plus className="h-4 w-4" /> Add</Button>
        </div>
      </CardContent>
    </Card>
  );
}
