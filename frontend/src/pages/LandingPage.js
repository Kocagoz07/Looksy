import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Mail, ArrowRight, Spade, Heart } from "lucide-react";
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
  const [emailError, setEmailError] = useState("");

  useEffect(() => {
    const checkAuth = async () => {
      try {
        await axios.get(`${BACKEND_URL}/api/auth/me`, { withCredentials: true });
        navigate("/dashboard", { replace: true });
      } catch (err) {
        // Not authenticated
      }
    };
    checkAuth();
  }, [navigate]);

  const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    if (value && !validateEmail(value)) {
      setEmailError("Please enter a valid email");
    } else {
      setEmailError("");
    }
  };

  const handleSendMagicLink = async (e) => {
    e.preventDefault();
    
    if (!email || !selectedGender) {
      toast.error("Please enter your email and select a category");
      return;
    }

    if (!validateEmail(email)) {
      setEmailError("Please enter a valid email");
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/auth/send-magic-link`,
        { email, category: selectedGender }
      );
      
      setEmailSent(true);
      setMagicLink(response.data.magic_link);
      toast.success("Magic link sent! Check your email.");
    } catch (err) {
      console.error("Error sending magic link:", err);
      toast.error("Failed to send magic link. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const isFormValid = email && validateEmail(email) && !emailError;

  if (emailSent) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="w-16 h-16 bg-black rounded-full flex items-center justify-center mx-auto">
            <Mail className="w-8 h-8 text-white" />
          </div>
          
          <h1 className="font-playfair text-3xl font-bold text-black">Check Your Email</h1>
          
          <p className="font-manrope text-gray-600">
            We've sent a secure link to <strong className="text-black">{email}</strong>
          </p>
          
          {magicLink && (
            <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
              <p className="font-manrope text-xs text-gray-500 mb-2">Development Mode</p>
              <a
                href={magicLink}
                className="font-manrope text-sm text-black hover:underline break-all font-medium"
              >
                Click here to sign in →
              </a>
            </div>
          )}
          
          <Button
            onClick={() => {
              setEmailSent(false);
              setEmail("");
            }}
            variant="ghost"
            className="font-manrope text-gray-600"
          >
            Use different email
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex">
      {/* Left Side - Men (Spade) */}
      <div 
        className={`w-1/2 min-h-screen flex flex-col items-center justify-center p-12 transition-all duration-500 cursor-pointer relative overflow-hidden ${
          selectedGender === 'men' ? 'bg-black' : 'bg-gray-900'
        }`}
        onClick={() => setSelectedGender('men')}
        data-testid="gender-men-section"
      >
        <div className="relative z-10 text-center space-y-8">
          {/* Spade Icon */}
          <div className={`transition-all duration-300 ${selectedGender === 'men' ? 'scale-100 opacity-100' : 'scale-90 opacity-60'}`}>
            <div className="w-32 h-32 flex items-center justify-center mx-auto">
              <Spade className="w-24 h-24 text-white fill-white" />
            </div>
          </div>
          
          {selectedGender === 'men' && (
            <div className="absolute top-6 right-6 animate-fade-in">
              <div className="w-2 h-2 rounded-full bg-white"></div>
            </div>
          )}
        </div>
      </div>

      {/* Right Side - Women (Ace of Hearts) */}
      <div 
        className={`w-1/2 min-h-screen flex flex-col items-center justify-center p-12 transition-all duration-500 cursor-pointer relative overflow-hidden ${
          selectedGender === 'women' ? 'bg-[#2C0A0A]' : 'bg-[#3D1010]'
        }`}
        onClick={() => setSelectedGender('women')}
        data-testid="gender-women-section"
      >
        <div className="relative z-10 text-center space-y-8">
          {/* Heart Icon */}
          <div className={`transition-all duration-300 ${selectedGender === 'women' ? 'scale-100 opacity-100' : 'scale-90 opacity-60'}`}>
            <div className="w-32 h-32 flex items-center justify-center mx-auto">
              <Heart className="w-24 h-24 text-white fill-white" />
            </div>
          </div>

          {selectedGender === 'women' && (
            <div className="absolute top-6 right-6 animate-fade-in">
              <div className="w-2 h-2 rounded-full bg-white"></div>
            </div>
          )}
        </div>
      </div>

      {/* Floating Login Card */}
      {selectedGender && (
        <div className="fixed inset-0 flex items-center justify-center pointer-events-none z-50">
          <div className="pointer-events-auto bg-white rounded-3xl shadow-2xl p-10 max-w-md w-full mx-4 animate-fade-in">
            {/* Logo */}
            <div className="text-center mb-8 space-y-2">
              <h1 className="font-playfair text-5xl font-bold tracking-wide text-black">
                Looksy
              </h1>
              <p className="font-manrope text-sm tracking-widest uppercase text-gray-600">
                Fashion Redefined
              </p>
              <div className="w-16 h-0.5 bg-black mx-auto mt-4"></div>
            </div>

            <form onSubmit={handleSendMagicLink} className="space-y-5">
              {/* Email Input */}
              <div className="space-y-2">
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <Input
                    data-testid="email-input"
                    type="email"
                    value={email}
                    onChange={handleEmailChange}
                    placeholder="Email address"
                    className="pl-12 h-14 rounded-full border-gray-200 font-manrope text-base focus:border-black focus:ring-black"
                    required
                  />
                </div>
                {emailError && (
                  <p className="text-xs text-red-500 font-manrope ml-4">{emailError}</p>
                )}
              </div>

              {/* Sign In Button */}
              <Button
                data-testid="send-magic-link-btn"
                type="submit"
                disabled={loading || !isFormValid}
                className="w-full h-14 bg-black text-white hover:bg-gray-900 rounded-full font-manrope font-medium text-base transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
              >
                {loading ? (
                  <span className="flex items-center justify-center">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Sending...
                  </span>
                ) : (
                  <span className="flex items-center justify-center">
                    Send Magic Link
                    <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                  </span>
                )}
              </Button>

              {/* Info Text */}
              <p className="text-center font-manrope text-xs text-gray-500 mt-4">
                We'll send you a secure sign-in link
              </p>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
