import { useState } from "react";
import { User, Mail, Lock, Eye, EyeOff, Phone, ShieldCheck, ArrowRight, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function RegisterModal({ open, onOpenChange, selectedGender, onSuccess }) {
  // Step: 1 = Phone input, 2 = OTP verification, 3 = Account details
  const [step, setStep] = useState(1);
  
  // Phone verification
  const [phoneNumber, setPhoneNumber] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [phoneVerified, setPhoneVerified] = useState(false);
  const [testOtp, setTestOtp] = useState(null);
  
  // Account details
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const validatePhone = (phone) => {
    // Basic E.164 format validation
    return /^\+[1-9]\d{6,14}$/.test(phone);
  };

  const getPasswordStrength = (pwd) => {
    if (pwd.length < 6) return { strength: "weak", color: "bg-red-500", width: "33%" };
    if (pwd.length < 10) return { strength: "medium", color: "bg-yellow-500", width: "66%" };
    return { strength: "strong", color: "bg-green-500", width: "100%" };
  };

  const passwordStrength = getPasswordStrength(password);

  // Send OTP
  const handleSendOtp = async () => {
    if (!validatePhone(phoneNumber)) {
      toast.error("Please enter a valid phone number in international format (e.g., +1234567890)");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/auth/send-otp`,
        { phone_number: phoneNumber },
        { withCredentials: true }
      );
      
      setOtpSent(true);
      toast.success("OTP sent to your phone!");
      
      // In test mode, show the OTP
      if (response.data.test_mode && response.data.otp_code) {
        setTestOtp(response.data.otp_code);
        toast.info(`Test Mode: Your OTP is ${response.data.otp_code}`);
      }
      
      // Start countdown
      setCountdown(60);
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      
      setStep(2);
    } catch (err) {
      console.error("Send OTP error:", err);
      toast.error(err.response?.data?.detail || "Failed to send OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Verify OTP
  const handleVerifyOtp = async () => {
    if (otpCode.length !== 6) {
      toast.error("Please enter the 6-digit OTP");
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/auth/verify-otp`,
        { phone_number: phoneNumber, otp_code: otpCode },
        { withCredentials: true }
      );
      
      setPhoneVerified(true);
      toast.success("Phone number verified!");
      setStep(3);
    } catch (err) {
      console.error("Verify OTP error:", err);
      toast.error(err.response?.data?.detail || "Invalid OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Register
  const handleRegister = async (e) => {
    e.preventDefault();

    if (!name || !email || !password || !confirmPassword) {
      toast.error("Please fill all fields");
      return;
    }

    if (!validateEmail(email)) {
      toast.error("Please enter a valid email");
      return;
    }

    if (password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    if (!phoneVerified) {
      toast.error("Please verify your phone number first");
      return;
    }

    setLoading(true);

    try {
      await axios.post(
        `${BACKEND_URL}/api/auth/register-with-phone`,
        {
          name,
          email,
          password,
          category: selectedGender,
          phone_number: phoneNumber,
          otp_code: otpCode
        },
        { withCredentials: true }
      );

      toast.success("Account created successfully!");
      onOpenChange(false);
      onSuccess();
    } catch (err) {
      console.error("Registration error:", err);
      toast.error(err.response?.data?.detail || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setStep(1);
    setPhoneNumber("");
    setOtpCode("");
    setOtpSent(false);
    setPhoneVerified(false);
    setTestOtp(null);
    setName("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
    setCountdown(0);
  };

  return (
    <Dialog open={open} onOpenChange={(open) => {
      if (!open) resetForm();
      onOpenChange(open);
    }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-italiana text-2xl">Create Account</DialogTitle>
          <DialogDescription className="font-manrope">
            {step === 1 && "Verify your phone number to get started"}
            {step === 2 && "Enter the 6-digit code sent to your phone"}
            {step === 3 && "Complete your profile"}
          </DialogDescription>
        </DialogHeader>

        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-2 my-4">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`w-8 h-8 rounded-full flex items-center justify-center font-manrope text-sm font-semibold transition-all ${
                step >= s 
                  ? 'bg-black text-white' 
                  : 'bg-gray-200 text-gray-500'
              }`}
            >
              {s < step ? '✓' : s}
            </div>
          ))}
        </div>

        {/* Step 1: Phone Input */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="relative">
              <Phone className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <Input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="+1234567890"
                className="pl-12 h-12 rounded-full font-manrope"
                data-testid="phone-input"
              />
            </div>
            <p className="text-xs text-gray-500 font-manrope px-4">
              Enter your phone number in international format (e.g., +1 for US, +44 for UK)
            </p>
            
            <Button
              onClick={handleSendOtp}
              disabled={loading || !phoneNumber}
              className="w-full h-12 bg-black text-white hover:bg-gray-900 rounded-full font-manrope font-semibold"
              data-testid="send-otp-btn"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Sending...
                </span>
              ) : (
                <>
                  Send Verification Code
                  <ArrowRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          </div>
        )}

        {/* Step 2: OTP Verification */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="text-center mb-4">
              <ShieldCheck className="w-12 h-12 mx-auto text-green-500 mb-2" />
              <p className="font-manrope text-sm text-gray-600">
                Code sent to <strong>{phoneNumber}</strong>
              </p>
            </div>
            
            {testOtp && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-center">
                <p className="font-manrope text-xs text-yellow-700">
                  Test Mode: Your OTP is <strong className="text-lg">{testOtp}</strong>
                </p>
              </div>
            )}
            
            <Input
              type="text"
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="Enter 6-digit code"
              className="h-14 text-center text-2xl tracking-widest font-manrope rounded-xl"
              maxLength={6}
              data-testid="otp-input"
            />
            
            <Button
              onClick={handleVerifyOtp}
              disabled={loading || otpCode.length !== 6}
              className="w-full h-12 bg-black text-white hover:bg-gray-900 rounded-full font-manrope font-semibold"
              data-testid="verify-otp-btn"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Verifying...
                </span>
              ) : (
                "Verify Code"
              )}
            </Button>
            
            <div className="flex items-center justify-between">
              <Button
                variant="ghost"
                onClick={() => setStep(1)}
                className="font-manrope text-sm"
              >
                <ArrowLeft className="w-4 h-4 mr-1" />
                Change number
              </Button>
              
              <Button
                variant="ghost"
                onClick={handleSendOtp}
                disabled={countdown > 0}
                className="font-manrope text-sm"
              >
                {countdown > 0 ? `Resend in ${countdown}s` : "Resend code"}
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Account Details */}
        {step === 3 && (
          <form onSubmit={handleRegister} className="space-y-4">
            {/* Verified Phone Badge */}
            <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-full px-4 py-2">
              <ShieldCheck className="w-5 h-5 text-green-500" />
              <span className="font-manrope text-sm text-green-700">
                {phoneNumber} verified
              </span>
            </div>
            
            {/* Name */}
            <div className="relative">
              <User className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <Input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Full name"
                className="pl-12 h-12 rounded-full font-manrope"
                required
                data-testid="name-input"
              />
            </div>

            {/* Email */}
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email address"
                className="pl-12 h-12 rounded-full font-manrope"
                required
                data-testid="email-input"
              />
            </div>

            {/* Password */}
            <div>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <Input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password (min 6 characters)"
                  className="pl-12 pr-12 h-12 rounded-full font-manrope"
                  required
                  data-testid="password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              
              {/* Password Strength */}
              {password && (
                <div className="mt-2 px-4">
                  <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${passwordStrength.color} transition-all duration-300`}
                      style={{ width: passwordStrength.width }}
                    ></div>
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <Input
                type={showPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password"
                className="pl-12 h-12 rounded-full font-manrope"
                required
                data-testid="confirm-password-input"
              />
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={loading || password !== confirmPassword || password.length < 6}
              className="w-full h-12 bg-black text-white hover:bg-gray-900 rounded-full font-manrope font-semibold"
              data-testid="register-submit-btn"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Creating account...
                </span>
              ) : (
                "Create Account"
              )}
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
