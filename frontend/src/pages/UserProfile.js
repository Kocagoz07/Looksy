import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Briefcase, DollarSign } from "lucide-react";
import { Button } from "@/components/ui/button";
import PostCard from "@/components/PostCard";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function UserProfile() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

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
      setPosts(postsRes.data);
    } catch (err) {
      console.error("Error fetching profile:", err);
      toast.error("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black"></div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <p className="font-manrope text-gray-600">User not found</p>
      </div>
    );
  }

  const isOwnProfile = currentUser?.user_id === userId;

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
        <h1 className="font-playfair text-2xl font-bold">Profile</h1>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Profile Header */}
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6 mb-12">
          {user.picture ? (
            <img src={user.picture} alt={user.name} className="w-24 h-24 rounded-full" />
          ) : (
            <div className="w-24 h-24 rounded-full bg-gray-200 flex items-center justify-center">
              <span className="font-playfair text-3xl font-semibold">{user.name[0]}</span>
            </div>
          )}
          
          <div className="flex-1 text-center sm:text-left">
            <h2 className="font-playfair text-3xl font-bold mb-2">{user.name}</h2>
            {user.category && (
              <p className="font-manrope text-sm text-gray-600 capitalize mb-4">{user.category}'s Fashion</p>
            )}
            
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-4">
              <div className="text-center sm:text-left">
                <p className="font-manrope text-2xl font-bold">{posts.length}</p>
                <p className="font-manrope text-sm text-gray-600">Posts</p>
              </div>
              
              {isOwnProfile && (
                <div className="glass px-6 py-3 rounded-lg" data-testid="earnings-box">
                  <div className="flex items-center gap-2 mb-1">
                    <DollarSign className="w-4 h-4 text-green-600" />
                    <p className="font-manrope text-xs text-gray-600 font-semibold">Total Earnings</p>
                  </div>
                  <p className="font-playfair text-2xl font-bold text-green-600">
                    ${user.earnings.toFixed(2)}
                  </p>
                </div>
              )}
            </div>
            
            {!isOwnProfile && (
              <Button
                data-testid="collaborate-btn"
                className="mt-4 bg-black text-white hover:bg-gray-800 font-manrope font-semibold rounded-full flex items-center gap-2"
              >
                <Briefcase className="w-4 h-4" />
                Collaborate
              </Button>
            )}
          </div>
        </div>

        {/* Posts Grid */}
        <div>
          <h3 className="font-playfair text-2xl font-bold mb-6">Posts</h3>
          {posts.length === 0 ? (
            <div className="text-center py-12">
              <p className="font-manrope text-gray-500">No posts yet</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {posts.map((post) => (
                <PostCard key={post.post_id} post={post} currentUserId={currentUser?.user_id} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}