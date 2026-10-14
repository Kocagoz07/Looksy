import { Plus, X } from "lucide-react";
import { Input } from "@/components/ui/input";

export const MAX_STORY_PRODUCTS = 5;
export const emptyProduct = () => ({ name: "", url: "", price: "" });

export const ProductTagsEditor = ({ products, onChange }) => {
  const update = (i, key, value) => onChange(products.map((p, idx) => (idx === i ? { ...p, [key]: value } : p)));
  const remove = (i) => onChange(products.filter((_, idx) => idx !== i));

  return (
    <div data-testid="story-products-editor" className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-manrope text-sm font-semibold">Shop the look</span>
        <span className="font-manrope text-xs text-gray-400">{products.length}/{MAX_STORY_PRODUCTS}</span>
      </div>
      {products.map((p, i) => (
        <div key={i} data-testid={`story-product-row-${i}`} className="rounded-2xl border border-gray-200 p-2 space-y-2">
          <div className="flex gap-2">
            <Input data-testid={`story-product-name-${i}`} value={p.name} maxLength={80} placeholder="Product name"
              onChange={(e) => update(i, "name", e.target.value)} className="rounded-full font-manrope h-9 text-sm" />
            <Input data-testid={`story-product-price-${i}`} value={p.price} type="number" min="0" step="0.01" placeholder="€"
              onChange={(e) => update(i, "price", e.target.value)} className="rounded-full font-manrope h-9 text-sm w-24" />
            <button type="button" data-testid={`story-product-remove-${i}`} onClick={() => remove(i)}
              className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center hover:bg-gray-100 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <Input data-testid={`story-product-url-${i}`} value={p.url} maxLength={2000} placeholder="Product link (https://...)"
            onChange={(e) => update(i, "url", e.target.value)} className="rounded-full font-manrope h-9 text-sm" />
        </div>
      ))}
      {products.length < MAX_STORY_PRODUCTS && (
        <button type="button" data-testid="story-product-add-btn" onClick={() => onChange([...products, emptyProduct()])}
          className="w-full flex items-center justify-center gap-2 rounded-full border border-dashed border-gray-300 py-2 font-manrope text-sm text-gray-600 hover:border-black hover:text-black transition-colors">
          <Plus className="w-4 h-4" /> Add product link
        </button>
      )}
    </div>
  );
};
