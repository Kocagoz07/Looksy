import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, MessageCircle, Star, Trash2, Bookmark } from "lucide-react";
import { Button } from "@/components/ui/button";
import DeleteConfirmDialog from "@/components/DeleteConfirmDialog";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function PostCard({ post, currentUserId, onDelete }) {
  const navigate = useNavigate();
  const [likes, setLikes] = useState(post.likes_count);
  const [isLiked, setIsLiked] = useState(post.liked_by?.includes(currentUserId));
  const [isStarred, setIsStarred] = useState(post.starred_by?.includes(currentUserId));
  const [isFavorited, setIsFavorited] = useState(post.is_favorited || false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const isOwner = post.user_id === currentUserId;

  const handleLike = async (e) => {
    e.stopPropagation();
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/posts/${post.post_id}/like`,
        {},
        { withCredentials: true }
      );
      setLikes(response.data.likes_count);
      setIsLiked(response.data.liked);
    } catch (err) {
      console.error("Error liking post:", err);
      toast.error("Failed to like post");
    }
  };

  const handleStar = async (e) => {
    e.stopPropagation();
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/posts/${post.post_id}/star`,
        {},
        { withCredentials: true }
      );
      setIsStarred(response.data.starred);
      toast.success(response.data.starred ? "Star given!" : "Star removed");
    } catch (err) {
      console.error("Error starring post:", err);
      toast.error("Failed to star post");
    }
  };

  const handleFavorite = async (e) => {
    e.stopPropagation();
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/posts/${post.post_id}/favorite`,
        {},
        { withCredentials: true }
      );
      setIsFavorited(response.data.is_favorited);
      toast.success(response.data.is_favorited ? "Added to favorites!" : "Removed from favorites");
    } catch (err) {
      console.error("Error favoriting post:", err);
      toast.error("Failed to update favorites");
    }
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    setDeleting(true);
    try {
      await axios.delete(
        `${BACKEND_URL}/api/posts/${post.post_id}`,
        { withCredentials: true }
      );
      toast.success("Post deleted successfully");
      setDeleteDialogOpen(false);
      if (onDelete) {
        onDelete(post.post_id);
      }
    } catch (err) {
      console.error("Error deleting post:", err);
      toast.error("Failed to delete post");
    } finally {
      setDeleting(false);
    }
  };

  const isStar = likes >= 10000;

  return (
    <>
      <div
        data-testid={`post-card-${post.post_id}`}
        onClick={() => navigate(`/post/${post.post_id}`)}
        className="post-card cursor-pointer group"
      >
        {/* Square 1:1 aspect ratio image container */}
        <div className="post-image-container rounded-lg">
          <img
            src={`${BACKEND_URL}/api/images/${post.image_id}`}
            alt={post.caption || "Post"}
            loading="lazy"
          />
          
          {isStar && (
            <div className="star-badge" data-testid="star-badge">
              <Star className="w-4 h-4 fill-current" />
              <span>10K+</span>
            </div>
          )}
          
          {/* Hover overlay */}
          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all duration-200 flex items-center justify-center gap-6 opacity-0 group-hover:opacity-100">
            <div className="flex items-center gap-2 text-white">
              <Heart className={`w-6 h-6 ${isLiked ? 'fill-current' : ''}`} />
              <span className="font-manrope font-semibold">{likes}</span>
            </div>
            <div className="flex items-center gap-2 text-white">
              <MessageCircle className="w-6 h-6" />
            </div>
          </div>
        </div>
        
        {/* Post info */}
        <div className="mt-3 space-y-2">
          {post.caption && (
            <p className="font-manrope text-sm line-clamp-2">{post.caption}</p>
          )}
          
          <div className="flex items-center gap-3">
            <button
              data-testid={`like-btn-${post.post_id}`}
              onClick={handleLike}
              className="flex items-center gap-1 hover:scale-110 transition-transform"
            >
              <Heart className={`w-5 h-5 ${isLiked ? 'fill-current text-red-500' : ''}`} />
              <span className="font-manrope text-sm font-semibold">{likes}</span>
            </button>
            
            <button
              data-testid={`star-btn-${post.post_id}`}
              onClick={handleStar}
              className="flex items-center gap-1 hover:scale-110 transition-transform"
              title={isStarred ? "Remove star" : "Give star"}
            >
              <Star className={`w-5 h-5 ${isStarred ? 'fill-current text-yellow-500' : ''}`} />
            </button>
            
            <button
              data-testid={`favorite-btn-${post.post_id}`}
              onClick={handleFavorite}
              className="flex items-center gap-1 hover:scale-110 transition-transform"
              title={isFavorited ? "Remove from favorites" : "Add to favorites"}
            >
              <Bookmark className={`w-5 h-5 ${isFavorited ? 'fill-current text-blue-500' : ''}`} />
            </button>
            
            {isOwner && (
              <button
                data-testid={`delete-btn-${post.post_id}`}
                onClick={handleDeleteClick}
                className="flex items-center gap-1 hover:scale-110 transition-transform text-red-500 ml-auto"
                title="Delete post"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            )}
          </div>
          
          {post.total_price_eur && (
            <p className="font-manrope text-xs opacity-70">Total: €{post.total_price_eur}</p>
          )}
        </div>
      </div>

      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onConfirm={handleDeleteConfirm}
        title="Delete Post?"
        description="This post will be hidden from your profile and feeds. This action cannot be undone."
      />
    </>
  );
}