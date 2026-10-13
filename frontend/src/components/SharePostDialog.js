import { useEffect, useState } from "react";
import { Search, Check, Send, Loader2, CirclePlus } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/utils/apiError";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const MAX_RECIPIENTS = 10;
const picUrl = (p) => (!p ? undefined : p.startsWith("http") ? p : `${BACKEND_URL}${p}`);

const RecipientRow = ({ user, selected, onToggle }) => (
  <button type="button" data-testid={`share-recipient-${user.user_id}`} onClick={() => onToggle(user.user_id)}
    className="w-full flex items-center gap-3 px-2 py-2 rounded-xl text-left transition-colors duration-200 hover:bg-gray-50">
    <Avatar className="w-10 h-10">
      <AvatarImage src={picUrl(user.picture)} />
      <AvatarFallback className="bg-gray-200 text-sm">{user.name?.[0]?.toUpperCase() || "?"}</AvatarFallback>
    </Avatar>
    <span className="flex-1 min-w-0">
      <span className="block font-manrope text-sm font-semibold truncate">{user.name}</span>
      <span className="block font-manrope text-xs text-gray-400">{user.is_following ? "Following" : "Follows you"}</span>
    </span>
    <span className={`w-6 h-6 rounded-full border flex items-center justify-center transition-colors duration-200 ${selected ? "bg-black border-black" : "border-gray-300"}`}>
      {selected && <Check className="w-3.5 h-3.5 text-white" />}
    </span>
  </button>
);

export const SharePostDialog = ({ open, onOpenChange, postId }) => {
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState(null);
  const [selected, setSelected] = useState([]);
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);
  const [addingStory, setAddingStory] = useState(false);

  const addToStory = async () => {
    setAddingStory(true);
    try {
      await axios.post(`${BACKEND_URL}/api/stories/from-post/${postId}`, {}, { withCredentials: true });
      toast.success("Added to your story");
      close(false);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Could not add to story"));
    } finally {
      setAddingStory(false);
    }
  };

  useEffect(() => {
    const q = query.trim();
    if (!open || q.length === 1) return;
    const t = setTimeout(() => {
      axios.get(`${BACKEND_URL}/api/share/recipients`, { params: q.length >= 2 ? { q } : {}, withCredentials: true })
        .then(({ data }) => setUsers(data.users))
        .catch(() => setUsers([]));
    }, q ? 300 : 0);
    return () => clearTimeout(t);
  }, [open, query]);

  const toggle = (id) => setSelected((s) => {
    if (s.includes(id)) return s.filter((x) => x !== id);
    if (s.length >= MAX_RECIPIENTS) {
      toast.error(`You can send to up to ${MAX_RECIPIENTS} people at once`);
      return s;
    }
    return [...s, id];
  });

  const close = (v) => {
    onOpenChange(v);
    if (!v) { setSelected([]); setNote(""); setQuery(""); setUsers(null); }
  };

  const send = async () => {
    setSending(true);
    try {
      const { data } = await axios.post(`${BACKEND_URL}/api/posts/${postId}/share`,
        { recipient_ids: selected, note: note.trim() || null }, { withCredentials: true });
      toast.success(`Sent to ${data.shared} ${data.shared === 1 ? "person" : "people"}`);
      close(false);
    } catch (err) {
      toast.error(apiErrorMessage(err, "Could not share post"));
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent data-testid="share-post-dialog" className="sm:max-w-md p-0 gap-0 overflow-hidden">
        <DialogHeader className="px-5 pt-5 pb-3 border-b">
          <DialogTitle className="font-italiana text-3xl">Share</DialogTitle>
        </DialogHeader>
        <button type="button" data-testid="share-add-to-story-btn" onClick={addToStory} disabled={addingStory}
          className="mx-5 mt-3 flex items-center gap-3 rounded-2xl border border-gray-200 px-4 py-3 text-left transition-colors duration-200 hover:border-black disabled:opacity-50">
          <span className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#800020] via-[#C2185B] to-[#D4AF37] p-[2px]">
            <span className="w-full h-full rounded-full bg-white flex items-center justify-center">
              {addingStory ? <Loader2 className="w-4 h-4 animate-spin" /> : <CirclePlus className="w-5 h-5" />}
            </span>
          </span>
          <span className="font-manrope">
            <span className="block text-sm font-semibold">Add to your story</span>
            <span className="block text-xs text-gray-500">Visible to your followers for 24 hours</span>
          </span>
        </button>
        <div className="px-5 py-3 relative">
          <Search className="absolute left-9 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input data-testid="share-search-input" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="Search people" className="pl-10 rounded-full font-manrope" />
        </div>
        <div className="px-3 h-72 overflow-y-auto" data-testid="share-recipient-list">
          {users === null ? (
            <div className="h-full flex items-center justify-center"><Loader2 className="w-5 h-5 animate-spin" /></div>
          ) : users.length === 0 ? (
            <p data-testid="share-recipients-empty" className="pt-16 text-center font-manrope text-sm text-gray-500 px-6">
              {query.trim().length >= 2 ? "No people found." : "Follow people to share with them, or search by name."}
            </p>
          ) : (
            users.map((u) => <RecipientRow key={u.user_id} user={u} selected={selected.includes(u.user_id)} onToggle={toggle} />)
          )}
        </div>
        <div className="p-4 border-t space-y-3">
          <Input data-testid="share-note-input" value={note} onChange={(e) => setNote(e.target.value)} maxLength={500}
            placeholder="Write a message..." className="rounded-full font-manrope" />
          <Button data-testid="share-send-btn" onClick={send} disabled={!selected.length || sending}
            className="w-full h-12 rounded-full bg-black text-white hover:bg-gray-800 font-manrope">
            {sending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
            {selected.length > 1 ? `Send separately (${selected.length})` : "Send"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
