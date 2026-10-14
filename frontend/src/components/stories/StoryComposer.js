import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProductTagsEditor, MAX_STORY_PRODUCTS, newProduct } from "@/components/stories/ProductTagsEditor";
import { apiErrorMessage } from "@/utils/apiError";
import { imageUrl } from "@/utils/media";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const opts = { withCredentials: true };

const cleanProducts = (products) =>
  products
    .filter((p) => p.name.trim() || p.url.trim())
    .map((p) => ({ name: p.name.trim(), url: p.url.trim(), price: p.price === "" ? null : parseFloat(p.price) }));

// source: { type: "file", file } | { type: "post", postId }
export const StoryComposer = ({ source, onClose, onPosted }) => {
  const [preview, setPreview] = useState(null);
  const [caption, setCaption] = useState("");
  const [products, setProducts] = useState([]);
  const [posting, setPosting] = useState(false);

  useEffect(() => {
    setCaption("");
    setProducts([]);
    setPreview(null);
    if (!source) return;
    if (source.type === "file") {
      const url = URL.createObjectURL(source.file);
      setPreview(url);
      return () => URL.revokeObjectURL(url);
    }
    axios.get(`${BACKEND_URL}/api/posts/${source.postId}`, opts).then(({ data }) => {
      setPreview(imageUrl(data.image_id));
      setProducts((data.products || []).slice(0, MAX_STORY_PRODUCTS).map((p) => newProduct(p.name || "", p.url || "")));
    }).catch(() => toast.error("Could not load post"));
  }, [source]);

  const post = async () => {
    const items = cleanProducts(products);
    if (items.some((p) => !p.name || !p.url)) return toast.error("Each product needs a name and a link");
    setPosting(true);
    try {
      const body = { caption: caption.trim() || null, products: items };
      if (source.type === "file") {
        const form = new FormData();
        form.append("file", source.file);
        const { data: up } = await axios.post(`${BACKEND_URL}/api/upload-image`, form, opts);
        await axios.post(`${BACKEND_URL}/api/stories`, { ...body, image_id: up.file_id }, opts);
      } else {
        await axios.post(`${BACKEND_URL}/api/stories/from-post/${source.postId}`, body, opts);
      }
      toast.success("Added to your story");
      onPosted();
    } catch (err) {
      toast.error(apiErrorMessage(err, "Could not post story"));
    } finally {
      setPosting(false);
    }
  };

  return (
    <Dialog open={!!source} onOpenChange={(v) => !v && !posting && onClose()}>
      <DialogContent data-testid="story-composer" className="sm:max-w-sm p-0 gap-0 overflow-hidden max-h-[92vh] flex flex-col">
        <DialogHeader className="px-5 pt-5 pb-3">
          <DialogTitle className="font-italiana text-3xl">New story</DialogTitle>
        </DialogHeader>
        <div className="overflow-y-auto">
          {preview && <img src={preview} alt="Story preview" data-testid="story-composer-preview" className="w-full aspect-[4/5] max-h-[40vh] object-cover bg-black" />}
          <div className="p-4 space-y-4">
            <Input data-testid="story-caption-input" value={caption} onChange={(e) => setCaption(e.target.value)} maxLength={200}
              placeholder="Add a caption (optional)" className="rounded-full font-manrope" />
            <ProductTagsEditor products={products} onChange={setProducts} />
          </div>
        </div>
        <div className="p-4 pt-0 space-y-2">
          <Button data-testid="story-post-btn" onClick={post} disabled={posting || !preview}
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
