import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/utils/apiError";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const StoryComposer = ({ file, onClose, onPosted }) => {
  const [preview, setPreview] = useState(null);
  const [caption, setCaption] = useState("");
  const [posting, setPosting] = useState(false);

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    setCaption("");
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const post = async () => {
    setPosting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data: up } = await axios.post(`${BACKEND_URL}/api/upload-image`, form, { withCredentials: true });
      await axios.post(`${BACKEND_URL}/api/stories`, { image_id: up.file_id, caption: caption.trim() || null }, { withCredentials: true });
      toast.success("Added to your story");
      onPosted();
    } catch (err) {
      toast.error(apiErrorMessage(err, "Could not post story"));
    } finally {
      setPosting(false);
    }
  };

  return (
    <Dialog open={!!file} onOpenChange={(v) => !v && !posting && onClose()}>
      <DialogContent data-testid="story-composer" className="sm:max-w-sm p-0 gap-0 overflow-hidden">
        <DialogHeader className="px-5 pt-5 pb-3">
          <DialogTitle className="font-italiana text-3xl">New story</DialogTitle>
        </DialogHeader>
        {preview && <img src={preview} alt="Story preview" data-testid="story-composer-preview" className="w-full aspect-[9/16] max-h-[55vh] object-cover bg-black" />}
        <div className="p-4 space-y-3">
          <Input data-testid="story-caption-input" value={caption} onChange={(e) => setCaption(e.target.value)} maxLength={200}
            placeholder="Add a caption (optional)" className="rounded-full font-manrope" />
          <Button data-testid="story-post-btn" onClick={post} disabled={posting}
            className="w-full h-12 rounded-full bg-black text-white hover:bg-gray-800 font-manrope">
            {posting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {posting ? "Posting..." : "Share to story"}
          </Button>
          <p className="font-manrope text-xs text-center text-gray-400">Visible to your followers for 24 hours</p>
        </div>
      </DialogContent>
    </Dialog>
  );
};
