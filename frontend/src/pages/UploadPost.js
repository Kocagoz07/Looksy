import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Upload, Plus, X, Trash2, AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import LocationPicker from "@/components/LocationPicker";
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
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [venue, setVenue] = useState("");
  const [totalPrice, setTotalPrice] = useState("");
  const [products, setProducts] = useState([]);
  const [newProduct, setNewProduct] = useState({ name: "", url: "" });
  const [checkingBrand, setCheckingBrand] = useState(false);
  const [brandCheckResult, setBrandCheckResult] = useState(null);

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

  // Check product title for brand names
  const checkProductBrand = async (title) => {
    setCheckingBrand(true);
    setBrandCheckResult(null);
    
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/products/check-brand`,
        { product_title: title },
        { withCredentials: true }
      );
      
      setBrandCheckResult(response.data);
      return response.data;
    } catch (err) {
      console.error("Brand check error:", err);
      toast.error("Failed to check product title");
      return null;
    } finally {
      setCheckingBrand(false);
    }
  };

  const addProduct = async () => {
    if (!newProduct.name || !newProduct.url) {
      toast.error("Please fill both product name and URL");
      return;
    }

    // Check for brand names before adding
    const brandResult = await checkProductBrand(newProduct.name);
    
    if (!brandResult) {
      return; // Error occurred during check
    }
    
    if (brandResult.status === "REJECTED") {
      // Show detailed error with detected brands
      toast.error(
        <div className="space-y-2">
          <p className="font-semibold">Brand name detected!</p>
          <p className="text-sm">Detected: {brandResult.detected_terms.join(", ")}</p>
          <p className="text-sm text-gray-300">Use generic descriptions like: "{brandResult.clean_title}"</p>
        </div>,
        { duration: 6000 }
      );
      return;
    }
    
    // Brand check passed - add product
    setProducts([...products, newProduct]);
    setNewProduct({ name: "", url: "" });
    setBrandCheckResult(null);
    toast.success("Product added");
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

      const postResponse = await axios.post(
        `${BACKEND_URL}/api/posts?image_id=${imageId}`,
        postData,
        { withCredentials: true }
      );

      // If a location was selected, add it to the post
      if (selectedLocation) {
        try {
          await axios.post(
            `${BACKEND_URL}/api/posts/${postResponse.data.post_id}/location`,
            { location_id: selectedLocation.location_id },
            { withCredentials: true }
          );
        } catch (locErr) {
          console.warn("Failed to add location to post:", locErr);
        }
      }

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
            <label className="font-manrope text-sm font-semibold mb-2 block">
              Photo <span className="text-gray-500 font-normal">(1:1 square, 1080×1080px recommended)</span>
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
              {imagePreview ? (
                <div className="space-y-4">
                  <div className="relative inline-block">
                    {/* Square preview container */}
                    <div className="w-80 h-80 mx-auto rounded-lg overflow-hidden bg-gray-100">
                      <img
                        src={imagePreview}
                        alt="Preview"
                        className="w-full h-full object-cover object-center"
                      />
                    </div>
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
                  <p className="text-xs text-gray-500 font-manrope">
                    Image will be cropped to square (1:1) format
                  </p>
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
                  {/* Square upload placeholder */}
                  <div className="w-64 h-64 mx-auto border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center mb-4 bg-gray-50">
                    <Upload className="w-12 h-12 mb-4 text-gray-400" />
                    <p className="font-manrope text-gray-600 text-sm">Click to upload</p>
                    <p className="font-manrope text-gray-400 text-xs mt-1">1:1 square format</p>
                  </div>
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
              <LocationPicker
                selectedLocation={selectedLocation}
                onLocationSelect={(loc) => {
                  setSelectedLocation(loc);
                  setLocation(loc.name);
                }}
                onLocationRemove={() => {
                  setSelectedLocation(null);
                  setLocation("");
                }}
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
              <div>
                <Input
                  data-testid="product-name-input"
                  value={newProduct.name}
                  onChange={(e) => {
                    setNewProduct({ ...newProduct, name: e.target.value });
                    setBrandCheckResult(null);
                  }}
                  placeholder="Product name (e.g., 'Winter Green Jacket' - no brand names)"
                  className="font-manrope"
                />
                
                {/* Brand Check Result Display */}
                {brandCheckResult && (
                  <div className={`mt-2 p-3 rounded-lg text-sm ${
                    brandCheckResult.status === "REJECTED" 
                      ? "bg-red-50 border border-red-200 text-red-700"
                      : "bg-green-50 border border-green-200 text-green-700"
                  }`}>
                    <div className="flex items-start gap-2">
                      {brandCheckResult.status === "REJECTED" ? (
                        <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                      ) : (
                        <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="space-y-1">
                        <p className="font-semibold">
                          {brandCheckResult.status === "REJECTED" ? "Brand Detected!" : "Title Approved"}
                        </p>
                        {brandCheckResult.status === "REJECTED" && (
                          <>
                            <p>Detected brands: <span className="font-semibold">{brandCheckResult.detected_terms.join(", ")}</span></p>
                            <p className="text-gray-600">
                              Try instead: "<span className="italic">{brandCheckResult.clean_title}</span>"
                            </p>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Helper text */}
                <p className="mt-2 text-xs text-gray-500 font-manrope">
                  Use generic descriptions only. Brand names like Nike, Zara, Gucci are not allowed.
                </p>
              </div>
              
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
                disabled={checkingBrand}
              >
                {checkingBrand ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Checking...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-2" />
                    Add Product
                  </>
                )}
              </Button>
            </div>
            
            {/* Brand Guidelines Info */}
            <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-xs text-amber-800 font-manrope">
                <strong>Why no brand names?</strong> Using generic descriptions helps maintain a fair marketplace and avoids trademark issues.
              </p>
              <div className="mt-2 text-xs text-amber-700 font-manrope">
                <p className="font-semibold mb-1">Examples:</p>
                <ul className="list-disc list-inside space-y-0.5">
                  <li><span className="text-red-600 line-through">Zara Jacket</span> → <span className="text-green-600">Stylish casual jacket</span></li>
                  <li><span className="text-red-600 line-through">Nike Running Shoes</span> → <span className="text-green-600">Athletic running shoes</span></li>
                  <li><span className="text-red-600 line-through">Gucci Handbag</span> → <span className="text-green-600">Luxury leather handbag</span></li>
                </ul>
              </div>
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