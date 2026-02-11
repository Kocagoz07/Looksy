import { useState, useEffect } from "react";
import { MessageSquare, Check, X, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function CollaborationHub({ userId, textColor = '#FFFFFF', bgColor = '#000000' }) {
  const [collaborations, setCollaborations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchCollaborations();
  }, []);

  const fetchCollaborations = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/collaborations/inbox`, { 
        withCredentials: true 
      });
      setCollaborations(response.data || []);
    } catch (err) {
      console.error("Error fetching collaborations:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async (messageId) => {
    try {
      await axios.post(`${BACKEND_URL}/api/collaborations/${messageId}/accept`, {}, { 
        withCredentials: true 
      });
      setCollaborations(collaborations.map(c => 
        c.message_id === messageId ? { ...c, status: 'accepted' } : c
      ));
      toast.success("Collaboration accepted!");
    } catch (err) {
      toast.error("Failed to accept");
    }
  };

  const handleDecline = async (messageId) => {
    try {
      await axios.post(`${BACKEND_URL}/api/collaborations/${messageId}/decline`, {}, { 
        withCredentials: true 
      });
      setCollaborations(collaborations.filter(c => c.message_id !== messageId));
      toast.success("Collaboration declined");
    } catch (err) {
      toast.error("Failed to decline");
    }
  };

  const pendingCount = collaborations.filter(c => !c.status || c.status === 'pending').length;
  const pendingCollabs = collaborations.filter(c => !c.status || c.status === 'pending');

  if (loading) {
    return null;
  }

  if (pendingCount === 0) {
    return null;
  }

  return (
    <div className="mb-6" data-testid="collaboration-section">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 rounded-xl transition-colors"
        style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
      >
        <div className="flex items-center gap-3">
          <MessageSquare className="w-5 h-5" style={{ color: textColor }} />
          <span className="font-manrope font-semibold" style={{ color: textColor }}>
            Collaboration Requests
          </span>
          <Badge className="bg-blue-500 text-white text-xs">{pendingCount}</Badge>
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5" style={{ color: textColor }} />
        ) : (
          <ChevronDown className="w-5 h-5" style={{ color: textColor }} />
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="mt-3 space-y-3">
          {pendingCollabs.map((collab) => (
            <div
              key={collab.message_id}
              className="p-4 rounded-xl"
              style={{ backgroundColor: 'rgba(255,255,255,0.08)' }}
              data-testid={`collab-item-${collab.message_id}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="font-manrope font-semibold text-sm mb-1" style={{ color: textColor }}>
                    {collab.from_user_name}
                  </p>
                  <p className="font-manrope text-sm opacity-80 mb-2" style={{ color: textColor }}>
                    {collab.subject}
                  </p>
                  <p className="font-manrope text-xs opacity-60 line-clamp-2" style={{ color: textColor }}>
                    {collab.message}
                  </p>
                </div>
                
                <div className="flex items-center gap-2 flex-shrink-0">
                  <Button
                    size="sm"
                    onClick={() => handleAccept(collab.message_id)}
                    className="rounded-full w-8 h-8 p-0 bg-green-600 hover:bg-green-700"
                    data-testid={`accept-btn-${collab.message_id}`}
                  >
                    <Check className="w-4 h-4 text-white" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDecline(collab.message_id)}
                    className="rounded-full w-8 h-8 p-0"
                    style={{ borderColor: textColor, color: textColor }}
                    data-testid={`decline-btn-${collab.message_id}`}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
