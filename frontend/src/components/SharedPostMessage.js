import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { imageUrl } from "@/utils/media";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const EMOJIS = ["❤️", "😍", "🔥", "😂", "😮", "👏"];
const LONG_PRESS_MS = 500;
const DOUBLE_TAP_MS = 260;

const ReactionPicker = ({ onPick, onClose, mine }) => (
  <>
    <div className="fixed inset-0 z-40" onClick={onClose} />
    <div data-testid="reaction-picker"
      className="absolute -top-12 left-0 z-50 flex gap-1 rounded-full bg-white shadow-xl border border-gray-100 px-2 py-1.5 animate-in zoom-in-90 fade-in duration-150">
      {EMOJIS.map((e) => (
        <button key={e} type="button" data-testid={`reaction-option-${EMOJIS.indexOf(e)}`} onClick={() => onPick(e)}
          className={`w-8 h-8 rounded-full text-lg leading-none transition-transform duration-150 hover:scale-125 ${mine === e ? "bg-gray-100" : ""}`}>
          {e}
        </button>
      ))}
    </div>
  </>
);

const ReactionSummary = ({ reactions, currentUserId, messageId }) => {
  if (!reactions.length) return null;
  const counts = reactions.reduce((acc, r) => ({ ...acc, [r.emoji]: (acc[r.emoji] || 0) + 1 }), {});
  const mine = reactions.find((r) => r.user_id === currentUserId)?.emoji;
  return (
    <div data-testid={`reaction-summary-${messageId}`} className="flex gap-1 flex-wrap">
      {Object.entries(counts).map(([emoji, n]) => (
        <span key={emoji} className={`px-2 py-0.5 rounded-full text-xs bg-white text-gray-800 border ${mine === emoji ? "border-black" : "border-gray-200"}`}>
          {emoji}{n > 1 ? ` ${n}` : ""}
        </span>
      ))}
    </div>
  );
};

const SharedPostCard = ({ message, currentUserId }) => {
  const navigate = useNavigate();
  const shared = message.shared_post;
  const [reactions, setReactions] = useState(message.reactions || []);
  const [picker, setPicker] = useState(false);
  const [burst, setBurst] = useState(0);
  const pressTimer = useRef(null);
  const tapTimer = useRef(null);
  const longPressed = useRef(false);
  const mine = reactions.find((r) => r.user_id === currentUserId)?.emoji;

  useEffect(() => { setReactions(message.reactions || []); }, [message.reactions]);
  useEffect(() => () => { clearTimeout(pressTimer.current); clearTimeout(tapTimer.current); }, []);

  const react = async (emoji) => {
    setPicker(false);
    try {
      const { data } = await axios.post(`${BACKEND_URL}/api/chat/messages/${message.message_id}/react`, { emoji }, { withCredentials: true });
      setReactions(data.reactions);
    } catch {
      toast.error("Could not send reaction");
    }
  };

  const startPress = () => {
    longPressed.current = false;
    pressTimer.current = setTimeout(() => { longPressed.current = true; setPicker(true); }, LONG_PRESS_MS);
  };
  const endPress = () => clearTimeout(pressTimer.current);

  const onClick = () => {
    if (longPressed.current) { longPressed.current = false; return; }
    if (tapTimer.current) {
      clearTimeout(tapTimer.current);
      tapTimer.current = null;
      setBurst((b) => b + 1);
      if (mine !== "❤️") react("❤️");
      return;
    }
    tapTimer.current = setTimeout(() => { tapTimer.current = null; navigate(`/post/${shared.post_id}`); }, DOUBLE_TAP_MS);
  };

  return (
    <div className="relative space-y-1.5">
      {picker && <ReactionPicker mine={mine} onPick={react} onClose={() => setPicker(false)} />}
      <button type="button" data-testid={`shared-post-card-${shared.post_id}`} onClick={onClick}
        onPointerDown={startPress} onPointerUp={endPress} onPointerLeave={endPress} onContextMenu={(e) => e.preventDefault()}
        className="relative block w-56 max-w-full text-left rounded-xl overflow-hidden bg-white text-gray-900 border border-gray-200 select-none transition-transform duration-200 hover:-translate-y-0.5">
        <div className="px-3 py-2 font-manrope text-xs font-semibold truncate">{shared.author_name || "Looksy creator"}</div>
        <img src={imageUrl(shared.image_id)} alt="Shared post" draggable={false} className="w-full aspect-square object-cover" />
        {shared.caption && <p className="px-3 py-2 font-manrope text-xs text-gray-600 line-clamp-2">{shared.caption}</p>}
        {burst > 0 && (
          <span key={burst} data-testid="reaction-heart-burst" className="looksy-heart-pop absolute inset-0 flex items-center justify-center text-6xl pointer-events-none">❤️</span>
        )}
      </button>
      <ReactionSummary reactions={reactions} currentUserId={currentUserId} messageId={message.message_id} />
    </div>
  );
};

export const MessageContent = ({ message, currentUserId }) => {
  const shared = message.shared_post;
  if (!shared) return <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>;
  return (
    <div className="space-y-2">
      <SharedPostCard message={message} currentUserId={currentUserId} />
      {shared.has_note && <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>}
    </div>
  );
};
