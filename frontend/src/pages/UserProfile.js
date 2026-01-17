import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Briefcase, DollarSign, CheckCircle, Wallet, Camera, Edit2, Send, Plus, MessageSquare } from "lucide-react";
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
  const [editBioOpen, setEditBioOpen] = useState(false);
  const [bioText, setBioText] = useState("");
  const [collaborateOpen, setCollaborateOpen] = useState(false);
  const [collabSubject, setCollabSubject] = useState("");
  const [collabMessage, setCollabMessage] = useState("");
  const [uploadingPicture, setUploadingPicture] = useState(false);

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
        
        {/* Add Post Button */}
        {isOwnProfile && (
          <Button
            data-testid="add-post-btn"
            onClick={() => navigate('/upload')}
            className="rounded-full w-12 h-12 flex items-center justify-center"
            style={{ backgroundColor: textColor === '#FFFFFF' ? '#FFFFFF' : '#000000', color: bgColor }}
          >
            <Plus className="w-6 h-6" />
          </Button>
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
                  <div 
                    className="px-6 py-3 rounded-lg border border-white border-opacity-20 cursor-pointer hover:border-opacity-40 transition-all" 
                    style={{ backgroundColor: 'transparent' }}
                    data-testid="earnings-box"
                    onClick={() => navigate('/payouts')}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <DollarSign className="w-4 h-4" style={{ color: '#FFFFFF' }} />
                      <p className="font-manrope text-xs font-semibold" style={{ color: '#FFFFFF' }}>Total Earnings</p>
                    </div>
                    <p className="font-italiana text-2xl" style={{ color: '#FFFFFF' }}>
                      €{user.earnings_eur?.toFixed(2) || '0.00'}
                    </p>
                    <p className="font-manrope text-xs opacity-70" style={{ color: '#FFFFFF' }}>
                      ${user.earnings?.toFixed(2) || '0.00'} USD
                    </p>
                  </div>
                  
                  {user.kyc_verified && (
                    <div className="flex items-center gap-2 px-4 py-2 bg-green-600 rounded-lg">
                      <CheckCircle className="w-4 h-4 text-white" />
                      <span className="font-manrope text-xs font-semibold text-white">Verified</span>
                    </div>
                  )}
                  
                  <Button
                    onClick={() => navigate('/payouts')}
                    className="px-6 py-3 rounded-lg font-manrope font-semibold flex items-center gap-2"
                    style={{ backgroundColor: '#013220', color: '#FFFFFF' }}
                  >
                    <Wallet className="w-4 h-4" />
                    Payouts
                  </Button>
                </>
              ) : (
                /* Collaboration Box for Other Users */
                <div 
                  className="cursor-pointer group"
                  onClick={() => setCollaborateOpen(true)}
                  data-testid="collaborate-box"
                >
                  <div 
                    className="px-8 py-4 rounded-xl transition-all hover:shadow-lg relative overflow-hidden"
                    style={{ backgroundColor: '#013220' }}
                  >
                    {/* Decorative Background Pattern */}
                    <div className="absolute inset-0 opacity-5">
                      <div className="absolute top-0 right-0 w-20 h-20 bg-white rounded-full -translate-y-1/2 translate-x-1/2"></div>
                      <div className="absolute bottom-0 left-0 w-16 h-16 bg-white rounded-full translate-y-1/2 -translate-x-1/2"></div>
                    </div>
                    
                    <div className="relative z-10">
                      <div className="flex items-center gap-3 mb-2">
                        <MessageSquare className="w-6 h-6 text-white" />
                        <h3 className="font-italiana text-xl text-white">Collaborate</h3>
                      </div>
                      <p className="font-manrope text-sm text-white opacity-90 mb-3">
                        Partner with {user.name.split(' ')[0]} for your next project
                      </p>
                      <div className="flex items-center gap-2 text-white opacity-75 group-hover:opacity-100 transition-opacity">
                        <span className="font-manrope text-xs font-semibold">Send Message</span>
                        <Send className="w-4 h-4" />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

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