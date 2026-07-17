import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/client";
import { useAuthStore } from "../store/authStore";

export default function Login() {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  async function requestOtp(event: FormEvent) {
    event.preventDefault();
    await apiClient.post("/api/v1/auth/otp/request", { phone_number: phoneNumber });
    setStep("otp");
  }

  async function verifyOtp(event: FormEvent) {
    event.preventDefault();
    const { data } = await apiClient.post("/api/v1/auth/otp/verify", {
      phone_number: phoneNumber,
      code,
    });
    login({ accessToken: data.access_token, refreshToken: data.refresh_token }, phoneNumber);
    navigate("/");
  }

  if (step === "phone") {
    return (
      <form onSubmit={requestOtp} className="flex flex-col gap-4 p-8 max-w-sm mx-auto">
        <input
          value={phoneNumber}
          onChange={(e) => setPhoneNumber(e.target.value)}
          placeholder="+91XXXXXXXXXX"
          className="rounded border px-3 py-2"
        />
        <button type="submit" className="rounded bg-blue-600 px-3 py-2 text-white">
          Send code
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={verifyOtp} className="flex flex-col gap-4 p-8 max-w-sm mx-auto">
      <input
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="6-digit code"
        className="rounded border px-3 py-2"
      />
      <button type="submit" className="rounded bg-blue-600 px-3 py-2 text-white">
        Verify
      </button>
    </form>
  );
}
