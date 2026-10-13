import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, Heart, MessageCircle, UserPlus, Star, Send, Handshake, Wand2, SmilePlus } from "lucide-react";
import { timeAgo } from "@/utils/media";
import axios from "axios";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const POLL_MS = 30000;
const ICONS = { like: Heart, comment: MessageCircle, follow: UserPlus, star: Star, message: Send, collab: Handshake, outfit: Wand2, reaction: SmilePlus };

const linkFor = (n) => {
  if ((n.type === "message" || n.type === "reaction") && n.conversation_id) return `/chat/${n.conversation_id}`;
  if (n.post_id) return `/post/${n.post_id}`;
  if (n.actor_user_id) return `/profile/${n.actor_user_id}`;
  return null;
};

const NotificationItem = ({ n, onOpen }) => {
  const Icon = ICONS[n.type] || Bell;
  return (
    <button type="button" data-testid={`notification-item-${n.notification_id}`} onClick={() => onOpen(n)}
      className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors duration-200 hover:bg-gray-50 ${n.read ? "" : "bg-gray-50/70"}`}>
      <span className="mt-0.5 w-8 h-8 shrink-0 rounded-full bg-black text-white flex items-center justify-center">
        <Icon className="w-4 h-4" />
      </span>
      <span className="flex-1 min-w-0 font-manrope text-sm text-gray-800">
        <strong className="font-semibold">{n.actor_name || "Someone"}</strong> {n.preview}
        <span className="block text-xs text-gray-400 mt-0.5">{timeAgo(n.created_at)}</span>
      </span>
      {!n.read && <span className="mt-2 w-2 h-2 rounded-full bg-[#800020] shrink-0" />}
    </button>
  );
};

export const NotificationBell = () => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState(null);

  const pollCount = useCallback(() => {
    axios.get(`${BACKEND_URL}/api/notifications/unread-count`, { withCredentials: true })
      .then(({ data }) => setUnread(data.unread_count)).catch(() => {});
  }, []);

  useEffect(() => {
    pollCount();
    const id = setInterval(pollCount, POLL_MS);
    return () => clearInterval(id);
  }, [pollCount]);

  const onOpenChange = async (v) => {
    setOpen(v);
    if (!v) return;
    const { data } = await axios.get(`${BACKEND_URL}/api/notifications?limit=30`, { withCredentials: true });
    setItems(data.notifications);
    if (data.unread_count > 0) {
      await axios.post(`${BACKEND_URL}/api/notifications/mark-read`, {}, { withCredentials: true });
      setUnread(0);
    }
  };

  const openItem = (n) => {
    setOpen(false);
    const to = linkFor(n);
    if (to) navigate(to);
  };

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <Button data-testid="notification-bell-btn" variant="ghost" size="icon" className="rounded-full relative" title="Notifications">
          <Bell className="w-4 h-4" />
          {unread > 0 && (
            <span data-testid="notification-unread-badge"
              className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[#800020] text-white text-[10px] font-manrope font-bold flex items-center justify-center">
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[340px] max-w-[calc(100vw-24px)] p-0 overflow-hidden" data-testid="notification-panel">
        <div className="px-4 py-3 border-b font-italiana text-2xl text-black">Notifications</div>
        <div className="max-h-[420px] overflow-y-auto divide-y">
          {items === null ? (
            <div className="py-10 flex justify-center"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-black" /></div>
          ) : items.length === 0 ? (
            <p data-testid="notification-empty" className="py-10 text-center font-manrope text-sm text-gray-500">You're all caught up.</p>
          ) : (
            items.map((n) => <NotificationItem key={n.notification_id} n={n} onOpen={openItem} />)
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
};
