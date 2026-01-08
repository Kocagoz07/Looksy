import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Spade, Heart, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function LandingPage() {
  const navigate = useNavigate();
  const [selectedGender, setSelectedGender] = useState(null);
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [magicLink, setMagicLink] = useState("");

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

  const handleSendMagicLink = async (e) => {
    e.preventDefault();
    
    if (!email || !selectedGender) {
      toast.error("Please enter your email and select a category");
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/auth/send-magic-link`,
        { email, category: selectedGender }
      );
      
      setEmailSent(true);
      setMagicLink(response.data.magic_link); // For development only
      toast.success("Magic link sent! Check your email.");
    } catch (err) {
      console.error("Error sending magic link:", err);
      toast.error("Failed to send magic link. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (emailSent) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto">
            <Mail className="w-10 h-10 text-green-600" />
          </div>
          
          <h1 className="font-playfair text-3xl font-bold text-black">Check Your Email</h1>
          
          <p className="font-manrope text-gray-600">
            We've sent a magic link to <strong>{email}</strong>. Click the link in your email to sign in.
          </p>
          
          {/* Development only: Show clickable magic link */}
          {magicLink && (
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="font-manrope text-xs text-gray-500 mb-2">Development: Click below to sign in</p>
              <a
                href={magicLink}
                className="font-manrope text-sm text-blue-600 hover:underline break-all"
              >
                Open Magic Link
              </a>
            </div>
          )}
          
          <Button
            onClick={() => {
              setEmailSent(false);
              setEmail("");
            }}
            variant="outline"
            className="font-manrope"
          >
            Use different email
          </Button>
        </div>
      </div>
    );
  }

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

      {/* Floating Login Form */}
      {selectedGender && (
        <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-50 animate-fade-in">
          <div className="bg-white p-8 rounded-2xl shadow-2xl max-w-md w-full">
            <h1 className="font-playfair text-4xl font-bold text-black text-center mb-2">
              Looksy
            </h1>
            <p className="font-manrope text-sm text-gray-600 text-center mb-6">
              Enter your email to get started
            </p>
            
            <form onSubmit={handleSendMagicLink} className="space-y-4">
              <Input
                data-testid="email-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="font-manrope text-center"
                required
              />
              
              <Button
                data-testid="send-magic-link-btn"
                type="submit"
                disabled={loading || !email}
                className="w-full bg-black text-white hover:bg-gray-800 py-6 text-lg font-manrope font-semibold rounded-full"
              >
                {loading ? "Sending..." : "Send Magic Link"}
              </Button>
            </form>
            
            <p className="font-manrope text-xs text-gray-500 text-center mt-4">
              We'll send you a magic link to sign in
            </p>
          </div>
        </div>
      )}
    </div>
  );
}