import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  ArrowLeft, 
  Star, 
  Wallet, 
  CreditCard, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle,
  ArrowRight,
  Sparkles,
  DollarSign,
  Euro,
  Shield,
  Clock,
  TrendingUp
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function RewardsPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [rewardsInfo, setRewardsInfo] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [kycStatus, setKycStatus] = useState(null);
  
  // Conversion states
  const [starsToConvert, setStarsToConvert] = useState("");
  const [converting, setConverting] = useState(false);
  
  // KYC states
  const [showKycModal, setShowKycModal] = useState(false);
  const [kycSubmitting, setKycSubmitting] = useState(false);
  const [kycForm, setKycForm] = useState({
    full_name: "",
    date_of_birth: "",
    address: "",
    country: "",
    id_type: "passport",
    id_number: ""
  });
  
  // Payout states
  const [showPayoutModal, setShowPayoutModal] = useState(false);
  const [payoutMethod, setPayoutMethod] = useState("stripe");
  const [payoutAmount, setPayoutAmount] = useState("");
  const [paypalEmail, setPaypalEmail] = useState("");
  const [payoutProcessing, setPayoutProcessing] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [rewardsRes, kycRes, historyRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/rewards/info`, { withCredentials: true }),
        axios.get(`${BACKEND_URL}/api/kyc/status`, { withCredentials: true }),
        axios.get(`${BACKEND_URL}/api/payout/history`, { withCredentials: true })
      ]);
      
      setRewardsInfo(rewardsRes.data);
      setKycStatus(kycRes.data);
      setTransactions(historyRes.data.transactions || []);
    } catch (err) {
      console.error("Error fetching data:", err);
      if (err.response?.status === 401) {
        navigate("/");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleConvertStars = async () => {
    const stars = parseInt(starsToConvert);
    if (!stars || stars <= 0) {
      toast.error("Please enter a valid number of stars");
      return;
    }
    
    if (stars > rewardsInfo?.stars) {
      toast.error(`You only have ${rewardsInfo?.stars} stars`);
      return;
    }
    
    setConverting(true);
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/rewards/convert-stars`,
        { stars_to_convert: stars },
        { withCredentials: true }
      );
      
      toast.success(`Converted ${stars} stars to $${response.data.points_earned_usd.toFixed(4)}`);
      setStarsToConvert("");
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Conversion failed");
    } finally {
      setConverting(false);
    }
  };

  const handleKycSubmit = async () => {
    // Validate form
    if (!kycForm.full_name || !kycForm.date_of_birth || !kycForm.address || 
        !kycForm.country || !kycForm.id_number) {
      toast.error("Please fill in all fields");
      return;
    }
    
    setKycSubmitting(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/kyc/submit`,
        kycForm,
        { withCredentials: true }
      );
      
      toast.success("KYC verification completed!");
      setShowKycModal(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "KYC submission failed");
    } finally {
      setKycSubmitting(false);
    }
  };

  const handlePayout = async () => {
    const amount = parseFloat(payoutAmount);
    if (!amount || amount < 20) {
      toast.error("Minimum payout amount is €20");
      return;
    }
    
    if (payoutMethod === "paypal" && !paypalEmail) {
      toast.error("Please enter your PayPal email");
      return;
    }
    
    setPayoutProcessing(true);
    try {
      const endpoint = payoutMethod === "stripe" 
        ? "/api/payout/stripe/setup"
        : "/api/payout/paypal/setup";
      
      const payload = payoutMethod === "stripe"
        ? { amount_eur: amount, origin_url: window.location.origin }
        : { amount_eur: amount, paypal_email: paypalEmail };
      
      const response = await axios.post(
        `${BACKEND_URL}${endpoint}`,
        payload,
        { withCredentials: true }
      );
      
      toast.success(`Payout of €${amount} initiated successfully!`);
      setShowPayoutModal(false);
      setPayoutAmount("");
      setPaypalEmail("");
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Payout failed");
    } finally {
      setPayoutProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50" data-testid="rewards-page">
      {/* Header */}
      <header className="sticky top-0 bg-white/80 backdrop-blur-lg border-b z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate(-1)}
              data-testid="back-btn"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2">
              <Wallet className="w-6 h-6 text-indigo-600" />
              <h1 className="font-italiana text-2xl">Rewards & Payouts</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* Balance Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Stars Balance */}
          <div className="bg-gradient-to-br from-yellow-400 to-orange-500 rounded-2xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <Star className="w-8 h-8" />
              <Badge className="bg-white/20 text-white">Available</Badge>
            </div>
            <p className="font-italiana text-4xl mb-1">{rewardsInfo?.stars || 0}</p>
            <p className="font-manrope text-sm text-white/80">Stars Earned</p>
            <p className="font-manrope text-xs mt-2 text-white/60">
              Worth ${rewardsInfo?.potential_conversion_value_usd?.toFixed(4) || '0.00'}
            </p>
          </div>

          {/* Payout Points */}
          <div className="bg-gradient-to-br from-green-400 to-emerald-500 rounded-2xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <DollarSign className="w-8 h-8" />
              <Badge className="bg-white/20 text-white">Convertible</Badge>
            </div>
            <p className="font-italiana text-4xl mb-1">
              €{rewardsInfo?.payout_points_eur?.toFixed(2) || '0.00'}
            </p>
            <p className="font-manrope text-sm text-white/80">Payout Points</p>
            <p className="font-manrope text-xs mt-2 text-white/60">
              ${rewardsInfo?.payout_points_usd?.toFixed(2) || '0.00'} USD
            </p>
          </div>

          {/* Total Earnings */}
          <div className="bg-gradient-to-br from-purple-400 to-indigo-500 rounded-2xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <TrendingUp className="w-8 h-8" />
              <Badge className="bg-white/20 text-white">Lifetime</Badge>
            </div>
            <p className="font-italiana text-4xl mb-1">
              €{rewardsInfo?.earnings_eur?.toFixed(2) || '0.00'}
            </p>
            <p className="font-manrope text-sm text-white/80">Total Earnings</p>
            <p className="font-manrope text-xs mt-2 text-white/60">
              ${rewardsInfo?.earnings_usd?.toFixed(2) || '0.00'} USD
            </p>
          </div>
        </div>

        {/* KYC Status */}
        {!kycStatus?.kyc_verified && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
            <div className="flex items-start gap-4">
              <Shield className="w-8 h-8 text-amber-500 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="font-manrope font-bold text-amber-800 mb-1">
                  KYC Verification Required
                </h3>
                <p className="font-manrope text-sm text-amber-700 mb-4">
                  Complete identity verification to enable payouts. This is required for compliance.
                </p>
                <Button
                  onClick={() => setShowKycModal(true)}
                  className="bg-amber-500 hover:bg-amber-600 text-white rounded-full font-manrope"
                  data-testid="start-kyc-btn"
                >
                  <Shield className="w-4 h-4 mr-2" />
                  Start Verification
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Conversion Rates Card */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border">
          <h3 className="font-italiana text-xl mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-yellow-500" />
            Star Conversion Rates
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {rewardsInfo?.conversion_rates && Object.entries(rewardsInfo.conversion_rates)
              .filter(([key]) => key.startsWith('tier'))
              .map(([key, tier]) => (
                <div key={key} className="bg-gray-50 rounded-xl p-4">
                  <p className="font-manrope text-sm text-gray-500 mb-1">{tier.range}</p>
                  <p className="font-italiana text-2xl text-gray-800">
                    {tier.rate_cents}¢
                  </p>
                  <p className="font-manrope text-xs text-gray-400">per star</p>
                </div>
              ))}
          </div>
          <p className="font-manrope text-sm text-gray-500">
            Maximum: {rewardsInfo?.conversion_rates?.max_stars_per_post?.toLocaleString()} stars per post
          </p>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="convert" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="convert" className="font-manrope">Convert Stars</TabsTrigger>
            <TabsTrigger value="payout" className="font-manrope">Request Payout</TabsTrigger>
          </TabsList>

          {/* Convert Stars Tab */}
          <TabsContent value="convert" className="mt-6">
            <div className="bg-white rounded-2xl p-6 shadow-sm border">
              <h3 className="font-italiana text-xl mb-4">Convert Stars to Payout Points</h3>
              
              <div className="space-y-4">
                <div>
                  <Label className="font-manrope">Stars to Convert</Label>
                  <div className="flex gap-3 mt-2">
                    <Input
                      type="number"
                      value={starsToConvert}
                      onChange={(e) => setStarsToConvert(e.target.value)}
                      placeholder={`Max: ${rewardsInfo?.stars || 0}`}
                      max={rewardsInfo?.stars || 0}
                      className="font-manrope"
                      data-testid="stars-input"
                    />
                    <Button
                      onClick={() => setStarsToConvert(String(rewardsInfo?.stars || 0))}
                      variant="outline"
                      className="font-manrope whitespace-nowrap"
                    >
                      Max
                    </Button>
                  </div>
                </div>

                {starsToConvert && parseInt(starsToConvert) > 0 && (
                  <div className="bg-green-50 rounded-xl p-4">
                    <p className="font-manrope text-sm text-green-700">
                      You'll receive: <span className="font-bold">
                        ${calculatePayout(parseInt(starsToConvert)).toFixed(4)} USD
                      </span> ({" "}
                      €{(calculatePayout(parseInt(starsToConvert)) * 0.92).toFixed(4)} EUR)
                    </p>
                  </div>
                )}

                <Button
                  onClick={handleConvertStars}
                  disabled={converting || !starsToConvert || parseInt(starsToConvert) <= 0}
                  className="w-full bg-gradient-to-r from-yellow-400 to-orange-500 hover:from-yellow-500 hover:to-orange-600 text-white rounded-full font-manrope"
                  data-testid="convert-btn"
                >
                  {converting ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <ArrowRight className="w-4 h-4 mr-2" />
                  )}
                  Convert Stars
                </Button>
              </div>
            </div>
          </TabsContent>

          {/* Payout Tab */}
          <TabsContent value="payout" className="mt-6">
            <div className="bg-white rounded-2xl p-6 shadow-sm border">
              <h3 className="font-italiana text-xl mb-4">Request Payout</h3>
              
              {!kycStatus?.kyc_verified ? (
                <div className="text-center py-8">
                  <Shield className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p className="font-manrope text-gray-500 mb-4">
                    Complete KYC verification to request payouts
                  </p>
                  <Button
                    onClick={() => setShowKycModal(true)}
                    className="rounded-full font-manrope"
                  >
                    Start Verification
                  </Button>
                </div>
              ) : rewardsInfo?.payout_points_eur < 20 ? (
                <div className="text-center py-8">
                  <Euro className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p className="font-manrope text-gray-500 mb-2">
                    Minimum payout is €20
                  </p>
                  <p className="font-manrope text-sm text-gray-400">
                    You have €{rewardsInfo?.payout_points_eur?.toFixed(2)} - need €{(20 - rewardsInfo?.payout_points_eur).toFixed(2)} more
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-green-50 rounded-xl p-4 flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <p className="font-manrope text-sm text-green-700">
                      KYC verified - You can request payouts up to €{rewardsInfo?.payout_points_eur?.toFixed(2)}
                    </p>
                  </div>
                  
                  <Button
                    onClick={() => setShowPayoutModal(true)}
                    className="w-full bg-gradient-to-r from-green-400 to-emerald-500 hover:from-green-500 hover:to-emerald-600 text-white rounded-full font-manrope"
                    data-testid="request-payout-btn"
                  >
                    <Wallet className="w-4 h-4 mr-2" />
                    Request Payout
                  </Button>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>

        {/* Transaction History */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border">
          <h3 className="font-italiana text-xl mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-gray-400" />
            Payout History
          </h3>
          
          {transactions.length === 0 ? (
            <p className="font-manrope text-gray-500 text-center py-8">
              No payout transactions yet
            </p>
          ) : (
            <div className="space-y-3">
              {transactions.map((tx) => (
                <div 
                  key={tx.transaction_id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-xl"
                >
                  <div className="flex items-center gap-3">
                    {tx.payment_method === "stripe" ? (
                      <CreditCard className="w-5 h-5 text-indigo-500" />
                    ) : (
                      <Wallet className="w-5 h-5 text-blue-500" />
                    )}
                    <div>
                      <p className="font-manrope font-semibold">
                        €{tx.amount?.toFixed(2)} {tx.currency}
                      </p>
                      <p className="font-manrope text-xs text-gray-500">
                        {new Date(tx.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <Badge className={
                    tx.payment_status === "completed" 
                      ? "bg-green-100 text-green-700"
                      : tx.payment_status === "pending"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-red-100 text-red-700"
                  }>
                    {tx.payment_status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* KYC Modal */}
      <Dialog open={showKycModal} onOpenChange={setShowKycModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-italiana text-2xl flex items-center gap-2">
              <Shield className="w-6 h-6 text-indigo-600" />
              KYC Verification
            </DialogTitle>
            <DialogDescription className="font-manrope">
              Complete identity verification to enable payouts
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <div>
              <Label className="font-manrope">Full Legal Name</Label>
              <Input
                value={kycForm.full_name}
                onChange={(e) => setKycForm({...kycForm, full_name: e.target.value})}
                placeholder="John Doe"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="font-manrope">Date of Birth</Label>
              <Input
                type="date"
                value={kycForm.date_of_birth}
                onChange={(e) => setKycForm({...kycForm, date_of_birth: e.target.value})}
                className="mt-1"
              />
            </div>
            <div>
              <Label className="font-manrope">Address</Label>
              <Input
                value={kycForm.address}
                onChange={(e) => setKycForm({...kycForm, address: e.target.value})}
                placeholder="123 Main St, City"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="font-manrope">Country</Label>
              <Input
                value={kycForm.country}
                onChange={(e) => setKycForm({...kycForm, country: e.target.value})}
                placeholder="United States"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="font-manrope">ID Type</Label>
              <Select value={kycForm.id_type} onValueChange={(v) => setKycForm({...kycForm, id_type: v})}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="passport">Passport</SelectItem>
                  <SelectItem value="id_card">National ID Card</SelectItem>
                  <SelectItem value="drivers_license">Driver's License</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="font-manrope">ID Number</Label>
              <Input
                value={kycForm.id_number}
                onChange={(e) => setKycForm({...kycForm, id_number: e.target.value})}
                placeholder="ABC123456"
                className="mt-1"
              />
            </div>
          </div>

          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setShowKycModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleKycSubmit}
              disabled={kycSubmitting}
              className="bg-indigo-600 hover:bg-indigo-700"
            >
              {kycSubmitting ? "Submitting..." : "Submit Verification"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payout Modal */}
      <Dialog open={showPayoutModal} onOpenChange={setShowPayoutModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-italiana text-2xl flex items-center gap-2">
              <Wallet className="w-6 h-6 text-green-600" />
              Request Payout
            </DialogTitle>
            <DialogDescription className="font-manrope">
              Available: €{rewardsInfo?.payout_points_eur?.toFixed(2)} • Min: €20
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <div>
              <Label className="font-manrope">Payout Method</Label>
              <Select value={payoutMethod} onValueChange={setPayoutMethod}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="stripe">
                    <div className="flex items-center gap-2">
                      <CreditCard className="w-4 h-4" />
                      Stripe (Bank Transfer)
                    </div>
                  </SelectItem>
                  <SelectItem value="paypal">
                    <div className="flex items-center gap-2">
                      <Wallet className="w-4 h-4" />
                      PayPal
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label className="font-manrope">Amount (EUR)</Label>
              <Input
                type="number"
                value={payoutAmount}
                onChange={(e) => setPayoutAmount(e.target.value)}
                placeholder="20.00"
                min="20"
                max={rewardsInfo?.payout_points_eur || 0}
                className="mt-1"
              />
            </div>

            {payoutMethod === "paypal" && (
              <div>
                <Label className="font-manrope">PayPal Email</Label>
                <Input
                  type="email"
                  value={paypalEmail}
                  onChange={(e) => setPaypalEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="mt-1"
                />
              </div>
            )}
          </div>

          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setShowPayoutModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handlePayout}
              disabled={payoutProcessing}
              className="bg-green-600 hover:bg-green-700"
            >
              {payoutProcessing ? "Processing..." : "Request Payout"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Helper function to calculate payout locally (matches backend - flat rate per tier in EUR)
function calculatePayout(stars) {
  if (stars <= 0) return 0;
  stars = Math.min(stars, 10000);
  
  // Flat rate based on which tier the total falls into
  if (stars <= 1000) {
    // Tier 1: 0-1000 stars → €0.05 per star
    return stars * 0.05;
  } else if (stars <= 5000) {
    // Tier 2: 1001-5000 stars → €0.10 per star (flat rate for ALL stars)
    return stars * 0.10;
  } else {
    // Tier 3: 5001-10000 stars → €0.25 per star (flat rate for ALL stars)
    return stars * 0.25;
  }
}
