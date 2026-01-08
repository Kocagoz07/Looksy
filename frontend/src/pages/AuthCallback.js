import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function AuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [verifying, setVerifying] = useState(true);

  useEffect(() => {
    let isMounted = true;
    
    const verifyMagicLink = async () => {
      try {
        const token = searchParams.get('token');

        if (!token) {
          toast.error("Invalid magic link");
          navigate('/', { replace: true });
          return;
        }

        const response = await axios.get(
          `${BACKEND_URL}/api/auth/verify-magic-link?token=${token}`,
          { withCredentials: true }
        );

        if (isMounted && response.data) {
          sessionStorage.setItem('just_authenticated', 'true');
          toast.success(`Welcome, ${response.data.name}!`);
          navigate('/dashboard', { replace: true, state: { user: response.data } });
        }
      } catch (err) {
        console.error('Auth error:', err);
        const errorMsg = err.response?.data?.detail || "Invalid or expired magic link";
        toast.error(errorMsg);
        if (isMounted) {
          setTimeout(() => {
            navigate('/', { replace: true });
          }, 2000);
        }
      } finally {
        if (isMounted) {
          setVerifying(false);
        }
      }
    };

    verifyMagicLink();
    
    return () => {
      isMounted = false;
    };
  }, [navigate, searchParams]);

  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        {verifying ? (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black mx-auto mb-4"></div>
            <p className="font-manrope text-gray-600">Verifying your magic link...</p>
          </>
        ) : (
          <p className="font-manrope text-gray-600">Redirecting...</p>
        )}
      </div>
    </div>
  );
}