import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { 
  ArrowLeft, Send, MoreVertical, Phone, Video, 
  Image, Smile, Paperclip, Check, CheckCheck, Clock
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { ScrollArea } from '../components/ui/scroll-area';
import { MessageContent } from '../components/SharedPostMessage';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';

const API = process.env.REACT_APP_BACKEND_URL;

const ChatPage = ({ user }) => {
  const navigate = useNavigate();
  const { conversationId } = useParams();
  const [searchParams] = useSearchParams();
  const targetUserId = searchParams.get('user');
  
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [typingUsers, setTypingUsers] = useState({});
  const [ws, setWs] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentUser, setCurrentUser] = useState(user);
  
  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);
  const inputRef = useRef(null);
  const startedConversationRef = useRef(false);

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Connect to WebSocket
  useEffect(() => {
    if (!user) return;

    const wsUrl = API.replace('https://', 'wss://').replace('http://', 'ws://') + '/ws/chat';
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('Chat WebSocket connected');
      // Send auth
      const sessionToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('session_token='))
        ?.split('=')[1];
      
      if (sessionToken) {
        socket.send(JSON.stringify({ type: 'auth', token: sessionToken }));
      }
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWsMessage(data);
    };

    socket.onclose = () => {
      console.log('Chat WebSocket disconnected');
      setIsConnected(false);
    };

    setWs(socket);

    return () => {
      socket.close();
    };
  }, [user]);

  const handleWsMessage = (data) => {
    switch (data.type) {
      case 'connected':
        setIsConnected(true);
        break;
      
      case 'message:new':
        if (activeConversation?.conversation_id === data.message.conversation_id) {
          setMessages(prev => [...prev, data.message]);
        }
        // Update conversation list
        setConversations(prev => {
          const updated = prev.map(conv => {
            if (conv.conversation_id === data.message.conversation_id) {
              return {
                ...conv,
                last_message: {
                  content: data.message.content,
                  sender_id: data.message.sender_id,
                  sent_at: data.message.created_at
                },
                updated_at: data.message.created_at
              };
            }
            return conv;
          });
          return updated.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        });
        break;
      
      case 'message:sent':
        // Update temp message with real one
        setMessages(prev => prev.map(m => 
          m.temp_id ? { ...data.message, temp_id: undefined } : m
        ));
        break;
      
      case 'typing:update':
        setTypingUsers(prev => ({
          ...prev,
          [data.conversation_id]: {
            ...prev[data.conversation_id],
            [data.user_id]: data.is_typing
          }
        }));
        break;
      
      default:
        break;
    }
  };

  // Fetch conversations
  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const response = await axios.get(`${API}/api/chat/conversations`, {
          withCredentials: true
        });
        setConversations(response.data.conversations || []);
      } catch (error) {
        console.error('Error fetching conversations:', error);
      } finally {
        setLoading(false);
      }
    };

    if (currentUser) {
      fetchConversations();
    }
  }, [currentUser]);

  // Fetch current user if not passed
  useEffect(() => {
    const fetchCurrentUser = async () => {
      if (!user) {
        try {
          const response = await axios.get(`${API}/api/auth/me`, { withCredentials: true });
          setCurrentUser(response.data);
        } catch (error) {
          console.error('Error fetching user:', error);
        }
      }
    };
    fetchCurrentUser();
  }, [user]);

  // Start conversation from ?user= param
  useEffect(() => {
    if (targetUserId && !startedConversationRef.current && currentUser && !loading) {
      startedConversationRef.current = true;
      startConversationWithUser(targetUserId);
    }
  }, [targetUserId, currentUser, loading]);

  const startConversationWithUser = async (userId) => {
    try {
      const response = await axios.post(`${API}/api/chat/conversations/direct`, {
        user_id: userId
      }, { withCredentials: true });
      
      const conversation = response.data;
      
      // Add to conversations if not exists
      setConversations(prev => {
        if (!prev.find(c => c.conversation_id === conversation.conversation_id)) {
          return [conversation, ...prev];
        }
        return prev;
      });
      
      selectConversation(conversation);
      
      // Clear the query param
      navigate(`/chat/${conversation.conversation_id}`, { replace: true });
    } catch (error) {
      console.error('Error starting conversation:', error);
    }
  };

  // Load conversation from URL param
  useEffect(() => {
    if (conversationId && conversations.length > 0 && !targetUserId) {
      const conv = conversations.find(c => c.conversation_id === conversationId);
      if (conv) {
        selectConversation(conv);
      }
    }
  }, [conversationId, conversations]);

  // Select a conversation and load messages
  const selectConversation = async (conversation) => {
    setActiveConversation(conversation);
    setMessages([]);
    
    try {
      const response = await axios.get(
        `${API}/api/chat/conversations/${conversation.conversation_id}/messages`,
        { withCredentials: true }
      );
      setMessages(response.data.messages || []);
      
      // Mark as read
      await axios.post(
        `${API}/api/chat/conversations/${conversation.conversation_id}/read`,
        {},
        { withCredentials: true }
      );
      
      // Update URL
      navigate(`/chat/${conversation.conversation_id}`, { replace: true });
    } catch (error) {
      console.error('Error loading messages:', error);
    }
    
    // Focus input
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  // Effective user (for currentUser fallback)
  const effectiveUser = currentUser || user;

  // Send message
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !activeConversation || sendingMessage) return;

    const content = newMessage.trim();
    setNewMessage('');
    setSendingMessage(true);

    // Optimistic update
    const tempMessage = {
      message_id: `temp_${Date.now()}`,
      temp_id: true,
      conversation_id: activeConversation.conversation_id,
      sender_id: effectiveUser?.user_id,
      sender_name: effectiveUser?.name,
      sender_picture: effectiveUser?.picture,
      content,
      type: 'text',
      created_at: new Date().toISOString(),
      sending: true
    };
    setMessages(prev => [...prev, tempMessage]);

    // Send via WebSocket if connected
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'message:send',
        conversation_id: activeConversation.conversation_id,
        content
      }));
      setSendingMessage(false);
    } else {
      // Fallback to REST
      try {
        const response = await axios.post(
          `${API}/api/chat/conversations/${activeConversation.conversation_id}/messages`,
          { content },
          { withCredentials: true }
        );
        setMessages(prev => prev.map(m => 
          m.temp_id ? response.data : m
        ));
      } catch (error) {
        console.error('Error sending message:', error);
        setMessages(prev => prev.map(m =>
          m.temp_id ? { ...m, sending: false, failed: true } : m
        ));
      } finally {
        setSendingMessage(false);
      }
    }

    // Stop typing indicator
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'typing:stop',
        conversation_id: activeConversation.conversation_id
      }));
    }
  };

  // Handle typing
  const handleTyping = (e) => {
    setNewMessage(e.target.value);
    
    if (!activeConversation || !ws || ws.readyState !== WebSocket.OPEN) return;

    // Send typing start
    ws.send(JSON.stringify({
      type: 'typing:start',
      conversation_id: activeConversation.conversation_id
    }));

    // Clear previous timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set timeout to stop typing
    typingTimeoutRef.current = setTimeout(() => {
      ws.send(JSON.stringify({
        type: 'typing:stop',
        conversation_id: activeConversation.conversation_id
      }));
    }, 2000);
  };

  // Format time
  const formatMessageTime = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 24 * 60 * 60 * 1000) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diff < 7 * 24 * 60 * 60 * 1000) {
      return date.toLocaleDateString([], { weekday: 'short' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  // Get other user's typing status
  const isOtherUserTyping = () => {
    if (!activeConversation) return false;
    const typing = typingUsers[activeConversation.conversation_id];
    if (!typing) return false;
    return Object.entries(typing).some(([uid, isTyping]) => uid !== effectiveUser?.user_id && isTyping);
  };

  if (!effectiveUser && !loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <p className="text-gray-500">Please log in to access messages</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex" style={{ fontFamily: '"Italiana", serif' }}>
      {/* Conversations Sidebar */}
      <div className={`w-full md:w-80 lg:w-96 border-r border-gray-200 flex flex-col ${activeConversation ? 'hidden md:flex' : 'flex'}`}>
        {/* Header */}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <h1 className="text-xl font-semibold">Messages</h1>
          </div>
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-300'}`} title={isConnected ? 'Connected' : 'Disconnected'} />
        </div>

        {/* Conversations List */}
        <ScrollArea className="flex-1">
          {loading ? (
            <div className="p-4 text-center text-gray-500">Loading...</div>
          ) : conversations.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-gray-500 mb-2">No conversations yet</p>
              <p className="text-sm text-gray-400">Start chatting with someone from their profile</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {conversations.map((conv) => {
                const otherUser = conv.other_user || {};
                const lastMsg = conv.last_message;
                const isActive = activeConversation?.conversation_id === conv.conversation_id;
                
                return (
                  <div
                    key={conv.conversation_id}
                    onClick={() => selectConversation(conv)}
                    className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${isActive ? 'bg-gray-100' : ''}`}
                    data-testid={`conversation-${conv.conversation_id}`}
                  >
                    <div className="flex items-center gap-3">
                      <Avatar className="w-12 h-12">
                        <AvatarImage src={otherUser.picture ? `${API}${otherUser.picture}` : undefined} />
                        <AvatarFallback className="bg-gray-200 text-gray-600">
                          {otherUser.name?.[0]?.toUpperCase() || '?'}
                        </AvatarFallback>
                      </Avatar>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-gray-900 truncate">{otherUser.name || 'Unknown'}</span>
                          {lastMsg && (
                            <span className="text-xs text-gray-400">
                              {formatMessageTime(lastMsg.sent_at)}
                            </span>
                          )}
                        </div>
                        {lastMsg && (
                          <p className="text-sm text-gray-500 truncate">
                            {lastMsg.sender_id === effectiveUser?.user_id && 'You: '}
                            {lastMsg.content}
                          </p>
                        )}
                      </div>
                      
                      {conv.unread_count > 0 && (
                        <span className="bg-red-500 text-white text-xs rounded-full px-2 py-0.5 min-w-[20px] text-center">
                          {conv.unread_count}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Chat Area */}
      <div className={`flex-1 flex flex-col ${!activeConversation ? 'hidden md:flex' : 'flex'}`}>
        {activeConversation ? (
          <>
            {/* Chat Header */}
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="md:hidden"
                  onClick={() => setActiveConversation(null)}
                >
                  <ArrowLeft className="w-5 h-5" />
                </Button>
                
                <Avatar 
                  className="w-10 h-10 cursor-pointer"
                  onClick={() => navigate(`/profile/${activeConversation.other_user?.user_id}`)}
                >
                  <AvatarImage src={activeConversation.other_user?.picture ? `${API}${activeConversation.other_user.picture}` : undefined} />
                  <AvatarFallback className="bg-gray-200">
                    {activeConversation.other_user?.name?.[0]?.toUpperCase() || '?'}
                  </AvatarFallback>
                </Avatar>
                
                <div>
                  <h2 className="font-medium">{activeConversation.other_user?.name || 'Unknown'}</h2>
                  {isOtherUserTyping() && (
                    <p className="text-xs text-green-600">typing...</p>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="icon" disabled>
                  <Phone className="w-5 h-5 text-gray-400" />
                </Button>
                <Button variant="ghost" size="icon" disabled>
                  <Video className="w-5 h-5 text-gray-400" />
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <MoreVertical className="w-5 h-5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => navigate(`/profile/${activeConversation.other_user?.user_id}`)}>
                      View Profile
                    </DropdownMenuItem>
                    <DropdownMenuItem className="text-red-600">
                      Delete Conversation
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            {/* Messages */}
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                {messages.map((message, index) => {
                  const isOwn = message.sender_id === effectiveUser?.user_id;
                  const showAvatar = !isOwn && (index === 0 || messages[index - 1]?.sender_id !== message.sender_id);
                  
                  return (
                    <div
                      key={message.message_id}
                      className={`flex items-end gap-2 ${isOwn ? 'justify-end' : 'justify-start'}`}
                    >
                      {!isOwn && (
                        <div className="w-8">
                          {showAvatar && (
                            <Avatar className="w-8 h-8">
                              <AvatarImage src={message.sender_picture ? `${API}${message.sender_picture}` : undefined} />
                              <AvatarFallback className="text-xs bg-gray-200">
                                {message.sender_name?.[0]?.toUpperCase() || '?'}
                              </AvatarFallback>
                            </Avatar>
                          )}
                        </div>
                      )}
                      
                      <div className={`max-w-[70%] ${isOwn ? 'order-1' : ''}`}>
                        <div
                          className={`px-4 py-2 rounded-2xl ${
                            isOwn 
                              ? 'bg-black text-white rounded-br-md' 
                              : 'bg-gray-100 text-gray-900 rounded-bl-md'
                          } ${message.failed ? 'opacity-60' : ''}`}
                        >
                          <MessageContent message={message} />
                        </div>
                        
                        <div className={`flex items-center gap-1 mt-1 text-xs text-gray-400 ${isOwn ? 'justify-end' : ''}`}>
                          <span>{formatMessageTime(message.created_at)}</span>
                          {isOwn && (
                            message.sending ? (
                              <Clock className="w-3 h-3" />
                            ) : message.failed ? (
                              <span className="text-red-500">Failed</span>
                            ) : (
                              <CheckCheck className="w-3 h-3" />
                            )
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
                
                {isOtherUserTyping() && (
                  <div className="flex items-center gap-2">
                    <div className="w-8" />
                    <div className="bg-gray-100 rounded-2xl px-4 py-2">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Message Input */}
            <form onSubmit={handleSendMessage} className="p-4 border-t border-gray-200">
              <div className="flex items-center gap-2">
                <Button type="button" variant="ghost" size="icon" disabled>
                  <Paperclip className="w-5 h-5 text-gray-400" />
                </Button>
                <Button type="button" variant="ghost" size="icon" disabled>
                  <Image className="w-5 h-5 text-gray-400" />
                </Button>
                
                <Input
                  ref={inputRef}
                  value={newMessage}
                  onChange={handleTyping}
                  placeholder="Type a message..."
                  className="flex-1 rounded-full"
                  data-testid="message-input"
                />
                
                <Button type="button" variant="ghost" size="icon" disabled>
                  <Smile className="w-5 h-5 text-gray-400" />
                </Button>
                
                <Button 
                  type="submit" 
                  size="icon"
                  disabled={!newMessage.trim() || sendingMessage}
                  className="rounded-full bg-black hover:bg-gray-800"
                  data-testid="send-message-btn"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </form>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                <Send className="w-8 h-8 text-gray-400" />
              </div>
              <h2 className="text-xl font-medium text-gray-900 mb-2">Your Messages</h2>
              <p className="text-gray-500">Select a conversation to start chatting</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatPage;
