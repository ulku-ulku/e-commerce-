"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("demo@commerce.ai");
  const [password, setPassword] = useState("demo1234");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch {
      setErr("E-posta veya şifre hatalı");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={onSubmit} className="w-full max-w-sm bg-white rounded-xl shadow p-8 space-y-4">
        <div>
          <h1 className="text-2xl font-bold">Commerce-AI</h1>
          <p className="text-sm text-slate-500">E-ticaret içgörü paneline giriş</p>
        </div>
        <input className="w-full border rounded-lg px-3 py-2" type="email" placeholder="E-posta"
          value={email} onChange={(e) => setEmail(e.target.value)} />
        <input className="w-full border rounded-lg px-3 py-2" type="password" placeholder="Şifre"
          value={password} onChange={(e) => setPassword(e.target.value)} />
        {err && <p className="text-sm text-red-600">{err}</p>}
        <button disabled={loading}
          className="w-full bg-slate-900 text-white rounded-lg py-2 font-medium disabled:opacity-50">
          {loading ? "Giriş yapılıyor…" : "Giriş Yap"}
        </button>
        <p className="text-xs text-slate-400 text-center">demo@commerce.ai / demo1234</p>
      </form>
    </div>
  );
}
