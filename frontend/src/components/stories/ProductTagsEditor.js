import { useState } from "react";
import { Plus, X, Link2, Pencil } from "lucide-react";
import { Input } from "@/components/ui/input";

export const MAX_STORY_PRODUCTS = 5;
let seq = 0;
export const newProduct = (name = "", url = "") => ({ key: `p${++seq}`, name, url, price: "" });
const emptyProduct = () => newProduct();

const LinkField = ({ url, index, onChange }) => {
  const [editing, setEditing] = useState(!url);

  if (editing || !url) {
    return (
      <Input data-testid={`story-product-url-${index}`} value={url} maxLength={2000} placeholder="Paste product link (https://...)"
        autoFocus={editing && !!url} onChange={(e) => onChange(e.target.value)} onBlur={() => url.trim() && setEditing(false)}
        className="rounded-full font-manrope h-9 text-sm" />
    );
  }
  return (
    <div data-testid={`story-product-link-pill-${index}`} className="flex items-center justify-between rounded-full bg-gray-100 pl-3 pr-1 h-9">
      <span className="flex items-center gap-2 font-manrope text-sm font-semibold"><Link2 className="w-4 h-4" /> Product Link</span>
      <button type="button" data-testid={`story-product-link-edit-${index}`} onClick={() => setEditing(true)}
        className="flex items-center gap-1 rounded-full px-3 h-7 font-manrope text-xs text-gray-600 hover:bg-white transition-colors">
        <Pencil className="w-3 h-3" /> Change
      </button>
    </div>
  );
};

const ProductRow = ({ product, index, onUpdate, onRemove }) => (
  <div data-testid={`story-product-row-${index}`} className="rounded-2xl border border-gray-200 p-2 space-y-2">
    <div className="flex gap-2">
      <Input data-testid={`story-product-name-${index}`} value={product.name} maxLength={80} placeholder="Product name"
        onChange={(e) => onUpdate("name", e.target.value)} className="rounded-full font-manrope h-9 text-sm" />
      <Input data-testid={`story-product-price-${index}`} value={product.price} type="number" min="0" step="0.01" placeholder="€"
        onChange={(e) => onUpdate("price", e.target.value)} className="rounded-full font-manrope h-9 text-sm w-24" />
      <button type="button" data-testid={`story-product-remove-${index}`} onClick={onRemove}
        className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center hover:bg-gray-100 transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>
    <LinkField url={product.url} index={index} onChange={(v) => onUpdate("url", v)} />
  </div>
);

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
        <ProductRow key={p.key} product={p} index={i} onUpdate={(k, v) => update(i, k, v)} onRemove={() => remove(i)} />
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
