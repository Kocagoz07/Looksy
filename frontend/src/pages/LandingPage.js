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
    <div className="min-h-screen flex">
      {/* Left Side - Men (Spade) - Black Background */}
      <div 
        className={`w-1/2 min-h-screen flex flex-col items-center justify-center p-16 transition-all duration-500 cursor-pointer relative ${
          selectedGender === 'men' ? 'bg-black' : 'bg-black opacity-70'
        }`}
        onClick={() => setSelectedGender('men')}
        data-testid="gender-men-section"
      >
        <div className="text-center space-y-10">
          {/* Spade Icon - Outline */}
          <div className={`transition-all duration-300 ${selectedGender === 'men' ? 'scale-100 opacity-100' : 'scale-95 opacity-60'}`}>
            <Spade className="w-32 h-32 mx-auto text-white" strokeWidth={1.5} />
          </div>
          
          {/* Looksy Text */}
          <div>
            <h1 className="font-italiana text-6xl text-white tracking-wide">
              Looksy
            </h1>
          </div>
          
          {/* Tagline */}
          <div>
            <p className="font-manrope text-white text-xs tracking-[0.3em] uppercase font-light">
              Fashion Redefined
            </p>
          </div>

          {selectedGender === 'men' && (
            <div className="absolute top-8 right-8 animate-fade-in">
              <div className="w-2 h-2 rounded-full bg-white"></div>
            </div>
          )}
        </div>
      </div>

      {/* Right Side - Women (Heart) - Burgundy Background */}
      <div 
        className={`w-1/2 min-h-screen flex flex-col items-center justify-center p-16 transition-all duration-500 cursor-pointer relative ${
          selectedGender === 'women' ? 'bg-[#800020]' : 'bg-[#800020] opacity-70'
        }`}
        onClick={() => setSelectedGender('women')}
        data-testid="gender-women-section"
      >
        <div className="text-center space-y-10">
          {/* Heart Icon - Outline */}
          <div className={`transition-all duration-300 ${selectedGender === 'women' ? 'scale-100 opacity-100' : 'scale-95 opacity-60'}`}>
            <Heart className="w-32 h-32 mx-auto text-white" strokeWidth={1.5} />
          </div>
          
          {/* Looksy Text */}
          <div>
            <h1 className="font-italiana text-6xl text-white tracking-wide">
              Looksy
            </h1>
          </div>
          
          {/* Tagline */}
          <div>
            <p className="font-manrope text-white text-xs tracking-[0.3em] uppercase font-light">
              Fashion Redefined
            </p>
          </div>

          {selectedGender === 'women' && (
            <div className="absolute top-8 right-8 animate-fade-in">
              <div className="w-2 h-2 rounded-full bg-white"></div>
            </div>
          )}
        </div>
      </div>

      {/* Floating Login Card */}
      {selectedGender && (
        <div className="fixed inset-0 flex items-center justify-center pointer-events-none z-50">
          <div className="pointer-events-auto bg-white rounded-3xl shadow-2xl p-12 max-w-lg w-full mx-4 animate-fade-in">
            {/* Logo */}
            <div className="text-center mb-10 space-y-3">
              <h1 className="font-italiana text-6xl tracking-wide text-black">
                Looksy
              </h1>
              <p className="font-manrope text-xs tracking-[0.3em] uppercase text-gray-500 font-light">
                Fashion Redefined
              </p>
              <div className="w-20 h-px bg-gray-300 mx-auto mt-6"></div>
            </div>

            <form onSubmit={handleSendMagicLink} className="space-y-6">
              {/* Email Input */}
              <div className="space-y-2">
                <div className="relative">
                  <Mail className="absolute left-5 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <Input
                    data-testid="email-input"
                    type="email"
                    value={email}
                    onChange={handleEmailChange}
                    placeholder="Email address"
                    className="pl-14 h-16 rounded-full border-gray-200 font-manrope text-base focus:border-black focus:ring-black"
                    required
                  />
                </div>
                {emailError && (
                  <p className="text-xs text-red-500 font-manrope ml-5">{emailError}</p>
                )}
              </div>

              {/* Sign In Button */}
              <Button
                data-testid="send-magic-link-btn"
                type="submit"
                disabled={loading || !isFormValid}
                className="w-full h-16 bg-black text-white hover:bg-gray-900 rounded-full font-manrope font-medium text-base transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
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
              <p className="text-center font-manrope text-xs text-gray-500 mt-6">
                We'll send you a secure sign-in link
              </p>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
