import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessageSquare } from "lucide-react";
import axios from "axios";
import { Button } from "@/components/ui/button";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const POLL_MS = 30000;

export const InboxButton = () => {
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    const poll = () => axios.get(`${BACKEND_URL}/api/chat/unread-count`, { withCredentials: true })
      .then(({ data }) => setUnread(data.unread_count)).catch(() => {});
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <Button data-testid="inbox-btn" onClick={() => navigate("/chat")} variant="ghost" size="icon" className="rounded-full relative" title="Messages">
      <MessageSquare className="w-4 h-4" />
      {unread > 0 && (
        <span data-testid="inbox-unread-badge"
          className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[#800020] text-white text-[10px] font-manrope font-bold flex items-center justify-center">
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </Button>
  );
};
