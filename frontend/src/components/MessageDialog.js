import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, X, Loader2, CheckCheck, Clock } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { MessageContent } from './SharedPostMessage';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';

const API = process.env.REACT_APP_BACKEND_URL;

const MessageDialog = ({ isOpen, onClose, targetUser, currentUser }) => {
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [ws, setWs] = useState(null);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && targetUser && currentUser) {
      initializeConversation();
      connectWebSocket();
    }
    
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [isOpen, targetUser, currentUser]);

  const connectWebSocket = () => {
    const wsUrl = API.replace('https://', 'wss://').replace('http://', 'ws://') + '/ws/chat';
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
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
      if (data.type === 'message:new' && conversation?.conversation_id === data.message.conversation_id) {
        setMessages(prev => [...prev, data.message]);
      } else if (data.type === 'message:reaction') {
        setMessages(prev => prev.map(m => m.message_id === data.message_id ? { ...m, reactions: data.reactions } : m));
      } else if (data.type === 'message:sent') {
        setMessages(prev => prev.map(m => 
          m.temp_id ? { ...data.message, temp_id: undefined } : m
        ));
      }
    };

    setWs(socket);
  };

  const initializeConversation = async () => {
    setLoading(true);
    try {
      const convResponse = await axios.post(`${API}/api/chat/conversations/direct`, {
        user_id: targetUser.user_id
      }, { withCredentials: true });
      
      setConversation(convResponse.data);
      
      const msgResponse = await axios.get(
        `${API}/api/chat/conversations/${convResponse.data.conversation_id}/messages`,
        { withCredentials: true }
      );
      setMessages(msgResponse.data.messages || []);
      
      await axios.post(
        `${API}/api/chat/conversations/${convResponse.data.conversation_id}/read`,
        {},
        { withCredentials: true }
      );
      
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (error) {
      console.error('Error initializing conversation:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !conversation || sending) return;

    const content = newMessage.trim();
    setNewMessage('');
    setSending(true);

    const tempMessage = {
      message_id: `temp_${Date.now()}`,
      temp_id: true,
      conversation_id: conversation.conversation_id,
      sender_id: currentUser?.user_id,
      sender_name: currentUser?.name,
      content,
      type: 'text',
      created_at: new Date().toISOString(),
      sending: true
    };
    setMessages(prev => [...prev, tempMessage]);

    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'message:send',
        conversation_id: conversation.conversation_id,
        content
      }));
      setSending(false);
    } else {
      try {
        const response = await axios.post(
          `${API}/api/chat/conversations/${conversation.conversation_id}/messages`,
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
        setSending(false);
      }
    }
  };

  const formatTime = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const handleClose = () => {
    if (ws) {
      ws.close();
    }
    setWs(null);
    setConversation(null);
    setMessages([]);
    setNewMessage('');
    onClose();
  };

  if (!targetUser) return null;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md p-0 gap-0 overflow-hidden">
        <DialogHeader className="p-4 border-b">
          <div className="flex items-center gap-3">
            <Avatar className="w-10 h-10">
              <AvatarImage src={targetUser.picture ? `${API}${targetUser.picture}` : undefined} />
              <AvatarFallback className="bg-gray-200">
                {targetUser.name?.[0]?.toUpperCase() || '?'}
              </AvatarFallback>
            </Avatar>
            <div>
              <DialogTitle className="text-base font-semibold">{targetUser.name}</DialogTitle>
              <DialogDescription className="text-xs text-gray-500">
                Direct Message
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="h-[350px] overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Avatar className="w-16 h-16 mb-3">
                <AvatarImage src={targetUser.picture ? `${API}${targetUser.picture}` : undefined} />
                <AvatarFallback className="bg-gray-200 text-xl">
                  {targetUser.name?.[0]?.toUpperCase() || '?'}
                </AvatarFallback>
              </Avatar>
              <p className="font-medium text-gray-900">{targetUser.name}</p>
              <p className="text-sm text-gray-500 mt-1">Send a message to start the conversation</p>
            </div>
          ) : (
            <div className="space-y-3">
              {messages.map((message) => {
                const isOwn = message.sender_id === currentUser?.user_id;
                
                return (
                  <div
                    key={message.message_id}
                    className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[75%]`}>
                      <div
                        className={`px-3 py-2 rounded-2xl ${
                          isOwn 
                            ? 'bg-black text-white rounded-br-sm' 
                            : 'bg-gray-100 text-gray-900 rounded-bl-sm'
                        } ${message.failed ? 'opacity-60' : ''}`}
                      >
                        <MessageContent message={message} currentUserId={currentUser?.user_id} />
                      </div>
                      
                      <div className={`flex items-center gap-1 mt-0.5 text-[10px] text-gray-400 ${isOwn ? 'justify-end' : ''}`}>
                        <span>{formatTime(message.created_at)}</span>
                        {isOwn && (
                          message.sending ? (
                            <Clock className="w-2.5 h-2.5" />
                          ) : message.failed ? (
                            <span className="text-red-500">!</span>
                          ) : (
                            <CheckCheck className="w-2.5 h-2.5" />
                          )
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <form onSubmit={handleSendMessage} className="p-3 border-t bg-gray-50">
          <div className="flex items-center gap-2">
            <Input
              ref={inputRef}
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Type a message..."
              className="flex-1 rounded-full bg-white"
              data-testid="profile-message-input"
            />
            <Button 
              type="submit" 
              size="icon"
              disabled={!newMessage.trim() || sending}
              className="rounded-full bg-black hover:bg-gray-800 h-9 w-9"
              data-testid="profile-send-message-btn"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default MessageDialog;
