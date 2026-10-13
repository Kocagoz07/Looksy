import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Lock, Eye, EyeOff } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiErrorMessage } from "@/utils/apiError";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  const mismatch = confirm && password !== confirm;
  const tooShort = password && password.length < 8;

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await axios.post(`${BACKEND_URL}/api/auth/reset-password`, { token, new_password: password });
      toast.success(data.message);
      navigate("/", { replace: true });
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="max-w-md w-full space-y-8" data-testid="reset-password-page">
        <div className="text-center space-y-3">
          <h1 className="font-italiana text-5xl">Looksy</h1>
          <p className="font-manrope text-xs tracking-[0.3em] uppercase text-gray-500">Choose a new password</p>
        </div>
        {!token ? (
          <p data-testid="reset-password-missing-token" className="font-manrope text-center text-sm text-red-500">
            This reset link is missing its token. Please request a new one.
          </p>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            {[["New password", password, setPassword, "reset-password-input"], ["Confirm password", confirm, setConfirm, "reset-password-confirm-input"]].map(([ph, val, set, id]) => (
              <div key={id} className="relative">
                <Lock className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <Input data-testid={id} type={show ? "text" : "password"} value={val} required placeholder={ph}
                  onChange={(e) => set(e.target.value)} className="pl-14 pr-14 h-14 rounded-full font-manrope" />
              </div>
            ))}
            <button type="button" data-testid="reset-password-toggle-visibility" onClick={() => setShow(!show)}
              className="flex items-center gap-2 ml-5 font-manrope text-xs text-gray-500 hover:text-black">
              {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />} {show ? "Hide" : "Show"} passwords
            </button>
            {(tooShort || mismatch) && (
              <p data-testid="reset-password-error" className="ml-5 font-manrope text-xs text-red-500">
                {tooShort ? "Use at least 8 characters." : "Passwords do not match."}
              </p>
            )}
            <Button data-testid="reset-password-submit-btn" type="submit"
              disabled={loading || !password || tooShort || password !== confirm}
              className="w-full h-14 rounded-full bg-black text-white hover:bg-gray-900 font-manrope">
              {loading ? "Saving..." : "Update password"}
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
