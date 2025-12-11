import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Spade, Heart, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function LandingPage() {
  const navigate = useNavigate();

  useEffect(() => {
    // Check if already authenticated
    const checkAuth = async () => {
      try {
        await axios.get(`${BACKEND_URL}/api/auth/me`, { withCredentials: true });
        navigate("/dashboard", { replace: true });
      } catch (err) {
        // Not authenticated, stay on landing page
      }
    };
    checkAuth();
  }, [navigate]);

  const handleGoogleLogin = () => {
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-6">
      <div className="max-w-4xl w-full text-center space-y-8">
        {/* Logo */}
        <h1 className="font-playfair text-6xl sm:text-7xl lg:text-8xl font-bold text-black tracking-tight">
          Looksy
        </h1>
        
        <p className="font-manrope text-lg sm:text-xl text-gray-700 max-w-2xl mx-auto">
          The fashion social network where your style earns. Share your looks, connect with brands, and monetize your influence.
        </p>

        {/* Category Icons */}
        <div className="flex items-center justify-center gap-8 py-8">
          <div className="text-center">
            <div className="w-20 h-20 flex items-center justify-center bg-black text-white rounded-full mb-2">
              <Spade className="w-10 h-10" />
            </div>
            <p className="font-playfair text-sm font-semibold">Men</p>
          </div>
          
          <div className="text-center">
            <div className="w-20 h-20 flex items-center justify-center bg-[#4A0404] text-[#FF0000] rounded-full mb-2">
              <Heart className="w-10 h-10 fill-current" />
            </div>
            <p className="font-playfair text-sm font-semibold">Women</p>
          </div>
          
          <div className="text-center">
            <div className="w-20 h-20 flex items-center justify-center bg-white border-2 border-[#FFD700] text-[#FFD700] rounded-full mb-2">
              <Star className="w-10 h-10 fill-current" />
            </div>
            <p className="font-playfair text-sm font-semibold">Stars</p>
          </div>
        </div>

        {/* CTA */}
        <Button
          data-testid="google-login-btn"
          onClick={handleGoogleLogin}
          className="bg-black text-white hover:bg-gray-800 px-12 py-6 text-lg font-manrope font-semibold rounded-full"
        >
          Continue with Google
        </Button>

        <p className="text-sm text-gray-500 font-manrope">
          Join fashion enthusiasts earning from their style
        </p>
      </div>
    </div>
  );
}