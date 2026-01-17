import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Star, Crown, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import PostCard from "@/components/PostCard";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function CelebrityPage() {
  const navigate = useNavigate();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    fetchCelebrityPosts();
  }, []);

  const fetchCelebrityPosts = async (skip = 0) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/posts/celebrity?skip=${skip}&limit=20`);
      if (skip === 0) {
        setPosts(response.data.posts || []);
      } else {
        setPosts(prev => [...prev, ...(response.data.posts || [])]);
      }
      setTotal(response.data.total);
      setHasMore(response.data.has_more);
    } catch (err) {
      console.error("Error fetching celebrity posts:", err);
      toast.error("Failed to load celebrity posts");
    } finally {
      setLoading(false);
    }
  };

  const loadMore = () => {
    fetchCelebrityPosts(posts.length);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-yellow-50 via-white to-orange-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-yellow-50 via-white to-orange-50" data-testid="celebrity-page">
      {/* Header */}
      <header className="sticky top-0 bg-gradient-to-r from-yellow-400 via-orange-400 to-red-400 text-white z-50">
        <div className="max-w-6xl mx-auto px-4 py-5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate(-1)}
              className="text-white hover:bg-white/20"
              data-testid="back-btn"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-xl">
                <Crown className="w-7 h-7" />
              </div>
              <div>
                <h1 className="font-italiana text-3xl">Celebrity Stars</h1>
                <p className="font-manrope text-sm text-white/80">Posts with 10,000+ likes</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-white/20 px-4 py-2 rounded-full">
            <TrendingUp className="w-5 h-5" />
            <span className="font-manrope font-bold">{total} viral posts</span>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {posts.length === 0 ? (
          <div className="text-center py-20">
            <Star className="w-20 h-20 mx-auto mb-4 text-yellow-300" />
            <h2 className="font-italiana text-3xl mb-2">No celebrity posts yet</h2>
            <p className="font-manrope text-gray-500 mb-6 max-w-md mx-auto">
              Posts that reach 10,000 likes will appear here in the Celebrity Stars hall of fame
            </p>
            <Button
              onClick={() => navigate("/dashboard")}
              className="font-manrope rounded-full bg-gradient-to-r from-yellow-400 to-orange-400 hover:from-yellow-500 hover:to-orange-500"
            >
              Back to Feed
            </Button>
          </div>
        ) : (
          <>
            {/* Featured Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {posts.map((post, index) => (
                <div 
                  key={post.post_id} 
                  className="relative"
                  data-testid={`celebrity-post-${post.post_id}`}
                >
                  {/* Rank Badge */}
                  {index < 3 && (
                    <div className={`absolute -top-3 -left-3 z-10 w-10 h-10 rounded-full flex items-center justify-center font-italiana text-lg font-bold shadow-lg ${
                      index === 0 ? 'bg-yellow-400 text-yellow-900' :
                      index === 1 ? 'bg-gray-300 text-gray-700' :
                      'bg-orange-300 text-orange-800'
                    }`}>
                      #{index + 1}
                    </div>
                  )}
                  
                  <div className="bg-white rounded-2xl overflow-hidden shadow-lg hover:shadow-xl transition-shadow">
                    <PostCard
                      post={post}
                      onLike={() => {}}
                      onStar={() => {}}
                      currentUserId=""
                    />
                    
                    {/* Stats Footer */}
                    <div className="px-4 py-3 bg-gradient-to-r from-yellow-50 to-orange-50 border-t">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
                          <span className="font-manrope font-bold text-yellow-700">
                            {post.likes_count?.toLocaleString()} likes
                          </span>
                        </div>
                        <span className="font-manrope text-xs text-gray-500">
                          by {post.user_name}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Load More */}
            {hasMore && (
              <div className="text-center mt-8">
                <Button
                  onClick={loadMore}
                  variant="outline"
                  className="font-manrope rounded-full px-8"
                >
                  Load More Celebrity Posts
                </Button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
