import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { 
  ArrowLeft, Camera, Edit2, Send, Plus, MessageSquare, 
  UserPlus, UserCheck, Bookmark, Star, Settings, Grid3X3, 
  PlaySquare, UserSquare2, MoreHorizontal, ChevronDown,
  Heart, MessageCircle, X
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import BrandVerifiedBadge from "@/components/BrandVerifiedBadge";
import CollaborationHub from "@/components/CollaborationHub";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Story Highlight Component
function StoryHighlight({ title, image, onClick }) {
  return (
    <div 
      className="flex flex-col items-center gap-1 flex-shrink-0 cursor-pointer"
      onClick={onClick}
    >
      <div className="w-16 h-16 rounded-full p-[2px] bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600">
        <div className="w-full h-full rounded-full bg-white p-[2px]">
          {image ? (
            <img 
              src={image} 
              alt={title} 
              className="w-full h-full rounded-full object-cover"
            />
          ) : (
            <div className="w-full h-full rounded-full bg-gray-100 flex items-center justify-center">
              <Plus className="w-5 h-5 text-gray-400" />
            </div>
          )}
        </div>
      </div>
      <span className="text-xs text-gray-900 max-w-[64px] truncate font-normal">
        {title}
      </span>
    </div>
  );
}

// Add Highlight Button
function AddHighlightButton({ onClick }) {
  return (
    <div 
      className="flex flex-col items-center gap-1 flex-shrink-0 cursor-pointer"
      onClick={onClick}
    >
      <div className="w-16 h-16 rounded-full border-2 border-gray-300 flex items-center justify-center bg-white">
        <Plus className="w-6 h-6 text-gray-600" />
      </div>
      <span className="text-xs text-gray-900 font-normal">New</span>
    </div>
  );
}

// Post Grid Item with Lazy Loading
function PostGridItem({ post, onClick, isVisible }) {
  const [loaded, setLoaded] = useState(false);
  const imageUrl = `${BACKEND_URL}/api/images/${post.image_id}`;

  return (
    <div 
      className="aspect-square relative cursor-pointer bg-gray-100 overflow-hidden"
      onClick={() => onClick(post)}
      data-testid={`grid-post-${post.post_id}`}
    >
      {isVisible && (
        <>
          {!loaded && (
            <div className="absolute inset-0 bg-gray-200 animate-pulse" />
          )}
          <img
            src={imageUrl}
            alt={post.caption || "Post"}
            className={`w-full h-full object-cover transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'}`}
            loading="lazy"
            onLoad={() => setLoaded(true)}
          />
          {/* Hover overlay for desktop */}
          <div className="absolute inset-0 bg-black/40 opacity-0 hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-6">
            <div className="flex items-center gap-1 text-white font-semibold">
              <Heart className="w-5 h-5 fill-white" />
              <span>{post.likes_count || 0}</span>
            </div>
            <div className="flex items-center gap-1 text-white font-semibold">
              <MessageCircle className="w-5 h-5 fill-white" />
              <span>{post.comments_count || 0}</span>
            </div>
          </div>
          {/* Multiple images indicator */}
          {post.has_multiple && (
            <div className="absolute top-2 right-2">
              <Grid3X3 className="w-4 h-4 text-white drop-shadow-lg" />
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Post Detail Modal
function PostDetailModal({ post, user, isOpen, onClose, currentUserId, onLike }) {
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [isLiked, setIsLiked] = useState(post?.liked_by?.includes(currentUserId));
  const [likesCount, setLikesCount] = useState(post?.likes_count || 0);

  useEffect(() => {
    if (isOpen && post) {
      fetchComments();
      setIsLiked(post.liked_by?.includes(currentUserId));
      setLikesCount(post.likes_count || 0);
    }
  }, [isOpen, post]);

  const fetchComments = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/posts/${post.post_id}/comments`, { withCredentials: true });
      setComments(res.data);
    } catch (err) {
      console.error("Error fetching comments:", err);
    }
  };

  const handleLike = async () => {
    try {
      const res = await axios.post(`${BACKEND_URL}/api/posts/${post.post_id}/like`, {}, { withCredentials: true });
      setIsLiked(res.data.liked);
      setLikesCount(res.data.likes_count);
      if (onLike) onLike(post.post_id, res.data.likes_count);
    } catch (err) {
      toast.error("Failed to like post");
    }
  };

  const handleComment = async () => {
    if (!newComment.trim()) return;
    try {
      await axios.post(`${BACKEND_URL}/api/posts/${post.post_id}/comments`, { text: newComment }, { withCredentials: true });
      setNewComment("");
      fetchComments();
    } catch (err) {
      toast.error("Failed to add comment");
    }
  };

  if (!post) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl p-0 gap-0 overflow-hidden max-h-[90vh]">
        <div className="flex flex-col md:flex-row h-full">
          {/* Image */}
          <div className="md:w-[60%] bg-black flex items-center justify-center">
            <img
              src={`${BACKEND_URL}/api/images/${post.image_id}`}
              alt={post.caption || "Post"}
              className="max-h-[50vh] md:max-h-[80vh] w-full object-contain"
            />
          </div>
          
          {/* Details */}
          <div className="md:w-[40%] flex flex-col bg-white">
            {/* Header */}
            <div className="flex items-center gap-3 p-4 border-b">
              {user?.picture ? (
                <img src={user.picture.startsWith('http') ? user.picture : BACKEND_URL + user.picture} className="w-8 h-8 rounded-full object-cover" alt="" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-sm font-semibold">
                  {user?.name?.[0]}
                </div>
              )}
              <div className="flex items-center gap-1">
                <span className="font-semibold text-sm">{user?.name}</span>
                {user?.brand_verified && <BrandVerifiedBadge size="xs" />}
              </div>
              <button className="ml-auto" onClick={onClose}>
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Caption & Comments */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[30vh] md:max-h-none">
              {post.caption && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex-shrink-0 flex items-center justify-center text-xs font-semibold">
                    {user?.name?.[0]}
                  </div>
                  <div>
                    <p className="text-sm">
                      <span className="font-semibold mr-2">{user?.name}</span>
                      {post.caption}
                    </p>
                  </div>
                </div>
              )}
              
              {comments.map((comment) => (
                <div key={comment.comment_id} className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex-shrink-0 flex items-center justify-center text-xs font-semibold overflow-hidden">
                    {comment.user_picture ? (
                      <img src={comment.user_picture} className="w-full h-full object-cover" alt="" />
                    ) : (
                      comment.user_name?.[0]
                    )}
                  </div>
                  <div>
                    <p className="text-sm">
                      <span className="font-semibold mr-2">{comment.user_name}</span>
                      {comment.text}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Actions */}
            <div className="border-t p-4 space-y-3">
              <div className="flex items-center gap-4">
                <button onClick={handleLike} className="hover:opacity-60 transition-opacity">
                  <Heart className={`w-6 h-6 ${isLiked ? 'fill-red-500 text-red-500' : ''}`} />
                </button>
                <button className="hover:opacity-60 transition-opacity">
                  <MessageCircle className="w-6 h-6" />
                </button>
                <button className="hover:opacity-60 transition-opacity">
                  <Send className="w-6 h-6" />
                </button>
                <button className="ml-auto hover:opacity-60 transition-opacity">
                  <Bookmark className="w-6 h-6" />
                </button>
              </div>
              <p className="font-semibold text-sm">{likesCount.toLocaleString()} likes</p>
              
              {/* Add comment */}
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Add a comment..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleComment()}
                  className="flex-1 text-sm outline-none"
                />
                {newComment && (
                  <button onClick={handleComment} className="text-blue-500 font-semibold text-sm">
                    Post
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function UserProfile() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editBioOpen, setEditBioOpen] = useState(false);
  const [bioText, setBioText] = useState("");
  const [collaborateOpen, setCollaborateOpen] = useState(false);
  const [collabSubject, setCollabSubject] = useState("");
  const [collabMessage, setCollabMessage] = useState("");
  const [uploadingPicture, setUploadingPicture] = useState(false);
  const [isFollowing, setIsFollowing] = useState(false);
  const [followLoading, setFollowLoading] = useState(false);
  const [rewardsInfo, setRewardsInfo] = useState(null);
  const [acceptedCollabs, setAcceptedCollabs] = useState([]);
  const [activeTab, setActiveTab] = useState("posts");
  const [selectedPost, setSelectedPost] = useState(null);
  const [visiblePosts, setVisiblePosts] = useState(new Set());
  
  const gridRef = useRef(null);
  const observerRef = useRef(null);

  // Intersection Observer for lazy loading
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const postId = entry.target.dataset.postId;
          if (entry.isIntersecting) {
            setVisiblePosts((prev) => new Set([...prev, postId]));
          }
        });
      },
      { rootMargin: "100px", threshold: 0.1 }
    );

    return () => observerRef.current?.disconnect();
  }, []);

  useEffect(() => {
    if (posts.length > 0 && gridRef.current) {
      const items = gridRef.current.querySelectorAll('[data-post-id]');
      items.forEach((item) => observerRef.current?.observe(item));
    }
  }, [posts]);

  useEffect(() => {
    fetchData();
  }, [userId]);

  const fetchData = async () => {
    try {
      const [userRes, currentUserRes, postsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/users/${userId}`, { withCredentials: true }),
        axios.get(`${BACKEND_URL}/api/auth/me`, { withCredentials: true }),
        axios.get(`${BACKEND_URL}/api/users/${userId}/posts`, { withCredentials: true })
      ]);
      
      setUser(userRes.data);
      setCurrentUser(currentUserRes.data);
      setBioText(userRes.data.bio || "");
      setPosts(postsRes.data);
      
      if (currentUserRes.data.following) {
        setIsFollowing(currentUserRes.data.following.includes(userId));
      }
      
      if (currentUserRes.data.user_id === userId) {
        try {
          const rewardsRes = await axios.get(`${BACKEND_URL}/api/rewards/info`, { withCredentials: true });
          setRewardsInfo(rewardsRes.data);
        } catch (err) {
          console.error("Error fetching rewards:", err);
        }
        
        try {
          const collabRes = await axios.get(`${BACKEND_URL}/api/collaborations/accepted`, { withCredentials: true });
          setAcceptedCollabs(collabRes.data.collaborations || []);
        } catch (err) {
          console.error("Error fetching accepted collabs:", err);
        }
      }
    } catch (err) {
      console.error("Error fetching profile:", err);
      toast.error("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleProfilePictureUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error("Please select an image file");
      return;
    }

    setUploadingPicture(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/users/me/profile-picture`,
        formData,
        { withCredentials: true, headers: { 'Content-Type': 'multipart/form-data' } }
      );
      setUser({ ...user, picture: BACKEND_URL + response.data.picture });
      toast.success("Profile picture updated!");
    } catch (err) {
      toast.error("Failed to upload picture");
    } finally {
      setUploadingPicture(false);
    }
  };

  const handleSaveBio = async () => {
    try {
      await axios.patch(
        `${BACKEND_URL}/api/users/me?bio=${encodeURIComponent(bioText)}`,
        {},
        { withCredentials: true }
      );
      setUser({ ...user, bio: bioText });
      setEditBioOpen(false);
      toast.success("Bio updated!");
    } catch (err) {
      toast.error("Failed to update bio");
    }
  };

  const handleSendCollaboration = async () => {
    if (!collabSubject || !collabMessage) {
      toast.error("Please fill in both subject and message");
      return;
    }
    try {
      await axios.post(
        `${BACKEND_URL}/api/collaborations/send`,
        { to_user_id: userId, subject: collabSubject, message: collabMessage },
        { withCredentials: true }
      );
      toast.success("Collaboration request sent!");
      setCollaborateOpen(false);
      setCollabSubject("");
      setCollabMessage("");
    } catch (err) {
      toast.error("Failed to send collaboration request");
    }
  };

  const handleToggleFollow = async () => {
    setFollowLoading(true);
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/users/${userId}/follow`,
        {},
        { withCredentials: true }
      );
      setIsFollowing(response.data.following);
      toast.success(response.data.following ? "Following!" : "Unfollowed");
      setUser({
        ...user,
        followers: response.data.following 
          ? [...(user.followers || []), currentUser.user_id]
          : (user.followers || []).filter(id => id !== currentUser.user_id)
      });
    } catch (err) {
      toast.error("Failed to update follow status");
    } finally {
      setFollowLoading(false);
    }
  };

  const handleRequestBrandVerification = async () => {
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/users/${userId}/brand-verify`,
        {},
        { withCredentials: true }
      );
      if (response.data.brand_verified) {
        setUser({ ...user, brand_verified: true });
        toast.success("Congratulations! You're now Brand Verified!");
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to verify brand status");
    }
  };

  const handlePostClick = (post) => {
    setSelectedPost(post);
  };

  const handlePostLike = (postId, newLikesCount) => {
    setPosts(posts.map(p => p.post_id === postId ? { ...p, likes_count: newLikesCount } : p));
  };

  // Generate story highlights from accepted collaborations
  const storyHighlights = [
    ...(acceptedCollabs.length > 0 ? acceptedCollabs.slice(0, 5).map((collab, i) => ({
      id: collab.message_id,
      title: collab.from_user_name || collab.to_user_name || "Collab",
      image: null
    })) : []),
    { id: 'fashion', title: 'Fashion', image: posts[0] ? `${BACKEND_URL}/api/images/${posts[0].image_id}` : null },
    { id: 'style', title: 'Style', image: posts[1] ? `${BACKEND_URL}/api/images/${posts[1].image_id}` : null },
    { id: 'ootd', title: 'OOTD', image: posts[2] ? `${BACKEND_URL}/api/images/${posts[2].image_id}` : null },
  ].filter(h => h.title);

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 border-t-gray-900"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <p className="text-gray-500">User not found</p>
      </div>
    );
  }

  const isOwnProfile = currentUser?.user_id === userId;

  return (
    <div className="min-h-screen bg-white">
      {/* Mobile Header */}
      <header className="sticky top-0 z-50 bg-white border-b px-4 py-3">
        <div className="flex items-center justify-between max-w-lg mx-auto">
          <button onClick={() => navigate(-1)} className="p-1">
            <ArrowLeft className="w-6 h-6" />
          </button>
          
          <div className="flex items-center gap-1">
            <span className="font-semibold text-base">{user.name}</span>
            {user.brand_verified && <BrandVerifiedBadge size="sm" />}
            <ChevronDown className="w-4 h-4" />
          </div>
          
          <div className="flex items-center gap-3">
            {isOwnProfile && (
              <button onClick={() => navigate('/upload')} className="p-1">
                <Plus className="w-6 h-6" />
              </button>
            )}
            <button className="p-1">
              <MoreHorizontal className="w-6 h-6" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto pb-16">
        {/* Profile Info Section */}
        <div className="px-4 pt-4">
          {/* Profile Picture & Stats Row */}
          <div className="flex items-center gap-6 mb-4">
            {/* Profile Picture */}
            <div className="relative flex-shrink-0">
              <div className="w-20 h-20 rounded-full overflow-hidden bg-gray-100 ring-2 ring-gray-200">
                {user.picture ? (
                  <img 
                    src={user.picture.startsWith('http') ? user.picture : BACKEND_URL + user.picture} 
                    alt={user.name} 
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-purple-400 to-pink-400">
                    <span className="text-white text-2xl font-semibold">{user.name[0]}</span>
                  </div>
                )}
              </div>
              {isOwnProfile && (
                <label className="absolute -bottom-1 -right-1 w-7 h-7 bg-blue-500 rounded-full flex items-center justify-center cursor-pointer border-2 border-white">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleProfilePictureUpload}
                    className="hidden"
                    disabled={uploadingPicture}
                  />
                  <Plus className="w-4 h-4 text-white" />
                </label>
              )}
            </div>

            {/* Stats */}
            <div className="flex-1 flex justify-around">
              <div className="text-center">
                <p className="font-semibold text-lg">{posts.length}</p>
                <p className="text-sm text-gray-500">posts</p>
              </div>
              <div className="text-center">
                <p className="font-semibold text-lg">{user.followers?.length || 0}</p>
                <p className="text-sm text-gray-500">followers</p>
              </div>
              <div className="text-center">
                <p className="font-semibold text-lg">{user.following?.length || 0}</p>
                <p className="text-sm text-gray-500">following</p>
              </div>
            </div>
          </div>

          {/* Name & Bio */}
          <div className="mb-4">
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-sm">{user.name}</h2>
              {user.brand_verified && <BrandVerifiedBadge size="xs" />}
            </div>
            {user.category && (
              <p className="text-sm text-gray-500 capitalize">{user.category}'s Fashion</p>
            )}
            {user.bio ? (
              <p className="text-sm mt-1 whitespace-pre-wrap">{user.bio}</p>
            ) : isOwnProfile && (
              <button 
                onClick={() => setEditBioOpen(true)}
                className="text-sm text-blue-500 mt-1"
              >
                Add bio
              </button>
            )}
            
            {/* Earnings indicator for own profile */}
            {isOwnProfile && rewardsInfo && (
              <div className="flex items-center gap-2 mt-2">
                <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                <span className="text-sm font-medium">{rewardsInfo.stars || 0} stars</span>
                <span className="text-gray-300">•</span>
                <span className="text-sm text-green-600 font-medium">€{rewardsInfo.payout_points_eur?.toFixed(2) || '0.00'}</span>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 mb-4">
            {isOwnProfile ? (
              <>
                <button 
                  onClick={() => setEditBioOpen(true)}
                  className="flex-1 py-1.5 px-4 bg-gray-100 hover:bg-gray-200 rounded-lg font-semibold text-sm transition-colors"
                >
                  Edit profile
                </button>
                <button 
                  onClick={() => navigate('/rewards')}
                  className="flex-1 py-1.5 px-4 bg-gray-100 hover:bg-gray-200 rounded-lg font-semibold text-sm transition-colors"
                >
                  Rewards
                </button>
                {acceptedCollabs.length > 0 && !user.brand_verified && (
                  <button 
                    onClick={handleRequestBrandVerification}
                    className="py-1.5 px-3 bg-gradient-to-r from-yellow-400 to-yellow-600 rounded-lg font-semibold text-sm text-white"
                    data-testid="get-brand-verified-btn"
                  >
                    <BrandVerifiedBadge size="xs" className="inline-block" />
                  </button>
                )}
              </>
            ) : (
              <>
                <button 
                  onClick={handleToggleFollow}
                  disabled={followLoading}
                  className={`flex-1 py-1.5 px-4 rounded-lg font-semibold text-sm transition-colors ${
                    isFollowing 
                      ? 'bg-gray-100 hover:bg-gray-200 text-gray-900' 
                      : 'bg-blue-500 hover:bg-blue-600 text-white'
                  }`}
                  data-testid="follow-btn"
                >
                  {isFollowing ? 'Following' : 'Follow'}
                </button>
                <button 
                  onClick={() => setCollaborateOpen(true)}
                  className="flex-1 py-1.5 px-4 bg-gray-100 hover:bg-gray-200 rounded-lg font-semibold text-sm transition-colors"
                  data-testid="collaborate-btn"
                >
                  Message
                </button>
                <button className="py-1.5 px-3 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors">
                  <UserPlus className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>

        {/* Story Highlights */}
        <div className="border-b">
          <div className="px-4 py-4 overflow-x-auto scrollbar-hide">
            <div className="flex gap-4">
              {isOwnProfile && (
                <AddHighlightButton onClick={() => toast.info("Create a highlight from your posts")} />
              )}
              {storyHighlights.map((highlight) => (
                <StoryHighlight 
                  key={highlight.id}
                  title={highlight.title}
                  image={highlight.image}
                  onClick={() => toast.info(`Viewing ${highlight.title}`)}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Collaboration Hub for own profile */}
        {isOwnProfile && (
          <CollaborationHub 
            userId={userId} 
            textColor="#000000" 
            bgColor="#FFFFFF"
          />
        )}

        {/* Tab Navigation */}
        <div className="flex border-b sticky top-[57px] bg-white z-40">
          <button 
            onClick={() => setActiveTab("posts")}
            className={`flex-1 py-3 flex justify-center items-center border-b-2 transition-colors ${
              activeTab === "posts" ? 'border-gray-900' : 'border-transparent text-gray-400'
            }`}
          >
            <Grid3X3 className="w-6 h-6" />
          </button>
          <button 
            onClick={() => setActiveTab("reels")}
            className={`flex-1 py-3 flex justify-center items-center border-b-2 transition-colors ${
              activeTab === "reels" ? 'border-gray-900' : 'border-transparent text-gray-400'
            }`}
          >
            <PlaySquare className="w-6 h-6" />
          </button>
          <button 
            onClick={() => setActiveTab("tagged")}
            className={`flex-1 py-3 flex justify-center items-center border-b-2 transition-colors ${
              activeTab === "tagged" ? 'border-gray-900' : 'border-transparent text-gray-400'
            }`}
          >
            <UserSquare2 className="w-6 h-6" />
          </button>
        </div>

        {/* Post Grid */}
        <div ref={gridRef} className="grid grid-cols-3 gap-[1px] bg-gray-100">
          {posts.length === 0 ? (
            <div className="col-span-3 py-20 text-center bg-white">
              <Camera className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p className="text-gray-500 font-semibold">No Posts Yet</p>
              {isOwnProfile && (
                <button 
                  onClick={() => navigate('/upload')}
                  className="mt-4 text-blue-500 font-semibold"
                >
                  Share your first post
                </button>
              )}
            </div>
          ) : (
            posts.map((post) => (
              <div key={post.post_id} data-post-id={post.post_id}>
                <PostGridItem
                  post={post}
                  onClick={handlePostClick}
                  isVisible={visiblePosts.has(post.post_id) || posts.indexOf(post) < 9}
                />
              </div>
            ))
          )}
        </div>
      </main>

      {/* Post Detail Modal */}
      <PostDetailModal
        post={selectedPost}
        user={user}
        isOpen={!!selectedPost}
        onClose={() => setSelectedPost(null)}
        currentUserId={currentUser?.user_id}
        onLike={handlePostLike}
      />

      {/* Edit Bio Dialog */}
      <Dialog open={editBioOpen} onOpenChange={setEditBioOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Edit Profile</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <label className="text-sm font-medium text-gray-700 mb-2 block">Bio</label>
            <Textarea
              value={bioText}
              onChange={(e) => setBioText(e.target.value)}
              placeholder="Add a bio..."
              rows={4}
              maxLength={150}
              className="resize-none"
            />
            <p className="text-xs text-gray-400 mt-1 text-right">{bioText.length}/150</p>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditBioOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveBio} className="bg-blue-500 hover:bg-blue-600">Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Collaboration Dialog */}
      <Dialog open={collaborateOpen} onOpenChange={setCollaborateOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Send Message</DialogTitle>
            <DialogDescription>Send a collaboration request to {user.name}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Subject</label>
              <Input
                value={collabSubject}
                onChange={(e) => setCollabSubject(e.target.value)}
                placeholder="Brand partnership, photo shoot..."
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Message</label>
              <Textarea
                value={collabMessage}
                onChange={(e) => setCollabMessage(e.target.value)}
                placeholder="Hi! I'd love to collaborate..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setCollaborateOpen(false)}>Cancel</Button>
            <Button onClick={handleSendCollaboration} className="bg-blue-500 hover:bg-blue-600">
              <Send className="w-4 h-4 mr-2" />
              Send
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Custom scrollbar hide styles */}
      <style>{`
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
    </div>
  );
}
