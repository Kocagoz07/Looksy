import { useState } from "react";
import { MailWarning } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { apiErrorMessage } from "@/utils/apiError";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const EmailVerifyBanner = ({ user }) => {
  const [sending, setSending] = useState(false);
  const [devLink, setDevLink] = useState(null);

  if (!user || user.email_verified !== false) return null;

  const resend = async () => {
    setSending(true);
    try {
      const { data } = await axios.post(`${BACKEND_URL}/api/auth/resend-verification`, {}, { withCredentials: true });
      toast.success(data.message);
      setDevLink(data.verification_link || null);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSending(false);
    }
  };

  return (
    <div data-testid="email-verify-banner"
      className="mb-6 flex flex-wrap items-center gap-3 rounded-2xl border border-current/20 px-4 py-3 font-manrope text-sm backdrop-blur-sm">
      <MailWarning className="w-4 h-4 shrink-0" />
      <span className="flex-1 min-w-[200px]">
        Please verify <strong>{user.email}</strong> — check your inbox for the link.
      </span>
      {devLink && (
        <a data-testid="email-verify-dev-link" href={devLink} className="underline text-xs opacity-70">Dev mode: open link</a>
      )}
      <button data-testid="email-verify-resend-btn" onClick={resend} disabled={sending}
        className="rounded-full border border-current px-4 py-1.5 text-xs font-semibold hover:opacity-70 transition-opacity disabled:opacity-40">
        {sending ? "Sending..." : "Resend email"}
      </button>
    </div>
  );
};
