import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import LandingPage from "@/pages/LandingPage";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import UploadPost from "@/pages/UploadPost";
import PostDetail from "@/pages/PostDetail";
import UserProfile from "@/pages/UserProfile";
import ProtectedRoute from "@/components/ProtectedRoute";
import { Toaster } from "@/components/ui/sonner";

function AppContent() {
  const location = useLocation();
  
  // Check for session_id in URL hash
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/men" element={<ProtectedRoute><Dashboard category="men" /></ProtectedRoute>} />
      <Route path="/women" element={<ProtectedRoute><Dashboard category="women" /></ProtectedRoute>} />
      <Route path="/stars" element={<ProtectedRoute><Dashboard category="stars" /></ProtectedRoute>} />
      <Route path="/upload" element={<ProtectedRoute><UploadPost /></ProtectedRoute>} />
      <Route path="/post/:postId" element={<ProtectedRoute><PostDetail /></ProtectedRoute>} />
      <Route path="/profile/:userId" element={<ProtectedRoute><UserProfile /></ProtectedRoute>} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AppContent />
        <Toaster position="top-center" />
      </BrowserRouter>
    </div>
  );
}

export default App;