import { useEffect, useState } from "react";
import { Eye, X, ShoppingBag } from "lucide-react";
import axios from "axios";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { picUrl, timeAgo } from "@/utils/media";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const StoryViewersSheet = ({ storyId, onClose }) => {
  const [viewers, setViewers] = useState(null);
  const [clicks, setClicks] = useState([]);

  useEffect(() => {
    axios.get(`${BACKEND_URL}/api/stories/${storyId}/viewers`, { withCredentials: true })
      .then(({ data }) => { setViewers(data.viewers); setClicks(data.product_clicks || []); })
      .catch(() => setViewers([]));
  }, [storyId]);

  return (
    <div className="absolute inset-x-0 bottom-0 z-30 bg-white text-black rounded-t-3xl max-h-[60%] flex flex-col animate-in slide-in-from-bottom duration-300"
      data-testid="story-viewers-sheet" onPointerDown={(e) => e.stopPropagation()} onClick={(e) => e.stopPropagation()}>
      <div className="flex items-center justify-between px-5 py-4 border-b">
        <span className="font-manrope font-semibold flex items-center gap-2">
          <Eye className="w-4 h-4" /> Seen by {viewers ? viewers.length : "…"}
        </span>
        <button data-testid="story-viewers-close-btn" onClick={onClose} className="p-1 rounded-full hover:bg-gray-100"><X className="w-5 h-5" /></button>
      </div>
      <div className="overflow-y-auto px-3 py-2">
        {clicks.length > 0 && (
          <div data-testid="story-product-clicks" className="mx-2 mb-2 rounded-2xl bg-gray-50 p-3 space-y-1.5">
            <p className="font-manrope text-xs font-semibold uppercase tracking-widest text-gray-500 flex items-center gap-2">
              <ShoppingBag className="w-3.5 h-3.5" /> Product clicks · {clicks.reduce((n, c) => n + c.clicks, 0)}
            </p>
            {clicks.map((c, i) => (
              <div key={c.link_id} data-testid={`story-product-clicks-${i}`} className="flex justify-between font-manrope text-sm">
                <span className="truncate pr-3">{c.name}</span><span className="font-semibold">{c.clicks}</span>
              </div>
            ))}
          </div>
        )}
        {viewers?.length === 0 && (
          <p data-testid="story-viewers-empty" className="py-8 text-center font-manrope text-sm text-gray-500">No views yet.</p>
        )}
        {viewers?.map((v) => (
          <div key={v.user_id} data-testid={`story-viewer-${v.user_id}`} className="flex items-center gap-3 px-2 py-2">
            <Avatar className="w-9 h-9">
              <AvatarImage src={picUrl(v.picture)} />
              <AvatarFallback className="bg-gray-200 text-xs">{v.name?.[0]?.toUpperCase() || "?"}</AvatarFallback>
            </Avatar>
            <span className="flex-1 font-manrope text-sm font-semibold">{v.name || "Looksy user"}</span>
            <span className="font-manrope text-xs text-gray-400">{timeAgo(v.viewed_at)}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
