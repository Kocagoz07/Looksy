import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Heart, Music, MapPin, Star, ExternalLink, MessageCircle, Trash2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import BrandVerifiedBadge from "@/components/BrandVerifiedBadge";
import { SharePostDialog } from "@/components/SharePostDialog";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function PostDetail() {
  const { postId } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [shareOpen, setShareOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [isLiked, setIsLiked] = useState(false);
  const [isStarred, setIsStarred] = useState(false);

  useEffect(() => {
    fetchData();
  }, [postId]);

  const fetchData = async () => {
    try {
      const [postRes, currentUserRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/posts/${postId}`, { withCredentials: true }),
        axios.get(`${BACKEND_URL}/api/auth/me`, { withCredentials: true })
      ]);
      
      setPost(postRes.data);
      setCurrentUser(currentUserRes.data);
      setIsLiked(postRes.data.liked_by?.includes(currentUserRes.data.user_id));
      setIsStarred(postRes.data.starred_by?.includes(currentUserRes.data.user_id));
      
      const userRes = await axios.get(`${BACKEND_URL}/api/users/${postRes.data.user_id}`, { withCredentials: true });
      setUser(userRes.data);
      
      const commentsRes = await axios.get(`${BACKEND_URL}/api/posts/${postId}/comments`, { withCredentials: true });
      setComments(commentsRes.data);
    } catch (err) {
      console.error("Error fetching post:", err);
      toast.error("Failed to load post");
    } finally {
      setLoading(false);
    }
  };

  const handleLike = async () => {
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/posts/${postId}/like`,
        {},
        { withCredentials: true }
      );
      setPost({ ...post, likes_count: response.data.likes_count });
      setIsLiked(response.data.liked);
    } catch (err) {
      console.error("Error liking post:", err);
      toast.error("Failed to like post");
    }
  };

  const handleStar = async () => {
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/posts/${postId}/star`,
        {},
        { withCredentials: true }
      );
      setIsStarred(response.data.starred);
      toast.success(response.data.starred ? "Post saved!" : "Post unsaved");
    } catch (err) {
      console.error("Error starring post:", err);
      toast.error("Failed to save post");
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;
    
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/posts/${postId}/comments`,
        { text: newComment },
        { withCredentials: true }
      );
      setComments([response.data, ...comments]);
      setNewComment("");
      toast.success("Comment added");
    } catch (err) {
      console.error("Error adding comment:", err);
      toast.error("Failed to add comment");
    }
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await axios.delete(
        `${BACKEND_URL}/api/comments/${commentId}`,
        { withCredentials: true }
      );
      setComments(comments.filter(c => c.comment_id !== commentId));
      toast.success("Comment deleted");
    } catch (err) {
      console.error("Error deleting comment:", err);
      toast.error("Failed to delete comment");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black"></div>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <p className="font-manrope text-gray-600">Post not found</p>
      </div>
    );
  }

  const isStar = post.likes_count >= 10000;

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b px-4 py-4 flex items-center gap-4 sticky top-0 bg-white z-10">
        <Button
          data-testid="back-btn"
          onClick={() => navigate(-1)}
          variant="ghost"
          size="icon"
          className="rounded-full"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <h1 className="font-playfair text-2xl font-bold">Post</h1>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 md:py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
          {/* Image */}
          <div className="relative">
            <div className="aspect-square rounded-lg overflow-hidden relative bg-gray-100">
              <img
                src={`${BACKEND_URL}/api/images/${post.image_id}`}
                alt={post.caption || "Post"}
                className="w-full h-full object-cover"
              />
              {isStar && (
                <div className="star-badge">
                  <Star className="w-4 h-4 fill-current" />
                  <span>10K+</span>
                </div>
              )}
            </div>
            
            {/* User Info - Mobile: Directly below image */}
            <div className="lg:hidden mt-4">
              {user && (
                <div 
                  className="flex items-center gap-4 cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => navigate(`/profile/${user.user_id}`)}
                >
                  {user.picture ? (
                    <img 
                      src={user.picture.startsWith('http') ? user.picture : `${BACKEND_URL}${user.picture}`} 
                      alt={user.name} 
                      className="w-12 h-12 rounded-full object-cover border-2 border-gray-100 shadow-sm" 
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center border-2 border-gray-100 shadow-sm">
                      <span className="font-playfair text-lg font-semibold text-gray-600">{user.name?.[0]?.toUpperCase()}</span>
                    </div>
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-manrope font-semibold text-base">{user.name}</p>
                      {user.brand_verified && <BrandVerifiedBadge size="sm" />}
                    </div>
                    {post.location && (
                      <div className="flex items-center gap-1 text-gray-600 mt-0.5" data-testid="post-location-mobile">
                        <MapPin className="w-3.5 h-3.5" />
                        <span className="font-manrope text-sm">{post.location}{post.venue && ` • ${post.venue}`}</span>
                      </div>
                    )}
                    {user.category && (
                      <p className="font-manrope text-xs text-gray-500 capitalize mt-0.5">{user.category}</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Details */}
          <div className="space-y-6">
            {/* User Info - Desktop: In sidebar */}
            <div className="hidden lg:block">
              {user && (
                <div 
                  className="flex items-center gap-4 cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => navigate(`/profile/${user.user_id}`)}
                >
                  {user.picture ? (
                    <img 
                      src={user.picture.startsWith('http') ? user.picture : `${BACKEND_URL}${user.picture}`} 
                      alt={user.name} 
                      className="w-14 h-14 rounded-full object-cover border-2 border-gray-100 shadow-sm" 
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center border-2 border-gray-100 shadow-sm">
                      <span className="font-playfair text-xl font-semibold text-gray-600">{user.name?.[0]?.toUpperCase()}</span>
                    </div>
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-manrope font-semibold text-base">{user.name}</p>
                      {user.brand_verified && <BrandVerifiedBadge size="sm" />}
                    </div>
                    {post.location && (
                      <div className="flex items-center gap-1 text-gray-600 mt-0.5" data-testid="post-location-desktop">
                        <MapPin className="w-3.5 h-3.5" />
                        <span className="font-manrope text-sm">{post.location}{post.venue && ` • ${post.venue}`}</span>
                      </div>
                    )}
                    {user.category && (
                      <p className="font-manrope text-xs text-gray-500 capitalize mt-0.5">{user.category}</p>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-4">
              <Button
                data-testid="like-btn"
                onClick={handleLike}
                variant="ghost"
                className="flex items-center gap-2"
              >
                <Heart className={`w-6 h-6 ${isLiked ? 'fill-current text-red-500' : ''}`} />
                <span className="font-manrope font-semibold">{post.likes_count}</span>
              </Button>
              
              <Button
                data-testid="star-btn"
                onClick={handleStar}
                variant="ghost"
                className="flex items-center gap-2"
                title={isStarred ? "Unsave" : "Save"}
              >
                <Star className={`w-6 h-6 ${isStarred ? 'fill-current text-yellow-500' : ''}`} />
              </Button>

              <Button
                data-testid="share-btn"
                onClick={() => setShareOpen(true)}
                variant="ghost"
                className="flex items-center gap-2"
                title="Share"
              >
                <Send className="w-6 h-6" />
              </Button>
              <SharePostDialog open={shareOpen} onOpenChange={setShareOpen} postId={post.post_id} />
            </div>

            {/* Caption */}
            {post.caption && (
              <div>
                <p className="font-manrope text-base leading-relaxed">{post.caption}</p>
              </div>
            )}

            {/* Metadata */}
            <div className="space-y-2">
              {post.music && (
                <a
                  href={post.music}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-gray-700 hover:text-black transition-colors"
                >
                  <Music className="w-4 h-4" />
                  <span className="font-manrope text-sm">Music Link</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>

            {/* Products */}
            {post.products && post.products.length > 0 && (
              <div>
                <h3 className="font-italiana text-lg font-semibold mb-3">Products</h3>
                {(post.total_price || post.total_price_eur) && (
                  <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                    <p className="font-manrope text-sm text-gray-600 mb-1">Total Outfit Price</p>
                    <div className="flex items-baseline gap-3">
                      {post.total_price_eur && (
                        <p className="font-manrope text-2xl font-bold text-black">€{post.total_price_eur.toFixed(2)}</p>
                      )}
                      {post.total_price && (
                        <p className="font-manrope text-lg text-gray-500">${post.total_price.toFixed(2)}</p>
                      )}
                    </div>
                  </div>
                )}
                <div className="space-y-2">
                  {post.products.map((product, index) => (
                    <a
                      key={index}
                      href={product.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <span className="font-manrope text-sm font-medium">{product.name}</span>
                      <ExternalLink className="w-4 h-4 text-gray-500" />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Comments Section */}
            <div className="border-t pt-6">
              <h3 className="font-playfair text-lg font-semibold mb-4 flex items-center gap-2">
                <MessageCircle className="w-5 h-5" />
                Comments ({comments.length})
              </h3>

              {/* Add Comment */}
              <div className="mb-6">
                <Textarea
                  data-testid="comment-input"
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Add a comment..."
                  className="font-manrope mb-2"
                  rows={2}
                />
                <Button
                  data-testid="add-comment-btn"
                  onClick={handleAddComment}
                  disabled={!newComment.trim()}
                  className="bg-black text-white hover:bg-gray-800 font-manrope rounded-full"
                >
                  Post Comment
                </Button>
              </div>

              {/* Comments List */}
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {comments.map((comment) => (
                  <div key={comment.comment_id} className="flex gap-3">
                    {comment.user_picture ? (
                      <img src={comment.user_picture} alt={comment.user_name} className="w-8 h-8 rounded-full" />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                        <span className="font-manrope text-xs font-semibold">{comment.user_name[0]}</span>
                      </div>
                    )}
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <p className="font-manrope text-sm font-semibold">{comment.user_name}</p>
                        {comment.user_id === currentUser?.user_id && (
                          <Button
                            data-testid={`delete-comment-${comment.comment_id}`}
                            onClick={() => handleDeleteComment(comment.comment_id)}
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        )}
                      </div>
                      <p className="font-manrope text-sm text-gray-700">{comment.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}