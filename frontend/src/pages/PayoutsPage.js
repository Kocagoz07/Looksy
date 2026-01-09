import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, CheckCircle, XCircle, Clock, DollarSign, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function PayoutsPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [kycDialogOpen, setKycDialogOpen] = useState(false);
  const [payoutMethodDialogOpen, setPayoutMethodDialogOpen] = useState(false);
  const [requestPayoutDialogOpen, setRequestPayoutDialogOpen] = useState(false);
  
  // KYC Form
  const [kycData, setKycData] = useState({
    full_name: "",
    date_of_birth: "",
    address: "",
    id_type: "passport",
    id_number: ""
  });
  
  // Payout Method Form
  const [payoutMethod, setPayoutMethod] = useState("paypal");
  const [payoutEmail, setPayoutEmail] = useState("");
  
  // Request Payout Form
  const [payoutAmount, setPayoutAmount] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [userRes, payoutsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/auth/me`, { withCredentials: true }),
        axios.get(`${BACKEND_URL}/api/users/me/payouts`, { withCredentials: true })
      ]);
      
      setUser(userRes.data);
      setPayouts(payoutsRes.data);
    } catch (err) {
      console.error("Error fetching data:", err);
      toast.error("Failed to load payout information");
    } finally {
      setLoading(false);
    }
  };

  const handleKYCSubmit = async () => {
    try {
      await axios.post(
        `${BACKEND_URL}/api/users/me/kyc`,
        kycData,
        { withCredentials: true }
      );
      toast.success("KYC documents submitted successfully!");
      setKycDialogOpen(false);
      fetchData();
    } catch (err) {
      console.error("Error submitting KYC:", err);
      toast.error("Failed to submit KYC documents");
    }
  };

  const handlePayoutMethodSubmit = async () => {
    try {
      await axios.post(
        `${BACKEND_URL}/api/users/me/payout-method`,
        {
          method: payoutMethod,
          payout_email: payoutEmail
        },
        { withCredentials: true }
      );
      toast.success("Payout method set successfully!");
      setPayoutMethodDialogOpen(false);
      fetchData();
    } catch (err) {
      console.error("Error setting payout method:", err);
      toast.error(err.response?.data?.detail || "Failed to set payout method");
    }
  };

  const handleRequestPayout = async () => {
    const amount = parseFloat(payoutAmount);
    if (isNaN(amount) || amount <= 0) {
      toast.error("Please enter a valid amount");
      return;
    }

    try {
      await axios.post(
        `${BACKEND_URL}/api/users/me/request-payout`,
        { amount_eur: amount },
        { withCredentials: true }
      );
      toast.success("Payout requested successfully!");
      setRequestPayoutDialogOpen(false);
      setPayoutAmount("");
      fetchData();
    } catch (err) {
      console.error("Error requesting payout:", err);
      toast.error(err.response?.data?.detail || "Failed to request payout");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black\"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white\">
      <header className="border-b px-4 py-4 flex items-center gap-4 sticky top-0 bg-white z-10">
        <Button
          onClick={() => navigate(-1)}
          variant="ghost"
          size="icon"
          className="rounded-full"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <h1 className="font-playfair text-2xl font-bold">Payouts</h1>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* Balance Card */}
        <div className="bg-gradient-to-r from-green-600 to-green-700 text-white rounded-2xl p-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-manrope text-sm opacity-90 mb-1">Available Balance</p>
              <p className="font-playfair text-5xl font-bold">
                €{user?.earnings_eur?.toFixed(2) || '0.00'}
              </p>
              <p className="font-manrope text-sm opacity-75 mt-2">
                ${user?.earnings?.toFixed(2) || '0.00'} USD
              </p>
            </div>
            <Wallet className="w-16 h-16 opacity-20" />
          </div>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* KYC Status */}
          <div className="border rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-playfair text-lg font-semibold">Identity Verification</h3>
              {user?.kyc_verified ? (
                <CheckCircle className="w-6 h-6 text-green-600" />
              ) : (
                <XCircle className="w-6 h-6 text-gray-400" />
              )}
            </div>
            <p className="font-manrope text-sm text-gray-600 mb-4">
              {user?.kyc_verified 
                ? "Your identity has been verified" 
                : "Complete KYC to enable payouts"}
            </p>
            {!user?.kyc_verified && (
              <Button
                onClick={() => setKycDialogOpen(true)}
                className="w-full bg-black text-white hover:bg-gray-800"
              >
                Complete KYC
              </Button>
            )}
          </div>

          {/* Payout Method */}
          <div className="border rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-playfair text-lg font-semibold">Payout Method</h3>
              {user?.payout_method ? (
                <CheckCircle className="w-6 h-6 text-green-600" />
              ) : (
                <XCircle className="w-6 h-6 text-gray-400" />
              )}
            </div>
            <p className="font-manrope text-sm text-gray-600 mb-4">
              {user?.payout_method 
                ? `${user.payout_method === 'paypal' ? 'PayPal' : 'Stripe'}: ${user.payout_email}` 
                : "Set up your payout method"}
            </p>
            <Button
              onClick={() => setPayoutMethodDialogOpen(true)}
              variant={user?.payout_method ? "outline" : "default"}
              className={!user?.payout_method ? "w-full bg-black text-white hover:bg-gray-800" : "w-full"}
            >
              {user?.payout_method ? 'Change Method' : 'Set up Method'}
            </Button>
          </div>
        </div>

        {/* Request Payout Button */}
        {user?.kyc_verified && user?.payout_method && (
          <Button
            onClick={() => setRequestPayoutDialogOpen(true)}
            className="w-full bg-green-600 hover:bg-green-700 text-white py-6 font-manrope font-semibold rounded-full text-lg"
            disabled={!user?.earnings_eur || user.earnings_eur < 20}
          >
            <DollarSign className="w-5 h-5 mr-2" />
            Request Payout (Minimum €20)
          </Button>
        )}

        {/* Payout History */}
        <div>
          <h2 className="font-playfair text-2xl font-bold mb-4">Payout History</h2>
          
          {payouts.length === 0 ? (
            <div className="text-center py-12 border rounded-lg">
              <p className="font-manrope text-gray-500">No payouts yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {payouts.map((payout) => (
                <div key={payout.payout_id} className="border rounded-lg p-4 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      payout.status === 'completed' ? 'bg-green-100' :
                      payout.status === 'pending' ? 'bg-yellow-100' : 'bg-red-100'
                    }`}>
                      {payout.status === 'completed' && <CheckCircle className="w-5 h-5 text-green-600" />}
                      {payout.status === 'pending' && <Clock className="w-5 h-5 text-yellow-600" />}
                      {payout.status === 'failed' && <XCircle className="w-5 h-5 text-red-600" />}
                    </div>
                    <div>
                      <p className="font-manrope font-semibold">€{payout.amount_eur.toFixed(2)}</p>
                      <p className="font-manrope text-sm text-gray-600">
                        {new Date(payout.created_at).toLocaleDateString()} • {payout.method}
                      </p>
                    </div>
                  </div>
                  <span className={`font-manrope text-sm font-semibold capitalize ${
                    payout.status === 'completed' ? 'text-green-600' :
                    payout.status === 'pending' ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {payout.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* KYC Dialog */}
      <Dialog open={kycDialogOpen} onOpenChange={setKycDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Complete KYC Verification</DialogTitle>
            <DialogDescription>
              Please provide your identification documents to enable payouts.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Full Name</Label>
              <Input
                value={kycData.full_name}
                onChange={(e) => setKycData({...kycData, full_name: e.target.value})}
                placeholder="John Doe"
              />
            </div>
            <div>
              <Label>Date of Birth</Label>
              <Input
                type="date"
                value={kycData.date_of_birth}
                onChange={(e) => setKycData({...kycData, date_of_birth: e.target.value})}
              />
            </div>
            <div>
              <Label>Address</Label>
              <Input
                value={kycData.address}
                onChange={(e) => setKycData({...kycData, address: e.target.value})}
                placeholder="123 Main St, City, Country"
              />
            </div>
            <div>
              <Label>ID Type</Label>
              <Select value={kycData.id_type} onValueChange={(val) => setKycData({...kycData, id_type: val})}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="passport">Passport</SelectItem>
                  <SelectItem value="drivers_license">Driver's License</SelectItem>
                  <SelectItem value="national_id">National ID</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>ID Number</Label>
              <Input
                value={kycData.id_number}
                onChange={(e) => setKycData({...kycData, id_number: e.target.value})}
                placeholder="ID123456789"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setKycDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleKYCSubmit} className="bg-black text-white hover:bg-gray-800">Submit</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payout Method Dialog */}
      <Dialog open={payoutMethodDialogOpen} onOpenChange={setPayoutMethodDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Set Payout Method</DialogTitle>
            <DialogDescription>
              Choose how you want to receive your earnings.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Payout Method</Label>
              <Select value={payoutMethod} onValueChange={setPayoutMethod}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="paypal">PayPal</SelectItem>
                  <SelectItem value="stripe">Stripe Connect</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>{payoutMethod === 'paypal' ? 'PayPal Email' : 'Stripe Email'}</Label>
              <Input
                type="email"
                value={payoutEmail}
                onChange={(e) => setPayoutEmail(e.target.value)}
                placeholder="your@email.com"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPayoutMethodDialogOpen(false)}>Cancel</Button>
            <Button onClick={handlePayoutMethodSubmit} className="bg-black text-white hover:bg-gray-800">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Request Payout Dialog */}
      <Dialog open={requestPayoutDialogOpen} onOpenChange={setRequestPayoutDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request Payout</DialogTitle>
            <DialogDescription>
              Enter the amount you want to withdraw (minimum €20).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Available Balance</Label>
              <p className="font-playfair text-3xl font-bold text-green-600 mt-2">
                €{user?.earnings_eur?.toFixed(2) || '0.00'}
              </p>
            </div>
            <div>
              <Label>Payout Amount (EUR)</Label>
              <Input
                type="number"
                step="0.01"
                min="20"
                max={user?.earnings_eur || 0}
                value={payoutAmount}
                onChange={(e) => setPayoutAmount(e.target.value)}
                placeholder="20.00"
              />
              <p className="font-manrope text-xs text-gray-500 mt-1">
                Minimum: €20.00 • Maximum: €{user?.earnings_eur?.toFixed(2) || '0.00'}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRequestPayoutDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleRequestPayout} className="bg-green-600 hover:bg-green-700 text-white">
              Request Payout
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
