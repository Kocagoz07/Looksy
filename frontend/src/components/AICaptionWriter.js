import { useState } from "react";
import { Sparkles, RefreshCw, Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { streamCaptions, fileToResizedBase64 } from "@/utils/captionStream";

const TONES = ["chic", "playful", "minimal", "bold", "luxury"];

const Pill = ({ active, onClick, children, testId, caps = true }) => (
  <button
    type="button"
    data-testid={testId}
    onClick={onClick}
    className={`px-3 py-1.5 rounded-full text-xs font-manrope ${caps ? "capitalize" : ""} border transition-colors duration-200 ${
      active ? "bg-black text-white border-black" : "bg-white text-gray-700 border-gray-200 hover:border-black"
    }`}
  >
    {children}
  </button>
);

const CaptionOption = ({ text, index, selected, onSelect }) => (
  <button
    type="button"
    data-testid={`ai-caption-option-${index}`}
    onClick={onSelect}
    className={`w-full text-left p-3 rounded-xl border font-manrope text-sm transition-[border-color,background-color,transform] duration-200 hover:-translate-y-0.5 ${
      selected ? "border-black bg-gray-50" : "border-gray-200 bg-white hover:border-gray-400"
    }`}
  >
    <span className="flex items-start gap-2">
      <span className={`mt-0.5 w-4 h-4 shrink-0 rounded-full border flex items-center justify-center ${selected ? "bg-black border-black" : "border-gray-300"}`}>
        {selected && <Check className="w-3 h-3 text-white" />}
      </span>
      {text}
    </span>
  </button>
);

export const AICaptionWriter = ({ context, imageFile, onApply }) => {
  const [tone, setTone] = useState("chic");
  const [streaming, setStreaming] = useState(false);
  const [liveText, setLiveText] = useState("");
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(0);
  const [tags, setTags] = useState([]);

  const generate = async () => {
    setStreaming(true);
    setResult(null);
    setLiveText("");
    try {
      const image_base64 = imageFile ? await fileToResizedBase64(imageFile) : null;
      await streamCaptions({ ...context, tone, image_base64 }, {
        onDelta: (chunk) => setLiveText((t) => t + chunk),
        onDone: (ev) => {
          if (!ev.captions?.length) throw new Error("No captions returned. Please try again.");
          setResult(ev);
          setSelected(0);
          setTags(ev.hashtags || []);
        },
      });
    } catch (err) {
      toast.error(err.message || "Caption writer failed");
    } finally {
      setStreaming(false);
    }
  };

  const toggleTag = (tag) => setTags((t) => (t.includes(tag) ? t.filter((x) => x !== tag) : [...t, tag]));

  const apply = () => {
    onApply([result.captions[selected], tags.join(" ")].filter(Boolean).join("\n\n"));
    toast.success("Caption added");
  };

  return (
    <div data-testid="ai-caption-writer" className="mt-3 rounded-2xl border border-gray-200 p-4 space-y-4 bg-white">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          <span className="font-manrope text-sm font-semibold">AI Caption Writer</span>
          <span className="font-manrope text-[10px] uppercase tracking-widest text-gray-400">Claude</span>
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {TONES.map((t) => (
            <Pill key={t} testId={`ai-caption-tone-${t}`} active={tone === t} onClick={() => setTone(t)}>{t}</Pill>
          ))}
        </div>
      </div>

      {streaming && (
        <pre data-testid="ai-caption-live" className="whitespace-pre-wrap font-manrope text-xs text-gray-500 bg-gray-50 rounded-xl p-3 max-h-40 overflow-auto">
          {liveText || "Styling your words..."}
        </pre>
      )}

      {result && !streaming && (
        <div className="space-y-3" data-testid="ai-caption-results">
          {result.captions.map((c, i) => (
            <CaptionOption key={i} index={i} text={c} selected={selected === i} onSelect={() => setSelected(i)} />
          ))}
          <div className="flex flex-wrap gap-1.5" data-testid="ai-hashtag-list">
            {result.hashtags.map((tag) => (
              <Pill key={tag} caps={false} testId={`ai-hashtag-${tag.slice(1)}`} active={tags.includes(tag)} onClick={() => toggleTag(tag)}>{tag}</Pill>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <Button type="button" data-testid="ai-caption-generate-btn" onClick={generate} disabled={streaming}
          variant={result ? "outline" : "default"} className="rounded-full font-manrope">
          {streaming ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : result ? <RefreshCw className="w-4 h-4 mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />}
          {streaming ? "Writing..." : result ? "Regenerate" : "Write with AI"}
        </Button>
        {result && !streaming && (
          <Button type="button" data-testid="ai-caption-apply-btn" onClick={apply} className="rounded-full font-manrope bg-black text-white hover:bg-gray-800">
            Use this caption
          </Button>
        )}
      </div>
    </div>
  );
};
