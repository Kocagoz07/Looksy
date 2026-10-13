import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { X, Eye, Trash2, ExternalLink } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { StoryViewersSheet } from "@/components/stories/StoryViewersSheet";
import { picUrl, imageUrl, timeAgo } from "@/utils/media";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const DURATION_MS = 5000;
const TICK_MS = 50;
const HOLD_MS = 220;

const firstUnseen = (group) => Math.max(0, group.stories.findIndex((s) => !s.seen));

const ProgressBars = ({ count, index, progress }) => (
  <div className="flex gap-1">
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="h-0.5 flex-1 rounded-full bg-white/30 overflow-hidden">
        <div className="h-full bg-white" style={{ width: `${i < index ? 100 : i === index ? progress * 100 : 0}%` }} />
      </div>
    ))}
  </div>
);

export const StoryViewer = ({ groups, startGroup, onClose }) => {
  const navigate = useNavigate();
  const [g, setG] = useState(startGroup);
  const [i, setI] = useState(() => firstUnseen(groups[startGroup]));
  const [progress, setProgress] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [paused, setPaused] = useState(false);
  const [viewersOpen, setViewersOpen] = useState(false);
  const downAt = useRef(0);

  const group = groups[g];
  const story = group?.stories[i];

  const next = useCallback(() => {
    if (i < group.stories.length - 1) setI(i + 1);
    else if (g < groups.length - 1) { setG(g + 1); setI(firstUnseen(groups[g + 1])); }
    else onClose();
  }, [g, i, group, groups, onClose]);

  const prev = useCallback(() => {
    if (i > 0) setI(i - 1);
    else if (g > 0) { setG(g - 1); setI(0); }
    else setProgress(0);
  }, [g, i]);

  useEffect(() => {
    setProgress(0);
    setLoaded(false);
    if (story && !group.is_me && !story.seen) {
      story.seen = true;
      axios.post(`${BACKEND_URL}/api/stories/${story.story_id}/view`, {}, { withCredentials: true }).catch(() => {});
    }
  }, [story, group]);

  useEffect(() => {
    if (!loaded || paused || viewersOpen) return;
    const id = setInterval(() => setProgress((p) => p + TICK_MS / DURATION_MS), TICK_MS);
    return () => clearInterval(id);
  }, [loaded, paused, viewersOpen, story]);

  useEffect(() => {
    if (progress < 1) return;
    setProgress(0);
    next();
  }, [progress, next]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, prev, onClose]);

  const onPointerDown = () => { downAt.current = Date.now(); setPaused(true); };
  const onPointerUp = (e) => {
    setPaused(false);
    if (Date.now() - downAt.current > HOLD_MS) return;
    const { left, width } = e.currentTarget.getBoundingClientRect();
    if (e.clientX - left < width / 3) prev(); else next();
  };

  const remove = async () => {
    try {
      await axios.delete(`${BACKEND_URL}/api/stories/${story.story_id}`, { withCredentials: true });
      toast.success("Story deleted");
      onClose();
    } catch {
      toast.error("Could not delete story");
    }
  };

  if (!story) return null;

  return (
    <div data-testid="story-viewer" className="fixed inset-0 z-[100] bg-black flex items-center justify-center">
      <div className="relative w-full h-full sm:max-w-[420px] sm:h-[92vh] sm:rounded-2xl overflow-hidden bg-neutral-900 select-none">
        <img key={story.story_id} src={imageUrl(story.image_id)} alt="Story" draggable={false} onLoad={() => setLoaded(true)}
          data-testid={`story-image-${story.story_id}`} className="absolute inset-0 w-full h-full object-contain" />
        <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-black/60 to-transparent pointer-events-none" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black/70 to-transparent pointer-events-none" />

        <div data-testid="story-tap-zone" className="absolute inset-0 z-10" onPointerDown={onPointerDown} onPointerUp={onPointerUp}
          onPointerLeave={() => setPaused(false)} onContextMenu={(e) => e.preventDefault()} />

        <div className="absolute inset-x-0 top-0 z-20 p-3 space-y-3">
          <ProgressBars count={group.stories.length} index={i} progress={progress} />
          <div className="flex items-center gap-3 text-white">
            <Avatar className="w-8 h-8 ring-1 ring-white/50">
              <AvatarImage src={picUrl(group.picture)} />
              <AvatarFallback className="bg-gray-700 text-xs text-white">{group.name?.[0]?.toUpperCase() || "?"}</AvatarFallback>
            </Avatar>
            <span className="font-manrope text-sm font-semibold" data-testid="story-owner-name">{group.is_me ? "Your story" : group.name}</span>
            <span className="font-manrope text-xs text-white/60">{timeAgo(story.created_at)}</span>
            <button data-testid="story-close-btn" onClick={onClose} className="ml-auto p-1 rounded-full hover:bg-white/10"><X className="w-6 h-6" /></button>
          </div>
        </div>

        <div className="absolute inset-x-0 bottom-0 z-20 p-4 space-y-3 text-white">
          {story.caption && <p data-testid="story-caption" className="font-manrope text-base text-center">{story.caption}</p>}
          <div className="flex items-center gap-2">
            {story.shared_post && (
              <button data-testid="story-view-post-btn" onClick={() => navigate(`/post/${story.shared_post.post_id}`)}
                className="flex items-center gap-2 rounded-full bg-white/15 backdrop-blur-md px-4 py-2 font-manrope text-xs hover:bg-white/25 transition-colors">
                <ExternalLink className="w-3.5 h-3.5" /> View post{story.shared_post.author_name ? ` by ${story.shared_post.author_name}` : ""}
              </button>
            )}
            {group.is_me && (
              <>
                <button data-testid="story-seen-by-btn" onClick={() => setViewersOpen(true)}
                  className="flex items-center gap-2 rounded-full bg-white/15 backdrop-blur-md px-4 py-2 font-manrope text-xs hover:bg-white/25 transition-colors">
                  <Eye className="w-3.5 h-3.5" /> Seen by {story.view_count ?? 0}
                </button>
                <button data-testid="story-delete-btn" onClick={remove} title="Delete story"
                  className="ml-auto rounded-full bg-white/15 backdrop-blur-md p-2 hover:bg-red-500/70 transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>

        {viewersOpen && <StoryViewersSheet storyId={story.story_id} onClose={() => setViewersOpen(false)} />}
      </div>
    </div>
  );
};
