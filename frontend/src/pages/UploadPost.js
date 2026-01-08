import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Upload, Plus, X, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function UploadPost() {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [caption, setCaption] = useState("");
  const [music, setMusic] = useState("");
  const [location, setLocation] = useState("");
  const [venue, setVenue] = useState("");
  const [totalPrice, setTotalPrice] = useState("");
  const [products, setProducts] = useState([]);
  const [newProduct, setNewProduct] = useState({ name: "", url: "" });

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        toast.error("Please select an image file");
        return;
      }
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleDeleteImage = () => {
    setImageFile(null);
    setImagePreview(null);
    toast.success("Image removed");
  };

  const addProduct = () => {
    if (newProduct.name && newProduct.url) {
      setProducts([...products, newProduct]);
      setNewProduct({ name: "", url: "" });
      toast.success("Product added");
    } else {
      toast.error("Please fill both product name and URL");
    }
  };

  const removeProduct = (index) => {
    setProducts(products.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!imageFile) {
      toast.error("Please select an image");
      return;
    }

    setUploading(true);

    try {
      // Upload image first
      const formData = new FormData();
      formData.append('file', imageFile);
      
      const imageResponse = await axios.post(
        `${BACKEND_URL}/api/upload-image`,
        formData,
        { 
          withCredentials: true,
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );
      
      const imageId = imageResponse.data.file_id;

      // Create post
      const postData = {
        caption: caption || null,
        music: music || null,
        location: location || null,
        venue: venue || null,
        total_price: totalPrice ? parseFloat(totalPrice) : null,
        products: products
      };

      await axios.post(
        `${BACKEND_URL}/api/posts?image_id=${imageId}`,
        postData,
        { withCredentials: true }
      );

      toast.success("Post uploaded successfully!");
      navigate("/dashboard");
    } catch (err) {
      console.error("Upload error:", err);
      toast.error("Failed to upload post");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b px-4 py-4 flex items-center gap-4">
        <Button
          data-testid="back-btn"
          onClick={() => navigate(-1)}
          variant="ghost"
          size="icon"
          className="rounded-full"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <h1 className="font-playfair text-2xl font-bold">Upload Post</h1>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Image Upload */}
          <div>
            <label className="font-manrope text-sm font-semibold mb-2 block">Image (1080x1080)</label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
              {imagePreview ? (
                <div className="space-y-4">
                  <div className="relative inline-block">
                    <img
                      src={imagePreview}
                      alt="Preview"
                      className="max-w-sm mx-auto rounded-lg"
                    />
                    <Button
                      data-testid="delete-image-btn"
                      type="button"
                      variant="destructive"
                      size="icon"
                      onClick={handleDeleteImage}
                      className="absolute top-2 right-2 rounded-full bg-red-500 hover:bg-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setImageFile(null);
                      setImagePreview(null);
                    }}
                  >
                    Change Image
                  </Button>
                </div>
              ) : (
                <label className="cursor-pointer">
                  <input
                    data-testid="image-input"
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                    className="hidden"
                  />
                  <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p className="font-manrope text-gray-600">Click to upload image</p>
                </label>
              )}
            </div>
          </div>

          {/* Caption */}
          <div>
            <label className="font-manrope text-sm font-semibold mb-2 block">Caption</label>
            <Textarea
              data-testid="caption-input"
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Write a caption for your post..."
              className="font-manrope"
              rows={3}
            />
          </div>

          {/* Music Link */}
          <div>
            <label className="font-manrope text-sm font-semibold mb-2 block">Music Link (Optional)</label>
            <Input
              data-testid="music-input"
              value={music}
              onChange={(e) => setMusic(e.target.value)}
              placeholder="Spotify or YouTube link"
              className="font-manrope"
            />
          </div>

          {/* Location & Venue */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="font-manrope text-sm font-semibold mb-2 block">Location (Optional)</label>
              <Input
                data-testid="location-input"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g., New York"
                className="font-manrope"
              />
            </div>
            <div>
              <label className="font-manrope text-sm font-semibold mb-2 block">Venue (Optional)</label>
              <Input
                data-testid="venue-input"
                value={venue}
                onChange={(e) => setVenue(e.target.value)}
                placeholder="e.g., Fashion Week"
                className="font-manrope"
              />
            </div>
          </div>

          {/* Total Price */}
          <div>
            <label className="font-manrope text-sm font-semibold mb-2 block">Total Outfit Price (Optional)</label>
            <Input
              data-testid="price-input"
              type="number"
              step="0.01"
              value={totalPrice}
              onChange={(e) => setTotalPrice(e.target.value)}
              placeholder="0.00"
              className="font-manrope"
            />
          </div>

          {/* Products */}
          <div>
            <label className="font-manrope text-sm font-semibold mb-2 block">Product Links</label>
            
            {/* Added Products */}
            {products.length > 0 && (
              <div className="space-y-2 mb-4">
                {products.map((product, index) => (
                  <div key={index} className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                    <div className="flex-1">
                      <p className="font-manrope text-sm font-semibold">{product.name}</p>
                      <p className="font-manrope text-xs text-gray-500 truncate">{product.url}</p>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeProduct(index)}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {/* Add Product Form */}
            <div className="border rounded-lg p-4 space-y-3">
              <Input
                data-testid="product-name-input"
                value={newProduct.name}
                onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                placeholder="Product name"
                className="font-manrope"
              />
              <Input
                data-testid="product-url-input"
                value={newProduct.url}
                onChange={(e) => setNewProduct({ ...newProduct, url: e.target.value })}
                placeholder="Product URL"
                className="font-manrope"
              />
              <Button
                data-testid="add-product-btn"
                type="button"
                onClick={addProduct}
                variant="outline"
                className="w-full font-manrope"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Product
              </Button>
            </div>
          </div>

          {/* Submit */}
          <Button
            data-testid="submit-post-btn"
            type="submit"
            disabled={uploading || !imageFile}
            className="w-full bg-black text-white hover:bg-gray-800 py-6 font-manrope font-semibold rounded-full"
          >
            {uploading ? "Uploading..." : "Post"}
          </Button>
        </form>
      </main>
    </div>
  );
}