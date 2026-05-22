import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Sparkles,
  Wand2,
  ShoppingBag,
  Bookmark,
  Loader2,
  TrendingUp,
  Tag,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function OutfitGeneratorPage() {
  const navigate = useNavigate();

  const [options, setOptions] = useState({ styles: [], occasions: [], seasons: [] });
  const [form, setForm] = useState({
    occasion: "everyday",
    style: "casual",
    season: "all-season",
    budget: "",
    color_preference: "",
    additional_notes: "",
  });
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [trending, setTrending] = useState([]);

  useEffect(() => {
    loadOptions();
    loadHistory();
    loadTrending();
  }, []);

  const loadOptions = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/outfits/options`);
      setOptions(res.data);
    } catch (e) {
      console.error("Failed to load options", e);
    }
  };

  const loadHistory = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/outfits/mine?limit=10`, {
        withCredentials: true,
      });
      setHistory(res.data.outfits || []);
    } catch (e) {
      console.error("Failed to load history", e);
    }
  };

  const loadTrending = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/outfits/trending?limit=5`);
      setTrending(res.data.trending || []);
    } catch (e) {
      // optional
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setResult(null);
    try {
      const res = await axios.post(
        `${BACKEND_URL}/api/outfits/generate`,
        { ...form, include_affiliate_links: true },
        { withCredentials: true }
      );
      setResult(res.data);
      toast.success("Outfit generated!");
      loadHistory();
    } catch (e) {
      console.error(e);
      const msg = e?.response?.data?.detail || "Failed to generate outfit";
      toast.error(msg);
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async (outfitId) => {
    try {
      await axios.post(
        `${BACKEND_URL}/api/outfits/${outfitId}/save`,
        {},
        { withCredentials: true }
      );
      toast.success("Saved to your collection");
      loadHistory();
    } catch (e) {
      toast.error("Failed to save outfit");
    }
  };

  const trackClick = (linkId) => {
    window.open(`${BACKEND_URL}/api/affiliate/track/${linkId}`, "_blank");
  };

  return (
    <div className="min-h-screen bg-white" data-testid="outfit-generator-page">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-100 rounded-full"
            data-testid="back-btn"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            <Wand2 className="w-5 h-5 text-rose-600" />
            AI Outfit Studio
          </h1>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Form column */}
        <div className="lg:col-span-2 space-y-4 bg-gray-50 p-5 rounded-2xl border border-gray-200">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-rose-600" />
            <h2 className="font-medium">Tell us about the look</h2>
          </div>

          <div className="space-y-3">
            <div>
              <Label>Occasion</Label>
              <Select
                value={form.occasion}
                onValueChange={(v) => setForm({ ...form, occasion: v })}
              >
                <SelectTrigger data-testid="select-occasion">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {options.occasions.map((o) => (
                    <SelectItem key={o} value={o}>
                      {o}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Style</Label>
              <Select
                value={form.style}
                onValueChange={(v) => setForm({ ...form, style: v })}
              >
                <SelectTrigger data-testid="select-style">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {options.styles.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Season</Label>
              <Select
                value={form.season}
                onValueChange={(v) => setForm({ ...form, season: v })}
              >
                <SelectTrigger data-testid="select-season">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {options.seasons.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>Budget (optional)</Label>
              <Input
                placeholder="e.g. under €150, premium..."
                value={form.budget}
                onChange={(e) => setForm({ ...form, budget: e.target.value })}
                data-testid="input-budget"
              />
            </div>

            <div>
              <Label>Colors (optional)</Label>
              <Input
                placeholder="e.g. earth tones, pastels"
                value={form.color_preference}
                onChange={(e) =>
                  setForm({ ...form, color_preference: e.target.value })
                }
                data-testid="input-color"
              />
            </div>

            <div>
              <Label>Anything else?</Label>
              <Textarea
                placeholder="Inspiration, vibe, must-have piece..."
                rows={3}
                value={form.additional_notes}
                onChange={(e) =>
                  setForm({ ...form, additional_notes: e.target.value })
                }
                data-testid="input-notes"
              />
            </div>

            <Button
              className="w-full bg-rose-600 hover:bg-rose-700"
              disabled={generating}
              onClick={handleGenerate}
              data-testid="generate-outfit-btn"
            >
              {generating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Curating...
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4 mr-2" /> Generate Outfit
                </>
              )}
            </Button>
          </div>

          {trending.length > 0 && (
            <div className="pt-4 border-t border-gray-200">
              <div className="flex items-center gap-1 text-sm text-gray-600 mb-2">
                <TrendingUp className="w-4 h-4" /> Trending styles
              </div>
              <div className="flex flex-wrap gap-2">
                {trending.map((t) => (
                  <Badge
                    key={t.style}
                    variant="outline"
                    className="cursor-pointer"
                    onClick={() => setForm({ ...form, style: t.style })}
                    data-testid={`trending-${t.style}`}
                  >
                    {t.style} · {t.popularity}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Result column */}
        <div className="lg:col-span-3 space-y-4">
          {result ? (
            <OutfitResultCard
              data={result}
              onSave={() => handleSave(result.outfit_id)}
              onTrack={trackClick}
            />
          ) : (
            <EmptyState />
          )}

          {history.length > 0 && (
            <div className="pt-4">
              <h3 className="text-sm font-medium text-gray-600 mb-2">
                Recent generations
              </h3>
              <div className="space-y-2">
                {history.map((h) => (
                  <div
                    key={h.outfit_id}
                    className="p-3 bg-white border border-gray-200 rounded-xl flex items-center justify-between"
                    data-testid={`history-${h.outfit_id}`}
                  >
                    <div>
                      <div className="font-medium text-sm">
                        {h.generated_outfit?.outfit_name || "Outfit"}
                      </div>
                      <div className="text-xs text-gray-500">
                        {h.request?.style} · {h.request?.occasion} · {h.request?.season}
                      </div>
                    </div>
                    {h.saved && (
                      <Badge variant="secondary">
                        <Bookmark className="w-3 h-3 mr-1" /> Saved
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="border-2 border-dashed border-gray-200 rounded-2xl p-12 text-center text-gray-500">
      <Wand2 className="w-10 h-10 mx-auto text-rose-200 mb-2" />
      <p className="font-medium">Your AI stylist is ready</p>
      <p className="text-sm">
        Fill in the details and tap <span className="text-rose-600">Generate Outfit</span>.
      </p>
    </div>
  );
}

function OutfitResultCard({ data, onSave, onTrack }) {
  const outfit = data.outfit || {};
  const items = outfit.items || [];
  const links = data.affiliate_links || [];

  // group links by item name
  const linksByItem = links.reduce((acc, l) => {
    const key = l.item || "general";
    if (!acc[key]) acc[key] = [];
    acc[key].push(l);
    return acc;
  }, {});

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-6" data-testid="outfit-result">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h2 className="text-2xl font-semibold" data-testid="outfit-name">
            {outfit.outfit_name || "Your Outfit"}
          </h2>
          <p className="text-gray-600 text-sm mt-1">{outfit.description}</p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={onSave}
          data-testid="save-outfit-btn"
        >
          <Bookmark className="w-4 h-4 mr-1" /> Save
        </Button>
      </div>

      {outfit.hashtags && outfit.hashtags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {outfit.hashtags.map((tag) => (
            <span key={tag} className="text-xs text-rose-600">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="space-y-3">
        {items.map((item, idx) => (
          <div
            key={idx}
            className="border border-gray-100 rounded-xl p-3"
            data-testid={`outfit-item-${idx}`}
          >
            <div className="flex items-start gap-2">
              <Tag className="w-4 h-4 text-rose-500 mt-0.5" />
              <div className="flex-1">
                <div className="font-medium">
                  {item.item}{" "}
                  <span className="text-xs text-gray-500">({item.category})</span>
                </div>
                {item.color && (
                  <div className="text-xs text-gray-500">Color: {item.color}</div>
                )}
                {item.style_tip && (
                  <div className="text-xs text-gray-600 mt-1">
                    {item.style_tip}
                  </div>
                )}
              </div>
              {item.price_range && (
                <Badge variant="outline" className="text-xs">
                  {item.price_range}
                </Badge>
              )}
            </div>

            {linksByItem[item.item] && linksByItem[item.item].length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {linksByItem[item.item].map((l) => (
                  <button
                    key={l.link_id}
                    onClick={() => onTrack(l.link_id)}
                    className="text-xs px-2 py-1 rounded-full bg-rose-50 text-rose-700 hover:bg-rose-100 inline-flex items-center gap-1"
                    data-testid={`affiliate-link-${l.link_id}`}
                  >
                    <ShoppingBag className="w-3 h-3" /> Shop at {l.retailer}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {outfit.styling_tips && outfit.styling_tips.length > 0 && (
        <div className="mt-4 p-3 bg-rose-50 rounded-xl">
          <div className="text-sm font-medium text-rose-800 mb-1">
            Styling tips
          </div>
          <ul className="text-sm text-rose-700 list-disc list-inside space-y-1">
            {outfit.styling_tips.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      {outfit.celebrity_inspiration && (
        <div className="mt-3 text-xs text-gray-500">
          Inspired by: {outfit.celebrity_inspiration}
        </div>
      )}
    </div>
  );
}
