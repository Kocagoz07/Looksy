import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, MessageCircle, Star } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function PostCard({ post, currentUserId }) {
  const navigate = useNavigate();
  const [likes, setLikes] = useState(post.likes_count);
  const [isLiked, setIsLiked] = useState(post.liked_by?.includes(currentUserId));

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

  const isStar = likes >= 10000;

  return (
    <div
      data-testid={`post-card-${post.post_id}`}
      onClick={() => navigate(`/post/${post.post_id}`)}
      className="post-card cursor-pointer group"
    >
      <div className="post-image-container rounded-lg overflow-hidden relative">
        <img
          src={`${BACKEND_URL}/api/images/${post.image_id}`}
          alt={post.caption || "Post"}
          className="w-full h-full object-cover"
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
      <div className="mt-3 space-y-1">
        {post.caption && (
          <p className="font-manrope text-sm line-clamp-2">{post.caption}</p>
        )}
        
        <div className="flex items-center gap-4">
          <button
            data-testid={`like-btn-${post.post_id}`}
            onClick={handleLike}
            className="flex items-center gap-1 hover:scale-110 transition-transform"
          >
            <Heart className={`w-5 h-5 ${isLiked ? 'fill-current text-red-500' : ''}`} />
            <span className="font-manrope text-sm font-semibold">{likes}</span>
          </button>
        </div>
        
        {post.total_price && (
          <p className="font-manrope text-xs opacity-70">Total: ${post.total_price}</p>
        )}
      </div>
    </div>
  );
}