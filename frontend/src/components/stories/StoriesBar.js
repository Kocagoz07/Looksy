import { useCallback, useEffect, useRef, useState } from "react";
import { Plus } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { StoryViewer } from "@/components/stories/StoryViewer";
import { StoryComposer } from "@/components/stories/StoryComposer";
import { picUrl } from "@/utils/media";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const MAX_FILE_MB = 10;

const StoryRing = ({ name, picture, unseen, onClick, testId, badge }) => (
  <button type="button" data-testid={testId} onClick={onClick}
    className="flex flex-col items-center gap-1.5 w-[72px] shrink-0 group">
    <span className={`relative p-[2.5px] rounded-full transition-transform duration-200 group-hover:scale-105 ${
      unseen ? "bg-gradient-to-tr from-[#800020] via-[#C2185B] to-[#D4AF37]" : "bg-gray-300"}`}>
      <span className="block p-[2px] rounded-full bg-white">
        <Avatar className="w-14 h-14">
          <AvatarImage src={picUrl(picture)} className="object-cover" />
          <AvatarFallback className="bg-gray-200 text-gray-700 font-manrope">{name?.[0]?.toUpperCase() || "?"}</AvatarFallback>
        </Avatar>
      </span>
      {badge}
    </span>
    <span className="font-manrope text-[11px] max-w-full truncate">{name}</span>
  </button>
);

export const StoriesBar = ({ currentUser }) => {
  const [groups, setGroups] = useState([]);
  const [openAt, setOpenAt] = useState(null);
  const [file, setFile] = useState(null);
  const inputRef = useRef(null);

  const load = useCallback(() => {
    axios.get(`${BACKEND_URL}/api/stories/feed`, { withCredentials: true })
      .then(({ data }) => setGroups(data.groups)).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const mine = groups.find((gr) => gr.is_me);
  const others = groups.filter((gr) => !gr.is_me);

  const pickFile = (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    if (!f.type.startsWith("image/")) return toast.error("Please choose an image");
    if (f.size > MAX_FILE_MB * 1024 * 1024) return toast.error(`Image must be under ${MAX_FILE_MB}MB`);
    setFile(f);
  };

  const addBadge = (
    <span role="button" data-testid="story-add-btn" onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
      className="absolute bottom-0 right-0 w-5 h-5 rounded-full bg-black text-white border-2 border-white flex items-center justify-center">
      <Plus className="w-3 h-3" />
    </span>
  );

  return (
    <section data-testid="stories-bar" className="mb-8 -mx-4 px-4 flex gap-3 overflow-x-auto pb-2 [scrollbar-width:none]">
      <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={pickFile} data-testid="story-file-input" />
      <StoryRing testId="story-ring-me" name="Your story" picture={currentUser?.picture} unseen={!!mine} badge={addBadge}
        onClick={() => (mine ? setOpenAt(groups.indexOf(mine)) : inputRef.current?.click())} />
      {others.map((gr) => (
        <StoryRing key={gr.user_id} testId={`story-ring-${gr.user_id}`} name={gr.name} picture={gr.picture}
          unseen={gr.has_unseen} onClick={() => setOpenAt(groups.indexOf(gr))} />
      ))}
      {openAt !== null && (
        <StoryViewer groups={groups} startGroup={openAt} onClose={() => { setOpenAt(null); load(); }} />
      )}
      <StoryComposer file={file} onClose={() => setFile(null)} onPosted={() => { setFile(null); load(); }} />
    </section>
  );
};
