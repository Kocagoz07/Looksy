import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Spade, Heart } from "lucide-react";
import { Button } from "@/components/ui/button";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function LandingPage() {
  const navigate = useNavigate();
  const [selectedGender, setSelectedGender] = useState(null);

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

  const handleGenderSelect = (gender) => {
    setSelectedGender(gender);
  };

  const handleGoogleLogin = () => {
    if (!selectedGender) return;
    
    // Store selected gender in sessionStorage to use after auth
    sessionStorage.setItem('selected_gender', selectedGender);
    
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen flex">
      {/* Men Section - Black */}
      <div 
        className={`w-1/2 min-h-screen flex flex-col items-center justify-center p-8 transition-all duration-300 cursor-pointer ${
          selectedGender === 'men' ? 'bg-black' : 'bg-black opacity-50 hover:opacity-70'
        }`}
        onClick={() => handleGenderSelect('men')}
        data-testid="gender-men-section"
      >
        <div className="text-center">
          {/* Logo */}
          <div className="w-32 h-32 flex items-center justify-center bg-white rounded-full mb-6 mx-auto">
            <Spade className="w-16 h-16 text-black" />
          </div>
          
          <h2 className="font-playfair text-2xl font-bold text-white mb-2">Fashion Redefined</h2>
          
          {selectedGender === 'men' && (
            <div className="mt-8 animate-fade-in">
              <div className="w-3 h-3 rounded-full bg-white mx-auto mb-2"></div>
              <p className="font-manrope text-sm text-white opacity-70">Selected</p>
            </div>
          )}
        </div>
      </div>

      {/* Women Section - Dark Red */}
      <div 
        className={`w-1/2 min-h-screen flex flex-col items-center justify-center p-8 transition-all duration-300 cursor-pointer ${
          selectedGender === 'women' ? 'bg-[#4A0404]' : 'bg-[#4A0404] opacity-50 hover:opacity-70'
        }`}
        onClick={() => handleGenderSelect('women')}
        data-testid="gender-women-section"
      >
        <div className="text-center">
          {/* Logo */}
          <div className="w-32 h-32 flex items-center justify-center bg-white rounded-full mb-6 mx-auto">
            <Heart className="w-16 h-16 text-[#FF0000] fill-current" />
          </div>
          
          <h2 className="font-playfair text-2xl font-bold text-white mb-2">Fashion Redefined</h2>
          
          {selectedGender === 'women' && (
            <div className="mt-8 animate-fade-in">
              <div className="w-3 h-3 rounded-full bg-white mx-auto mb-2"></div>
              <p className="font-manrope text-sm text-white opacity-70">Selected</p>
            </div>
          )}
        </div>
      </div>

      {/* Floating Continue Button */}
      {selectedGender && (
        <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-50 animate-fade-in">
          <div className="text-center">
            <h1 className="font-playfair text-5xl font-bold text-white mb-6 drop-shadow-lg">
              Looksy
            </h1>
            <Button
              data-testid="google-login-btn"
              onClick={handleGoogleLogin}
              className="bg-white text-black hover:bg-gray-100 px-12 py-6 text-lg font-manrope font-semibold rounded-full shadow-2xl"
            >
              Continue with Google
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}