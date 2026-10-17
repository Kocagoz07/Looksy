import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const ChatContext = createContext(null);

export const useChatContext = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within ChatProvider');
  }
  return context;
};

export const ChatProvider = ({ children, user }) => {
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [typingUsers, setTypingUsers] = useState({});
  const [onlineUsers, setOnlineUsers] = useState({});
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (!user || wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = API.replace('https://', 'wss://').replace('http://', 'ws://') + '/ws/chat';
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      // Send auth message
      const sessionToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('session_token='))
        ?.split('=')[1];
      
      if (sessionToken) {
        ws.send(JSON.stringify({ type: 'auth', token: sessionToken }));
      }
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      // Reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  }, [user]);

  const handleWebSocketMessage = useCallback((data) => {
    switch (data.type) {
      case 'connected':
        setIsConnected(true);
        break;
      
      case 'message:new':
        // Add new message if in active conversation
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
                unread_count: (conv.unread_count || 0) + 1,
                updated_at: data.message.created_at
              };
            }
            return conv;
          });
          return updated.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        });
        setUnreadCount(prev => prev + 1);
        break;
      
      case 'message:sent':
        // Message confirmed
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
      
      case 'presence:update':
        setOnlineUsers(data.statuses);
        break;
      
      case 'message:read_receipt':
        // Update read status in messages
        break;
      
      case 'pong':
        // Heartbeat response
        break;
      
      default:
        console.log('Unknown message type:', data.type);
    }
  }, [activeConversation]);

  // Fetch conversations
  const fetchConversations = useCallback(async () => {
    if (!user) return;
    
    try {
      const response = await axios.get(`${API}/api/chat/conversations`, {
        withCredentials: true
      });
      setConversations(prev => {
  prev = Array.isArray(prev) ? prev : [];

  if (
    !prev.find(
      c => c.conversation_id === conversation.conversation_id
    )
  ) {
    return [conversation, ...prev];
  }

  return prev;
});
    } catch (error) {
      console.error('Error fetching conversations:', error);
    }
  }, [user]);

  // Fetch unread count
  const fetchUnreadCount = useCallback(async () => {
    if (!user) return;
    
    try {
      const response = await axios.get(`${API}/api/chat/unread-count`, {
        withCredentials: true
      });
      setUnreadCount(response.data.unread_count || 0);
    } catch (error) {
      console.error('Error fetching unread count:', error);
    }
  }, [user]);

  // Start conversation with user
  const startConversation = async (targetUserId) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/api/chat/conversations/direct`, {
        user_id: targetUserId
      }, { withCredentials: true });
      
      const conversation = response.data;
      
      // Add to conversations if not exists
      setConversations(prev => {
        if (!prev.find(c => c.conversation_id === conversation.conversation_id)) {
          return [conversation, ...prev];
        }
        return prev;
      });
      
      setActiveConversation(conversation);
      await loadMessages(conversation.conversation_id);
      
      return conversation;
    } catch (error) {
      console.error('Error starting conversation:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Load messages for a conversation
  const loadMessages = async (conversationId, before = null) => {
    try {
      setLoading(true);
      const params = { limit: 30 };
      if (before) params.before = before;
      
      const response = await axios.get(
        `${API}/api/chat/conversations/${conversationId}/messages`,
        { params, withCredentials: true }
      );
      
      if (before) {
        setMessages(prev => [...response.data.messages, ...prev]);
      } else {
        setMessages(response.data.messages || []);
      }
      
      return response.data;
    } catch (error) {
      console.error('Error loading messages:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Send message
  const sendMessage = async (conversationId, content) => {
    // Optimistically add message
    const tempMessage = {
      message_id: `temp_${Date.now()}`,
      conversation_id: conversationId,
      sender_id: user?.user_id,
      sender_name: user?.name,
      sender_picture: user?.picture,
      content,
      type: 'text',
      created_at: new Date().toISOString(),
      sending: true
    };
    
    setMessages(prev => [...prev, tempMessage]);
    
    // Send via WebSocket if connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'message:send',
        conversation_id: conversationId,
        content
      }));
    } else {
      // Fallback to REST API
      try {
        const response = await axios.post(
          `${API}/api/chat/conversations/${conversationId}/messages`,
          { content },
          { withCredentials: true }
        );
        
        // Replace temp message with real one
        setMessages(prev => prev.map(m => 
          m.message_id === tempMessage.message_id ? response.data : m
        ));
      } catch (error) {
        // Mark message as failed
        setMessages(prev => prev.map(m =>
          m.message_id === tempMessage.message_id ? { ...m, sending: false, failed: true } : m
        ));
        throw error;
      }
    }
  };

  // Send typing indicator
  const sendTypingIndicator = (conversationId, isTyping) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: isTyping ? 'typing:start' : 'typing:stop',
        conversation_id: conversationId
      }));
    }
  };

  // Mark messages as read
  const markAsRead = async (conversationId) => {
    try {
      await axios.post(
        `${API}/api/chat/conversations/${conversationId}/read`,
        {},
        { withCredentials: true }
      );
      
      // Update local state
      setConversations(prev => prev.map(conv => 
        conv.conversation_id === conversationId 
          ? { ...conv, unread_count: 0 }
          : conv
      ));
      
      // Recalculate total unread
      fetchUnreadCount();
    } catch (error) {
      console.error('Error marking as read:', error);
    }
  };

  // Initialize
  useEffect(() => {
    if (user) {
      fetchConversations();
      fetchUnreadCount();
      connectWebSocket();
    }
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [user, fetchConversations, fetchUnreadCount, connectWebSocket]);

  // Heartbeat
  useEffect(() => {
    if (!isConnected) return;
    
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
    
    return () => clearInterval(interval);
  }, [isConnected]);

  const value = {
    conversations,
    activeConversation,
    setActiveConversation,
    messages,
    unreadCount,
    typingUsers,
    onlineUsers,
    isConnected,
    loading,
    startConversation,
    loadMessages,
    sendMessage,
    sendTypingIndicator,
    markAsRead,
    fetchConversations
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
};

export default ChatContext;
