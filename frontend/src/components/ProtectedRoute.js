import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { sendFingerprint } from "../utils/fingerprint";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ProtectedRoute({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [isAuthenticated, setIsAuthenticated] = useState(location.state?.user ? true : null);

  useEffect(() => {
    let isMounted = true;
    
    const checkAuth = async () => {
      // Skip delay if just authenticated
      const justAuth = sessionStorage.getItem('just_authenticated');
      if (!justAuth) {
        await new Promise(r => setTimeout(r, 150));
      } else {
        sessionStorage.removeItem('just_authenticated');
      }

      try {
        await axios.get(`${BACKEND_URL}/api/auth/me`, { withCredentials: true });
        if (isMounted) {
          setIsAuthenticated(true);
          
          // Send device fingerprint for fraud detection (non-blocking)
          sendFingerprint().catch(err => console.warn('Fingerprint failed:', err));
        }
      } catch (err) {
        if (isMounted) {
          setIsAuthenticated(false);
          navigate('/', { replace: true });
        }
      }
    };

    if (isAuthenticated !== true) {
      checkAuth();
    }
    
    return () => {
      isMounted = false;
    };
  }, [navigate, isAuthenticated]);

  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black mx-auto mb-4"></div>
          <p className="font-manrope text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated === false) {
    return null;
  }

  return children;
}