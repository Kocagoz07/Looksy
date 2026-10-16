import { useCallback, useEffect, useState } from "react";
import { Flame, Users, Compass } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import PostCard from "@/components/PostCard";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const FEW_POSTS = 6;
const GRID = "grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4";

const TabButton = ({ active, onClick, icon: Icon, children, testId }) => (
  <button type="button" data-testid={testId} onClick={onClick}
    className={`flex items-center gap-2 px-5 py-2 rounded-full font-manrope text-sm transition-colors duration-200 ${
      active ? "bg-black text-white" : "text-gray-500 hover:text-black"}`}>
    <Icon className="w-4 h-4" /> {children}
  </button>
);

const PostGrid = ({ posts, currentUserId, onDelete, testId }) => (
  <div className={GRID} data-testid={testId}>
    {posts.map((p) => <PostCard key={p.post_id} post={p} currentUserId={currentUserId} onDelete={onDelete} />)}
  </div>
);

export const HomeFeed = ({ currentUser }) => {
  const [tab, setTab] = useState("following");
  const [posts, setPosts] = useState(null);
  const [popular, setPopular] = useState([]);

  const load = useCallback(async () => {
    setPosts(null);
    setPopular([]);
    const get = (path) => axios.get(`${BACKEND_URL}${path}`, { withCredentials: true }).then((r) => r.data.posts);
    try {
      if (tab === "discover") {
        setPosts(await get("/api/feed/popular"));
        return;
      }
      const following = await get("/api/feed/following");
      setPosts(following);
      if (following.length < FEW_POSTS) setPopular(await get("/api/feed/popular?exclude_following=true"));
    } catch {
      setPosts([]);
      toast.error("Failed to load posts");
    }
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  const onDelete = (id) => {
    setPosts((ps) => ps.filter((p) => p.post_id !== id));
    setPopular((ps) => ps.filter((p) => p.post_id !== id));
  };

  return (
    <div data-testid="home-feed">
      <div className="flex gap-1 mb-8 p-1 rounded-full border border-gray-200 w-fit">
        <TabButton testId="feed-tab-following" active={tab === "following"} onClick={() => setTab("following")} icon={Users}>Following</TabButton>
        <TabButton testId="feed-tab-discover" active={tab === "discover"} onClick={() => setTab("discover")} icon={Compass}>Discover</TabButton>
      </div>

      {posts === null ? (
        <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-current" /></div>
      ) : (
        <>
          {posts.length > 0 ? (
            <PostGrid posts={posts} currentUserId={currentUser?.user_id} onDelete={onDelete} testId={`feed-grid-${tab}`} />
          ) : (
            <div data-testid="feed-empty" className="py-12 text-center font-manrope">
              <p className="text-lg opacity-70">{tab === "following" ? "Your feed is quiet" : "No popular looks yet"}</p>
              <p className="text-sm opacity-50 mt-2">
                {tab === "following" ? "Follow creators to see their looks here." : "Be the first to share your style!"}
              </p>
            </div>
          )}
          {popular.length > 0 && (
            <section className="mt-14" data-testid="popular-for-you">
              <h2 className="flex items-center gap-2 font-italiana text-3xl mb-1"><Flame className="w-6 h-6" /> Popular for you</h2>
              <p className="font-manrope text-sm text-gray-500 mb-6">Most loved looks of the last two weeks</p>
              <PostGrid posts={popular} currentUserId={currentUser?.user_id} onDelete={onDelete} testId="popular-grid" />
            </section>
          )}
        </>
      )}
    </div>
  );
};
