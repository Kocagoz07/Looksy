import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    
    const processAuth = async () => {
      try {
        const hash = window.location.hash.substring(1);
        const params = new URLSearchParams(hash);
        const sessionId = params.get('session_id');

        if (!sessionId) {
          navigate('/', { replace: true });
          return;
        }

        const response = await axios.post(
          `${BACKEND_URL}/api/auth/callback`,
          { session_id: sessionId },
          { withCredentials: true }
        );

        if (isMounted && response.data) {
          sessionStorage.setItem('just_authenticated', 'true');
          navigate('/dashboard', { replace: true, state: { user: response.data } });
        }
      } catch (err) {
        console.error('Auth error:', err);
        if (isMounted) {
          navigate('/', { replace: true });
        }
      }
    };

    processAuth();
    
    return () => {
      isMounted = false;
    };
  }, [navigate]);

  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black mx-auto mb-4"></div>
        <p className="font-manrope text-gray-600">Completing authentication...</p>
      </div>
    </div>
  );
}