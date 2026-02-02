import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Spade, Heart, Star, Plus, User, LogOut, Search, Crown, Compass } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import PostCard from "@/components/PostCard";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function Dashboard({ category = null }) {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(category || "all");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchDialog, setShowSearchDialog] = useState(false);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  useEffect(() => {
    if (category) {
      setActiveTab(category);
    }
  }, [category]);

  useEffect(() => {
    fetchPosts();
  }, [activeTab]);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/auth/me`, { withCredentials: true });
      setCurrentUser(response.data);
    } catch (err) {
      console.error("Error fetching user:", err);
    }
  };

  const fetchPosts = async () => {
    setLoading(true);
    try {
      let url = `${BACKEND_URL}/api/posts`;
      
      if (activeTab === "stars") {
        url = `${BACKEND_URL}/api/posts/stars`;
      } else if (activeTab === "men" || activeTab === "women") {
        url = `${BACKEND_URL}/api/posts?category=${activeTab}`;
      }
      
      const response = await axios.get(url, { withCredentials: true });
      setPosts(response.data);
    } catch (err) {
      console.error("Error fetching posts:", err);
      toast.error("Failed to load posts");
    } finally {
      setLoading(false);
    }
  };

  const handlePostDelete = (postId) => {
    setPosts(posts.filter(p => p.post_id !== postId));
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${BACKEND_URL}/api/auth/logout`, {}, { withCredentials: true });
      navigate("/", { replace: true });
    } catch (err) {
      console.error("Logout error:", err);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    setSearching(true);
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/users/search?q=${encodeURIComponent(searchQuery)}`,
        { withCredentials: true }
      );
      setSearchResults(response.data.users || []);
    } catch (err) {
      console.error("Search error:", err);
      toast.error("Search failed");
    } finally {
      setSearching(false);
    }
  };

  const getThemeClass = () => {
    if (activeTab === "men") return "theme-men";
    if (activeTab === "women") return "theme-women";
    if (activeTab === "stars") return "theme-stars";
    return "theme-global";
  };

  const getButtonClass = () => {
    if (activeTab === "men") return "bg-white text-black hover:bg-gray-200";
    if (activeTab === "women") return "bg-white text-[#4A0404] hover:bg-gray-200";
    return "bg-black text-white hover:bg-gray-800";
  };

  return (
    <div className={`min-h-screen transition-bg ${getThemeClass()}`}>
      {/* Header */}
      <header className="border-b border-opacity-20 backdrop-blur-sm sticky top-0 z-50" style={{ borderColor: 'currentColor' }}>
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="font-italiana text-3xl sm:text-4xl" data-testid="looksy-logo">
            Looksy
          </h1>
          
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Search Users */}
            <Button
              data-testid="search-users-btn"
              onClick={() => setShowSearchDialog(true)}
              variant="ghost"
              size="icon"
              className="rounded-full"
              title="Search Users"
            >
              <Search className="w-4 h-4" />
            </Button>
            
            {/* Celebrity Posts */}
            <Button
              data-testid="celebrity-link"
              onClick={() => navigate("/celebrity")}
              variant="ghost"
              size="icon"
              className="rounded-full"
              title="Celebrity Posts"
            >
              <Crown className="w-4 h-4" />
            </Button>
            
            <Button
              data-testid="upload-btn"
              onClick={() => navigate("/upload")}
              className={`${getButtonClass()} rounded-full font-manrope font-semibold flex items-center gap-2`}
              size="sm"
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">Upload</span>
            </Button>
            
            {currentUser && (
              <Button
                data-testid="profile-btn"
                onClick={() => navigate(`/profile/${currentUser.user_id}`)}
                className={`${getButtonClass()} rounded-full`}
                size="icon"
              >
                <User className="w-4 h-4" />
              </Button>
            )}
            
            <Button
              data-testid="logout-btn"
              onClick={handleLogout}
              variant="ghost"
              size="icon"
              className="rounded-full"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
        
        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 py-2 flex items-center justify-center gap-6">
          <button
            data-testid="tab-all"
            onClick={() => { setActiveTab("all"); navigate("/dashboard"); }}
            className={`flex flex-col items-center gap-1 py-2 px-4 transition-opacity ${
              activeTab === "all" ? "opacity-100" : "opacity-50 hover:opacity-75"
            }`}
          >
            <Compass className="w-8 h-8" />
            <span className="font-manrope text-xs font-semibold">Discover</span>
          </button>
          
          <button
            data-testid="tab-men"
            onClick={() => { setActiveTab("men"); navigate("/men"); }}
            className={`flex flex-col items-center gap-1 py-2 px-4 transition-opacity ${
              activeTab === "men" ? "opacity-100" : "opacity-50 hover:opacity-75"
            }`}
          >
            <Spade className="w-8 h-8" />
            <span className="font-manrope text-xs font-semibold">Men</span>
          </button>
          
          <button
            data-testid="tab-women"
            onClick={() => { setActiveTab("women"); navigate("/women"); }}
            className={`flex flex-col items-center gap-1 py-2 px-4 transition-opacity ${
              activeTab === "women" ? "opacity-100" : "opacity-50 hover:opacity-75"
            }`}
          >
            <Heart className="w-8 h-8 fill-current" />
            <span className="font-manrope text-xs font-semibold">Women</span>
          </button>
          
          <button
            data-testid="tab-stars"
            onClick={() => { setActiveTab("stars"); navigate("/stars"); }}
            className={`flex flex-col items-center gap-1 py-2 px-4 transition-opacity ${
              activeTab === "stars" ? "opacity-100" : "opacity-50 hover:opacity-75"
            }`}
          >
            <Star className="w-8 h-8 fill-current" style={{ color: activeTab === "stars" ? "#FFD700" : "currentColor" }} />
            <span className="font-manrope text-xs font-semibold">Stars</span>
          </button>
        </div>
      </header>

      {/* Search Users Dialog */}
      <Dialog open={showSearchDialog} onOpenChange={setShowSearchDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-italiana text-2xl">Search Users</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="flex gap-2">
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name or email..."
                className="font-manrope"
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                data-testid="search-input"
              />
              <Button onClick={handleSearch} disabled={searching} data-testid="search-submit">
                {searching ? "..." : "Search"}
              </Button>
            </div>
            
            {searchResults.length > 0 && (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {searchResults.map((user) => (
                  <div
                    key={user.user_id}
                    onClick={() => {
                      navigate(`/profile/${user.user_id}`);
                      setShowSearchDialog(false);
                    }}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors"
                    data-testid={`search-result-${user.user_id}`}
                  >
                    {user.picture ? (
                      <img
                        src={user.picture.startsWith('http') ? user.picture : BACKEND_URL + user.picture}
                        alt={user.name}
                        className="w-10 h-10 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                        <User className="w-5 h-5 text-gray-500" />
                      </div>
                    )}
                    <div>
                      <p className="font-manrope font-semibold">{user.name}</p>
                      <p className="font-manrope text-xs text-gray-500">{user.category || "Fashion"}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {searchResults.length === 0 && searchQuery && !searching && (
              <p className="text-center text-gray-500 font-manrope py-4">No users found</p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-current"></div>
          </div>
        ) : posts.length === 0 ? (
          <div className="text-center py-20">
            <Upload className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p className="font-manrope text-lg opacity-70">No posts yet</p>
            <p className="font-manrope text-sm opacity-50 mt-2">Be the first to share your style!</p>
          </div>
        ) : (
          <div className={`grid gap-6 ${
            activeTab === "stars" 
              ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3" 
              : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          }`}>
            {posts.map((post) => (
              <PostCard 
                key={post.post_id} 
                post={post} 
                currentUserId={currentUser?.user_id}
                onDelete={handlePostDelete}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}