import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Camera, Edit2, Send, Plus, MessageSquare, UserPlus, UserCheck, Bookmark, Star, Wallet, CheckCircle, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import PostCard from "@/components/PostCard";
import CollaborationHub from "@/components/CollaborationHub";
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
      
      // Check if following
      if (currentUserRes.data.following) {
        setIsFollowing(currentUserRes.data.following.includes(userId));
      }
      
      // Fetch rewards info if own profile
      if (currentUserRes.data.user_id === userId) {
        try {
          const rewardsRes = await axios.get(`${BACKEND_URL}/api/rewards/info`, { withCredentials: true });
          setRewardsInfo(rewardsRes.data);
        } catch (err) {
          console.error("Error fetching rewards:", err);
        }
        
        // Fetch accepted collaborations
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

  const handlePostDelete = (postId) => {
    setPosts(posts.filter(p => p.post_id !== postId));
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
        { 
          withCredentials: true,
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );
      setUser({ ...user, picture: BACKEND_URL + response.data.picture });
      toast.success("Profile picture updated!");
    } catch (err) {
      console.error("Error uploading picture:", err);
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
      console.error("Error updating bio:", err);
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
        {
          to_user_id: userId,
          subject: collabSubject,
          message: collabMessage
        },
        { withCredentials: true }
      );
      toast.success("Collaboration request sent!");
      setCollaborateOpen(false);
      setCollabSubject("");
      setCollabMessage("");
    } catch (err) {
      console.error("Error sending collaboration:", err);
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
      
      // Update follower count
      setUser({
        ...user,
        followers: response.data.following 
          ? [...(user.followers || []), currentUser.user_id]
          : (user.followers || []).filter(id => id !== currentUser.user_id)
      });
    } catch (err) {
      console.error("Error toggling follow:", err);
      toast.error("Failed to update follow status");
    } finally {
      setFollowLoading(false);
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
  const bgColor = user.category === 'men' ? '#050505' : user.category === 'women' ? '#4A0404' : '#FFFFFF';
  const textColor = user.category === 'men' || user.category === 'women' ? '#FFFFFF' : '#000000';

  return (
    <div className="min-h-screen" style={{ backgroundColor: bgColor, color: textColor }}>
      <header className="border-b border-opacity-20 px-4 py-4 flex items-center justify-between sticky top-0 z-10" style={{ borderColor: textColor, backgroundColor: bgColor }}>
        <div className="flex items-center gap-4">
          <Button
            data-testid="back-btn"
            onClick={() => navigate(-1)}
            variant="ghost"
            size="icon"
            className="rounded-full"
            style={{ color: textColor }}
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <h1 className="font-italiana text-2xl">Profile</h1>
        </div>
        
        {/* Action Buttons */}
        {isOwnProfile && (
          <div className="flex items-center gap-2">
            <Button
              data-testid="favorites-btn"
              onClick={() => navigate('/favorites')}
              variant="ghost"
              size="icon"
              className="rounded-full"
              style={{ color: textColor }}
              title="My Favorites"
            >
              <Bookmark className="w-5 h-5" />
            </Button>
            <Button
              data-testid="add-post-btn"
              onClick={() => navigate('/upload')}
              className="rounded-full w-10 h-10 flex items-center justify-center"
              style={{ backgroundColor: textColor === '#FFFFFF' ? '#FFFFFF' : '#000000', color: bgColor }}
            >
              <Plus className="w-5 h-5" />
            </Button>
          </div>
        )}
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Profile Header */}
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6 mb-8">
          {/* Profile Picture */}
          <div className="relative">
            {user.picture ? (
              <img src={user.picture.startsWith('http') ? user.picture : BACKEND_URL + user.picture} alt={user.name} className="w-32 h-32 rounded-full object-cover" />
            ) : (
              <div className="w-32 h-32 rounded-full bg-gray-200 flex items-center justify-center">
                <span className="font-italiana text-4xl text-black">{user.name[0]}</span>
              </div>
            )}
            
            {isOwnProfile && (
              <label className="absolute bottom-0 right-0 bg-white rounded-full p-2 shadow-lg cursor-pointer hover:bg-gray-100 transition-colors">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleProfilePictureUpload}
                  className="hidden"
                  disabled={uploadingPicture}
                />
                <Camera className="w-5 h-5 text-black" />
              </label>
            )}
          </div>
          
          <div className="flex-1 text-center sm:text-left space-y-4">
            <div>
              <h2 className="font-italiana text-4xl mb-2">{user.name}</h2>
              {user.category && (
                <p className="font-manrope text-sm opacity-70 capitalize">{user.category}'s Fashion</p>
              )}
            </div>

            {/* Bio Section */}
            <div className="max-w-2xl">
              {user.bio ? (
                <div className="relative group">
                  <p className="font-manrope text-base opacity-90 leading-relaxed">{user.bio}</p>
                  {isOwnProfile && (
                    <Button
                      onClick={() => setEditBioOpen(true)}
                      variant="ghost"
                      size="icon"
                      className="absolute -top-2 -right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                      style={{ color: textColor }}
                    >
                      <Edit2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ) : isOwnProfile ? (
                <Button
                  onClick={() => setEditBioOpen(true)}
                  variant="outline"
                  className="font-manrope text-sm"
                  style={{ borderColor: textColor, color: textColor }}
                >
                  Add Bio
                </Button>
              ) : null}
            </div>
            
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-6">
              <div className="text-center sm:text-left">
                <p className="font-manrope text-2xl font-bold">{posts.length}</p>
                <p className="font-manrope text-sm opacity-70">Posts</p>
              </div>
              
              <div className="text-center sm:text-left">
                <p className="font-manrope text-2xl font-bold">{user.followers?.length || 0}</p>
                <p className="font-manrope text-sm opacity-70">Followers</p>
              </div>
              
              <div className="text-center sm:text-left">
                <p className="font-manrope text-2xl font-bold">{user.following?.length || 0}</p>
                <p className="font-manrope text-sm opacity-70">Following</p>
              </div>
            </div>
            
            {/* Action Boxes */}
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3">
              {isOwnProfile ? (
                <>
                  {/* Total Earnings - Only visible to owner */}
                  <div 
                    className="px-5 py-3 rounded-xl border border-opacity-20" 
                    style={{ borderColor: textColor, backgroundColor: 'rgba(255,255,255,0.05)' }}
                    data-testid="earnings-box"
                  >
                    <p className="font-manrope text-xs opacity-70 mb-1">Total Earnings</p>
                    <p className="font-italiana text-2xl">
                      €{user.earnings_eur?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                  
                  {/* Stars */}
                  <div 
                    className="px-5 py-3 rounded-xl border border-opacity-20" 
                    style={{ borderColor: textColor, backgroundColor: 'rgba(255,255,255,0.05)' }}
                  >
                    <p className="font-manrope text-xs opacity-70 mb-1">Stars</p>
                    <div className="flex items-center gap-2">
                      <Star className="w-5 h-5 text-yellow-400 fill-yellow-400" />
                      <p className="font-italiana text-2xl">{rewardsInfo?.stars || 0}</p>
                    </div>
                  </div>
                  
                  {/* Payout Points */}
                  <div 
                    className="px-5 py-3 rounded-xl cursor-pointer hover:bg-white/10 transition-colors" 
                    style={{ backgroundColor: 'rgba(255,255,255,0.05)', border: `1px solid ${textColor}20` }}
                    onClick={() => navigate('/rewards')}
                    data-testid="rewards-box"
                  >
                    <p className="font-manrope text-xs opacity-70 mb-1">Payout Balance</p>
                    <p className="font-italiana text-2xl">€{rewardsInfo?.payout_points_eur?.toFixed(2) || '0.00'}</p>
                    <p className="font-manrope text-xs opacity-50 mt-1 flex items-center gap-1">
                      <Wallet className="w-3 h-3" /> Tap to manage
                    </p>
                  </div>
                  
                  {rewardsInfo?.kyc_verified && (
                    <div className="flex items-center gap-1 px-3 py-1.5 bg-green-600/80 rounded-full">
                      <Shield className="w-3 h-3 text-white" />
                      <span className="font-manrope text-xs text-white">KYC Verified</span>
                    </div>
                  )}
                </>
              ) : (
                <>
                  {/* Follow Button */}
                  <Button
                    data-testid="follow-btn"
                    onClick={handleToggleFollow}
                    disabled={followLoading}
                    className="px-6 py-3 rounded-full font-manrope font-semibold flex items-center gap-2 transition-all"
                    style={{ 
                      backgroundColor: isFollowing ? 'transparent' : textColor,
                      color: isFollowing ? textColor : bgColor,
                      border: isFollowing ? `2px solid ${textColor}` : 'none'
                    }}
                  >
                    {isFollowing ? (
                      <>
                        <UserCheck className="w-4 h-4" />
                        Following
                      </>
                    ) : (
                      <>
                        <UserPlus className="w-4 h-4" />
                        Follow
                      </>
                    )}
                  </Button>
                  
                  {/* Simple Collaborate Button */}
                  <Button
                    onClick={() => setCollaborateOpen(true)}
                    className="px-6 py-3 rounded-full font-manrope font-semibold flex items-center gap-2"
                    style={{ backgroundColor: '#013220', color: '#FFFFFF' }}
                    data-testid="collaborate-btn"
                  >
                    <MessageSquare className="w-4 h-4" />
                    Collaborate
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Accepted Collaborations - Shown on profile */}
        {acceptedCollabs.length > 0 && (
          <div className="mb-8">
            <h3 className="font-italiana text-xl mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-400" />
              Active Collaborations
            </h3>
            <div className="flex flex-wrap gap-2">
              {acceptedCollabs.map((collab) => (
                <Badge 
                  key={collab.message_id}
                  className="px-3 py-1.5 font-manrope text-sm"
                  style={{ backgroundColor: 'rgba(255,255,255,0.1)', color: textColor }}
                >
                  {collab.from_user_name || collab.to_user_name}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Posts Grid */}
        <div>
          <h3 className="font-italiana text-2xl mb-6">Posts</h3>
          {posts.length === 0 ? (
            <div className="text-center py-12">
              <p className="font-manrope opacity-70">No posts yet</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
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
        </div>
      </main>

      {/* Edit Bio Dialog */}
      <Dialog open={editBioOpen} onOpenChange={setEditBioOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Bio</DialogTitle>
            <DialogDescription>
              Tell people about yourself and your fashion style
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              value={bioText}
              onChange={(e) => setBioText(e.target.value)}
              placeholder="Fashion enthusiast, style creator, trendsetter..."
              rows={4}
              maxLength={200}
              className="font-manrope"
            />
            <p className="text-xs text-gray-500 mt-2">{bioText.length}/200 characters</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditBioOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveBio} className="bg-black text-white hover:bg-gray-800">Save Bio</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Collaboration Dialog */}
      <Dialog open={collaborateOpen} onOpenChange={setCollaborateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send Collaboration Request</DialogTitle>
            <DialogDescription>
              Send a message to {user.name} about working together
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="font-manrope text-sm font-semibold mb-2 block">Subject</label>
              <Input
                value={collabSubject}
                onChange={(e) => setCollabSubject(e.target.value)}
                placeholder="Brand partnership, photo shoot, etc."
                className="font-manrope"
              />
            </div>
            <div>
              <label className="font-manrope text-sm font-semibold mb-2 block">Message</label>
              <Textarea
                value={collabMessage}
                onChange={(e) => setCollabMessage(e.target.value)}
                placeholder="Hi! I'd love to collaborate with you on..."
                rows={5}
                className="font-manrope"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCollaborateOpen(false)}>Cancel</Button>
            <Button 
              onClick={handleSendCollaboration} 
              className="bg-[#013220] text-white hover:bg-[#024a30] flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Send Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}