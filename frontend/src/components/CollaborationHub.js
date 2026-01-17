import { useState, useEffect } from "react";
import { 
  MessageSquare, 
  Send, 
  CheckCircle, 
  XCircle, 
  Clock, 
  TrendingUp,
  Filter,
  Search,
  Sparkles,
  Mail,
  User,
  BarChart3,
  Wand2,
  Loader2,
  ChevronDown,
  ChevronUp,
  Brain,
  Zap
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// AI-powered categorization (local fallback)
const categorizeRequest = (subject, message) => {
  const text = `${subject} ${message}`.toLowerCase();
  
  if (text.includes('brand') || text.includes('partnership') || text.includes('sponsor')) {
    return { category: 'Brand Partnership', icon: '🏷️', color: 'bg-purple-100 text-purple-700' };
  }
  if (text.includes('influencer') || text.includes('collaboration') || text.includes('collab')) {
    return { category: 'Influencer Collab', icon: '🤝', color: 'bg-blue-100 text-blue-700' };
  }
  if (text.includes('magazine') || text.includes('editorial') || text.includes('feature')) {
    return { category: 'Editorial', icon: '📰', color: 'bg-green-100 text-green-700' };
  }
  if (text.includes('photo') || text.includes('shoot') || text.includes('campaign')) {
    return { category: 'Photo Shoot', icon: '📸', color: 'bg-orange-100 text-orange-700' };
  }
  return { category: 'General', icon: '💼', color: 'bg-gray-100 text-gray-700' };
};

// AI-powered priority scoring (local fallback)
const calculatePriority = (subject, message, from_user_name) => {
  let score = 0;
  const text = `${subject} ${message} ${from_user_name}`.toLowerCase();
  
  if (text.includes('urgent') || text.includes('asap') || text.includes('important')) score += 3;
  if (text.includes('exclusive') || text.includes('limited')) score += 2;
  if (text.includes('brand') || text.includes('official')) score += 2;
  if (text.includes('paid') || text.includes('compensation') || text.includes('fee')) score += 3;
  
  if (score >= 5) return { level: 'High', color: 'bg-red-100 text-red-700 border-red-300' };
  if (score >= 3) return { level: 'Medium', color: 'bg-yellow-100 text-yellow-700 border-yellow-300' };
  return { level: 'Low', color: 'bg-green-100 text-green-700 border-green-300' };
};

export default function CollaborationHub({ userId, textColor = '#000000', bgColor = '#FFFFFF' }) {
  const [collaborations, setCollaborations] = useState([]);
  const [filteredCollabs, setFilteredCollabs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("received");
  const [searchQuery, setSearchQuery] = useState("");
  const [filterPriority, setFilterPriority] = useState("all");
  const [filterCategory, setFilterCategory] = useState("all");
  
  // AI Feature States
  const [selectedCollab, setSelectedCollab] = useState(null);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiReplies, setAiReplies] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [showAiPanel, setShowAiPanel] = useState(false);
  const [batchAnalysis, setBatchAnalysis] = useState(null);
  const [batchLoading, setBatchLoading] = useState(false);
  const [expandedCollab, setExpandedCollab] = useState(null);

  useEffect(() => {
    fetchCollaborations();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [collaborations, searchQuery, filterPriority, filterCategory, activeTab]);

  const fetchCollaborations = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/collaborations/inbox`, { 
        withCredentials: true 
      });
      setCollaborations(response.data);
    } catch (err) {
      console.error("Error fetching collaborations:", err);
      toast.error("Failed to load collaborations");
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...collaborations];

    if (activeTab === "unread") {
      filtered = filtered.filter(c => !c.read);
    } else if (activeTab === "read") {
      filtered = filtered.filter(c => c.read);
    }

    if (searchQuery) {
      filtered = filtered.filter(c => 
        c.from_user_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.message.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    if (filterPriority !== "all") {
      filtered = filtered.filter(c => {
        const priority = calculatePriority(c.subject, c.message, c.from_user_name);
        return priority.level.toLowerCase() === filterPriority;
      });
    }

    if (filterCategory !== "all") {
      filtered = filtered.filter(c => {
        const cat = categorizeRequest(c.subject, c.message);
        return cat.category === filterCategory;
      });
    }

    setFilteredCollabs(filtered);
  };

  const markAsRead = async (messageId) => {
    try {
      await axios.patch(
        `${BACKEND_URL}/api/collaborations/${messageId}/read`,
        {},
        { withCredentials: true }
      );
      
      setCollaborations(collaborations.map(c => 
        c.message_id === messageId ? { ...c, read: true } : c
      ));
    } catch (err) {
      console.error("Error marking as read:", err);
    }
  };

  // AI Analysis Function
  const analyzeWithAI = async (collab) => {
    setSelectedCollab(collab);
    setShowAiPanel(true);
    setAiLoading(true);
    setAiAnalysis(null);
    setAiReplies(null);

    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/collaborations/ai/analyze`,
        {
          subject: collab.subject,
          message: collab.message,
          from_user_name: collab.from_user_name
        },
        { withCredentials: true }
      );
      setAiAnalysis(response.data);
      toast.success("AI analysis complete!");
    } catch (err) {
      console.error("AI analysis error:", err);
      toast.error("AI analysis failed");
    } finally {
      setAiLoading(false);
    }
  };

  // AI Reply Suggestions Function
  const getAIReplySuggestions = async (collab, tone = "professional") => {
    setAiLoading(true);

    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/collaborations/ai/suggest-reply`,
        {
          subject: collab.subject,
          message: collab.message,
          from_user_name: collab.from_user_name,
          reply_tone: tone
        },
        { withCredentials: true }
      );
      setAiReplies(response.data.replies);
      toast.success("Reply suggestions ready!");
    } catch (err) {
      console.error("AI reply error:", err);
      toast.error("Failed to generate replies");
    } finally {
      setAiLoading(false);
    }
  };

  // Batch Analysis Function
  const runBatchAnalysis = async () => {
    setBatchLoading(true);
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/collaborations/ai/batch-analyze`,
        {},
        { withCredentials: true }
      );
      setBatchAnalysis(response.data);
      toast.success("Batch analysis complete!");
    } catch (err) {
      console.error("Batch analysis error:", err);
      toast.error("Batch analysis failed");
    } finally {
      setBatchLoading(false);
    }
  };

  const stats = {
    total: collaborations.length,
    unread: collaborations.filter(c => !c.read).length,
    highPriority: collaborations.filter(c => {
      const priority = calculatePriority(c.subject, c.message, c.from_user_name);
      return priority.level === 'High';
    }).length
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2" style={{ borderColor: textColor }}></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl" style={{ backgroundColor: 'rgba(1, 50, 32, 0.1)' }}>
            <Brain className="w-6 h-6" style={{ color: '#013220' }} />
          </div>
          <div>
            <h2 className="font-italiana text-2xl" style={{ color: textColor }}>
              AI Collaboration Hub
            </h2>
            <p className="font-manrope text-sm opacity-70" style={{ color: textColor }}>
              Powered by GPT-4o-mini
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* AI Batch Analysis Button */}
          {stats.unread > 0 && (
            <Button
              onClick={runBatchAnalysis}
              disabled={batchLoading}
              className="rounded-full font-manrope font-semibold flex items-center gap-2"
              style={{ backgroundColor: '#6366f1', color: '#FFFFFF' }}
              data-testid="batch-analyze-btn"
            >
              {batchLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              Analyze All ({stats.unread})
            </Button>
          )}
          
          <div className="text-center px-4 py-2 rounded-lg" style={{ backgroundColor: 'rgba(255,255,255,0.1)', borderWidth: '1px', borderColor: textColor }}>
            <p className="font-italiana text-2xl" style={{ color: textColor }}>{stats.total}</p>
            <p className="font-manrope text-xs opacity-70" style={{ color: textColor }}>Total</p>
          </div>
          <div className="text-center px-4 py-2 rounded-lg" style={{ backgroundColor: 'rgba(59, 130, 246, 0.1)', borderWidth: '1px', borderColor: '#3b82f6' }}>
            <p className="font-italiana text-2xl text-blue-600">{stats.unread}</p>
            <p className="font-manrope text-xs text-blue-600">Unread</p>
          </div>
          <div className="text-center px-4 py-2 rounded-lg" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', borderWidth: '1px', borderColor: '#ef4444' }}>
            <p className="font-italiana text-2xl text-red-600">{stats.highPriority}</p>
            <p className="font-manrope text-xs text-red-600">Priority</p>
          </div>
        </div>
      </div>

      {/* Batch Analysis Results */}
      {batchAnalysis && (
        <div 
          className="p-4 rounded-xl border"
          style={{ backgroundColor: 'rgba(99, 102, 241, 0.1)', borderColor: '#6366f1' }}
        >
          <div className="flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-indigo-500 mt-1" />
            <div>
              <h4 className="font-manrope font-bold text-indigo-600 mb-2">AI Inbox Summary</h4>
              <p className="font-manrope text-sm mb-2" style={{ color: textColor }}>
                {batchAnalysis.overall_summary}
              </p>
              {batchAnalysis.recommendations && (
                <ul className="list-disc list-inside text-sm opacity-80" style={{ color: textColor }}>
                  {batchAnalysis.recommendations.map((rec, i) => (
                    <li key={i} className="font-manrope">{rec}</li>
                  ))}
                </ul>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setBatchAnalysis(null)}
                className="mt-2 text-indigo-600"
              >
                Dismiss
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search collaborations..."
            className="pl-10 font-manrope rounded-full"
            style={{ backgroundColor: 'rgba(255,255,255,0.9)' }}
          />
        </div>
        
        <Select value={filterPriority} onValueChange={setFilterPriority}>
          <SelectTrigger className="w-[150px] rounded-full font-manrope" style={{ backgroundColor: 'rgba(255,255,255,0.9)' }}>
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Priority</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>

        <Select value={filterCategory} onValueChange={setFilterCategory}>
          <SelectTrigger className="w-[180px] rounded-full font-manrope" style={{ backgroundColor: 'rgba(255,255,255,0.9)' }}>
            <Sparkles className="w-4 h-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            <SelectItem value="Brand Partnership">Brand Partnership</SelectItem>
            <SelectItem value="Influencer Collab">Influencer Collab</SelectItem>
            <SelectItem value="Editorial">Editorial</SelectItem>
            <SelectItem value="Photo Shoot">Photo Shoot</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3" style={{ backgroundColor: 'rgba(255,255,255,0.1)' }}>
          <TabsTrigger value="received" className="font-manrope">
            All ({stats.total})
          </TabsTrigger>
          <TabsTrigger value="unread" className="font-manrope">
            Unread ({stats.unread})
          </TabsTrigger>
          <TabsTrigger value="read" className="font-manrope">
            Read ({stats.total - stats.unread})
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6 space-y-4">
          {filteredCollabs.length === 0 ? (
            <div className="text-center py-12">
              <Mail className="w-16 h-16 mx-auto mb-4 opacity-30" style={{ color: textColor }} />
              <p className="font-manrope opacity-70" style={{ color: textColor }}>
                {searchQuery || filterPriority !== "all" || filterCategory !== "all" 
                  ? "No collaborations match your filters" 
                  : "No collaboration requests yet"}
              </p>
            </div>
          ) : (
            filteredCollabs.map((collab) => {
              const category = categorizeRequest(collab.subject, collab.message);
              const priority = calculatePriority(collab.subject, collab.message, collab.from_user_name);
              const isExpanded = expandedCollab === collab.message_id;
              
              return (
                <div
                  key={collab.message_id}
                  className="p-6 rounded-2xl transition-all hover:shadow-lg"
                  style={{
                    backgroundColor: collab.read ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.1)',
                    borderWidth: '1px',
                    borderColor: collab.read ? 'rgba(255,255,255,0.1)' : textColor,
                  }}
                  data-testid={`collab-card-${collab.message_id}`}
                >
                  <div className="flex items-start gap-4">
                    {/* User Picture */}
                    {collab.from_user_picture ? (
                      <img
                        src={collab.from_user_picture.startsWith('http') ? collab.from_user_picture : BACKEND_URL + collab.from_user_picture}
                        alt={collab.from_user_name}
                        className="w-14 h-14 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-14 h-14 rounded-full bg-gray-200 flex items-center justify-center">
                        <User className="w-7 h-7 text-gray-600" />
                      </div>
                    )}

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4 mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-manrope font-bold text-lg" style={{ color: textColor }}>
                              {collab.from_user_name}
                            </h4>
                            {!collab.read && (
                              <Badge className="bg-blue-500 text-white text-xs">New</Badge>
                            )}
                          </div>
                          <p className="font-manrope font-semibold opacity-90" style={{ color: textColor }}>
                            {collab.subject}
                          </p>
                        </div>
                        
                        <div className="flex flex-col items-end gap-2">
                          <Badge className={`${priority.color} border font-manrope font-semibold`}>
                            {priority.level} Priority
                          </Badge>
                          <Badge className={category.color}>
                            {category.icon} {category.category}
                          </Badge>
                        </div>
                      </div>

                      <p className="font-manrope leading-relaxed opacity-80 mb-4" style={{ color: textColor }}>
                        {collab.message}
                      </p>

                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <p className="font-manrope text-xs opacity-50" style={{ color: textColor }}>
                          {new Date(collab.created_at).toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric', 
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </p>

                        <div className="flex items-center gap-2">
                          {/* AI Analyze Button */}
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => analyzeWithAI(collab)}
                            className="rounded-full font-manrope font-semibold flex items-center gap-1"
                            data-testid={`ai-analyze-btn-${collab.message_id}`}
                          >
                            <Wand2 className="w-4 h-4" />
                            AI Analyze
                          </Button>
                          
                          {!collab.read && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => markAsRead(collab.message_id)}
                              className="rounded-full font-manrope"
                            >
                              <CheckCircle className="w-4 h-4 mr-1" />
                              Mark Read
                            </Button>
                          )}
                          
                          <Button
                            size="sm"
                            className="rounded-full font-manrope font-semibold"
                            style={{ backgroundColor: '#013220', color: '#FFFFFF' }}
                          >
                            <Send className="w-4 h-4 mr-2" />
                            Reply
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </TabsContent>
      </Tabs>

      {/* AI Analysis Dialog */}
      <Dialog open={showAiPanel} onOpenChange={setShowAiPanel}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="font-italiana text-2xl flex items-center gap-2">
              <Brain className="w-6 h-6 text-indigo-600" />
              AI Analysis
            </DialogTitle>
            <DialogDescription className="font-manrope">
              AI-powered insights for this collaboration request
            </DialogDescription>
          </DialogHeader>

          {selectedCollab && (
            <div className="space-y-4 mt-4">
              {/* Original Message Summary */}
              <div className="p-3 rounded-lg bg-gray-50">
                <p className="font-manrope text-sm">
                  <span className="font-semibold">From:</span> {selectedCollab.from_user_name}
                </p>
                <p className="font-manrope text-sm">
                  <span className="font-semibold">Subject:</span> {selectedCollab.subject}
                </p>
              </div>

              {aiLoading && !aiAnalysis && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
                  <span className="ml-3 font-manrope">Analyzing with AI...</span>
                </div>
              )}

              {/* AI Analysis Results */}
              {aiAnalysis && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-indigo-50 border border-indigo-200">
                    <h4 className="font-manrope font-bold text-indigo-700 mb-2 flex items-center gap-2">
                      <Sparkles className="w-4 h-4" />
                      AI Summary
                    </h4>
                    <p className="font-manrope text-sm text-gray-700">{aiAnalysis.summary}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
                      <p className="font-manrope text-xs text-purple-600 mb-1">Request Type</p>
                      <p className="font-manrope font-semibold text-purple-800">{aiAnalysis.request_type}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-orange-50 border border-orange-200">
                      <p className="font-manrope text-xs text-orange-600 mb-1">AI Priority</p>
                      <p className="font-manrope font-semibold text-orange-800">{aiAnalysis.priority}</p>
                    </div>
                  </div>

                  {aiAnalysis.action_items && (
                    <div className="p-4 rounded-xl bg-green-50 border border-green-200">
                      <h4 className="font-manrope font-bold text-green-700 mb-2">Recommended Actions</h4>
                      <ul className="list-disc list-inside space-y-1">
                        {aiAnalysis.action_items.map((item, i) => (
                          <li key={i} className="font-manrope text-sm text-gray-700">{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Reply Suggestions Section */}
              <div className="border-t pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-manrope font-bold flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    AI Reply Suggestions
                  </h4>
                  <div className="flex items-center gap-2">
                    <Select defaultValue="professional" onValueChange={(tone) => getAIReplySuggestions(selectedCollab, tone)}>
                      <SelectTrigger className="w-[140px] h-8 text-xs">
                        <SelectValue placeholder="Tone" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="professional">Professional</SelectItem>
                        <SelectItem value="friendly">Friendly</SelectItem>
                        <SelectItem value="brief">Brief</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      size="sm"
                      onClick={() => getAIReplySuggestions(selectedCollab)}
                      disabled={aiLoading}
                      className="bg-indigo-600 text-white"
                    >
                      {aiLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Generate"}
                    </Button>
                  </div>
                </div>

                {aiReplies && (
                  <div className="space-y-3">
                    {aiReplies.map((reply, i) => (
                      <div 
                        key={i}
                        className="p-3 rounded-lg border hover:bg-gray-50 cursor-pointer transition-colors"
                        onClick={() => {
                          navigator.clipboard.writeText(reply.text);
                          toast.success("Reply copied to clipboard!");
                        }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="outline" className="capitalize text-xs">
                            {reply.type}
                          </Badge>
                          <span className="text-xs text-gray-400">Click to copy</span>
                        </div>
                        <p className="font-manrope text-sm">{reply.text}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
