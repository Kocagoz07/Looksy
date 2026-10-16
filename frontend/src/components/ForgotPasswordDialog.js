import { useState } from "react";
import { Mail, ArrowRight } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/utils/apiError";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const ForgotPasswordDialog = ({ open, onOpenChange, initialEmail = "" }) => {
  const [email, setEmail] = useState(initialEmail);
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(null);

  const close = (v) => {
    onOpenChange(v);
    if (!v) setSent(null);
  };

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await axios.post(`${BACKEND_URL}/api/auth/forgot-password`, { email });
      setSent(data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent data-testid="forgot-password-dialog" className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-italiana text-3xl">Reset password</DialogTitle>
          <DialogDescription className="font-manrope">
            Enter your account email and we'll send you a link to choose a new password.
          </DialogDescription>
        </DialogHeader>
        {sent ? (
          <div className="space-y-4" data-testid="forgot-password-sent">
            <p className="font-manrope text-sm text-gray-700">{sent.message}</p>
            {sent.reset_link && (
              <a href={sent.reset_link} data-testid="forgot-password-dev-link"
                className="block text-center font-manrope text-xs underline text-gray-500 break-all">
                Dev mode: open reset link
              </a>
            )}
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <Input data-testid="forgot-password-email-input" type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)} placeholder="Email address"
                className="pl-14 h-14 rounded-full font-manrope" />
            </div>
            <Button data-testid="forgot-password-submit-btn" type="submit" disabled={loading || !email}
              className="w-full h-14 rounded-full bg-black text-white hover:bg-gray-900 font-manrope group">
              {loading ? "Sending..." : "Send reset link"}
              <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
};
