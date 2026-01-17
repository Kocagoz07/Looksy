import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Heart, Bookmark, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import PostCard from "@/components/PostCard";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function FavoritesPage() {
  const navigate = useNavigate();
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFavorites();
  }, []);

  const fetchFavorites = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/users/me/favorites`, {
        withCredentials: true
      });
      setFavorites(response.data.favorites || []);
    } catch (err) {
      console.error("Error fetching favorites:", err);
      if (err.response?.status === 401) {
        navigate("/");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUnfavorite = async (postId) => {
    try {
      await axios.post(`${BACKEND_URL}/api/posts/${postId}/favorite`, {}, {
        withCredentials: true
      });
      setFavorites(favorites.filter(f => f.post_id !== postId));
      toast.success("Removed from favorites");
    } catch (err) {
      console.error("Error unfavoriting:", err);
      toast.error("Failed to remove from favorites");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white" data-testid="favorites-page">
      {/* Header */}
      <header className="sticky top-0 bg-white border-b z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate(-1)}
              data-testid="back-btn"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2">
              <Bookmark className="w-6 h-6 fill-black" />
              <h1 className="font-italiana text-2xl">My Favorites</h1>
            </div>
          </div>
          <span className="font-manrope text-sm text-gray-500">
            {favorites.length} saved
          </span>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {favorites.length === 0 ? (
          <div className="text-center py-20">
            <Bookmark className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <h2 className="font-italiana text-2xl mb-2">No favorites yet</h2>
            <p className="font-manrope text-gray-500 mb-6">
              Save posts you love by tapping the bookmark icon
            </p>
            <Button
              onClick={() => navigate("/dashboard")}
              className="font-manrope rounded-full"
            >
              Explore Posts
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {favorites.map((post) => (
              <div key={post.post_id} className="relative group">
                <PostCard
                  post={post}
                  onLike={() => {}}
                  onStar={() => {}}
                  currentUserId=""
                />
                {/* Remove from favorites overlay */}
                <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    size="icon"
                    variant="secondary"
                    className="rounded-full bg-white/90 hover:bg-red-100"
                    onClick={() => handleUnfavorite(post.post_id)}
                    data-testid={`unfavorite-btn-${post.post_id}`}
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
