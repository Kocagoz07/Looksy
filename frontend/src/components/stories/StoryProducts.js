import { ShoppingBag, ExternalLink, X } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const ProductStrip = ({ products, onOpen }) => (
  <div data-testid="story-products-strip" className="flex gap-2 overflow-x-auto [scrollbar-width:none]">
    {products.map((p, i) => (
      <button key={p.link_id} type="button" data-testid={`story-product-chip-${i}`} onClick={() => onOpen(p)}
        className="shrink-0 flex items-center gap-2 rounded-full bg-white text-black pl-3 pr-4 py-2 font-manrope text-xs font-semibold shadow-lg transition-transform duration-200 hover:scale-105">
        <ShoppingBag className="w-3.5 h-3.5" />
        <span className="max-w-[140px] truncate">{p.name}</span>
        {p.price != null && <span className="text-gray-500 font-normal">€{p.price.toFixed(2)}</span>}
      </button>
    ))}
  </div>
);

export const ProductCardSheet = ({ product, onClose }) => {
  const buy = () => window.open(`${BACKEND_URL}/api/affiliate/track/${product.link_id}`, "_blank", "noopener,noreferrer");
  return (
    <div className="absolute inset-0 z-30 flex items-end" onPointerDown={(e) => e.stopPropagation()}>
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div data-testid="story-product-card" className="relative w-full bg-white text-black rounded-t-3xl p-5 space-y-4 animate-in slide-in-from-bottom duration-300">
        <button data-testid="story-product-card-close" onClick={onClose} className="absolute right-4 top-4 p-1 rounded-full hover:bg-gray-100">
          <X className="w-5 h-5" />
        </button>
        <div className="flex items-start gap-3 pr-8">
          <span className="w-12 h-12 shrink-0 rounded-2xl bg-black text-white flex items-center justify-center"><ShoppingBag className="w-5 h-5" /></span>
          <div className="min-w-0">
            <p data-testid="story-product-card-name" className="font-manrope font-semibold text-base break-words">{product.name}</p>
            <p data-testid="story-product-card-store" className="font-manrope text-xs text-gray-500 uppercase tracking-widest mt-1">{product.retailer}</p>
          </div>
        </div>
        {product.price != null && (
          <p data-testid="story-product-card-price" className="font-italiana text-4xl">€{product.price.toFixed(2)}</p>
        )}
        <button data-testid="story-product-buy-btn" onClick={buy}
          className="w-full h-12 rounded-full bg-black text-white font-manrope font-semibold flex items-center justify-center gap-2 hover:bg-gray-800 transition-colors">
          Buy now <ExternalLink className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
