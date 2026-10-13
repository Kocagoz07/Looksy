import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle, XCircle } from "lucide-react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/utils/apiError";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function VerifyEmailPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [state, setState] = useState({ status: "loading" });
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    const token = params.get("token");
    if (!token) {
      setState({ status: "error", message: "This verification link is missing its token." });
      return;
    }
    axios
      .post(`${BACKEND_URL}/api/auth/verify-email`, { token })
      .then(({ data }) => setState({ status: "ok", message: `${data.email} is verified.` }))
      .catch((err) => setState({ status: "error", message: apiErrorMessage(err) }));
  }, [params]);

  const Icon = state.status === "ok" ? CheckCircle : XCircle;

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center space-y-6" data-testid="verify-email-page">
        <h1 className="font-italiana text-5xl">Looksy</h1>
        {state.status === "loading" ? (
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-black mx-auto" />
        ) : (
          <>
            <Icon className={`w-12 h-12 mx-auto ${state.status === "ok" ? "text-black" : "text-red-500"}`} />
            <p data-testid="verify-email-status" className="font-manrope text-gray-700">{state.message}</p>
            <Button data-testid="verify-email-continue-btn" onClick={() => navigate("/dashboard", { replace: true })}
              className="rounded-full h-12 px-8 bg-black text-white hover:bg-gray-900 font-manrope">
              Continue to Looksy
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
