"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Scale, Phone, ArrowRight, Shield, Factory, Settings, Building2 } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import * as api from "@/lib/api";
import toast from "react-hot-toast";

const SELLER_DEMOS = [
  { udyam: "UDYAM-MH-01-0012345", name: "Rajesh Kumar", org: "Kumar Enterprises" },
  { udyam: "UDYAM-RJ-02-0067890", name: "Priya Sharma", org: "Sharma Textiles Pvt Ltd" },
];

const ADMIN_DEMO = { mobile: "9876543200", name: "Admin User", org: "ODRMitra Platform" };

type LoginType = "seller" | "admin";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth, hydrate, isAuthenticated, role } = useAuthStore();
  const [loginType, setLoginType] = useState<LoginType>("seller");
  const [udyamNumber, setUdyamNumber] = useState("");
  const [adminMobile, setAdminMobile] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace(role === "admin" ? "/admin" : "/dashboard");
    }
  }, [isAuthenticated, role, router]);

  const handleSellerLogin = async (udyam?: string) => {
    const num = udyam || udyamNumber;
    if (!num || num.trim().length < 5) {
      toast.error("Enter a valid Udyam Registration Number");
      return;
    }
    setLoading(true);
    try {
      const res = await api.loginWithUdyam(num.trim());
      if (res.role === "admin") {
        toast.error("Please use the Admin login");
        return;
      }
      setAuth(res.access_token, res.user_id, res.name, res.role);
      toast.success(`Welcome, ${res.name}!`);
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleAdminLogin = async (mobile?: string) => {
    const num = mobile || adminMobile;
    if (!num || num.length < 10) {
      toast.error("Enter a valid 10-digit mobile number");
      return;
    }
    setLoading(true);
    try {
      const res = await api.login(num);
      if (res.role !== "admin") {
        toast.error("Please use the Seller login");
        return;
      }
      setAuth(res.access_token, res.user_id, res.name, res.role);
      toast.success(`Welcome, ${res.name}!`);
      router.push("/admin");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left panel — branding */}
      <div className="hidden w-1/2 flex-col justify-between bg-navy-600 p-12 text-white lg:flex">
        <div>
          <div className="flex items-center gap-3">
            <Scale className="h-10 w-10 text-saffron-400" />
            <div>
              <h1 className="text-3xl font-bold tracking-tight">ODRMitra</h1>
              <p className="text-sm text-navy-200">ओडीआर मित्र</p>
            </div>
          </div>

          <div className="mt-16 max-w-md">
            <h2 className="text-2xl font-semibold leading-snug">
              AI-Powered Dispute Resolution for MSMEs
            </h2>
            <p className="mt-4 text-navy-200 leading-relaxed">
              Resolve delayed payment disputes faster with voice-assisted case filing,
              automated document analysis, AI-driven outcome prediction, and guided
              negotiation — all aligned with MSMED Act 2006.
            </p>
          </div>

          <div className="mt-12 grid grid-cols-2 gap-4">
            {[
              "Voice-based Filing",
              "Document Analysis",
              "Outcome Prediction",
              "AI Negotiation",
              "Interest Calculator",
              "Settlement Drafting",
            ].map((feature) => (
              <div
                key={feature}
                className="flex items-center gap-2 rounded-lg border border-navy-500 px-3 py-2 text-sm text-navy-100"
              >
                <div className="h-1.5 w-1.5 rounded-full bg-saffron-400" />
                {feature}
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-navy-300">
          <Shield className="h-4 w-4" />
          IndiaAI Innovation Challenge 2026 — Ministry of MSME
        </div>
      </div>

      {/* Right panel — login */}
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md">
          {/* Mobile branding */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <Scale className="h-8 w-8 text-navy-600" />
            <span className="text-2xl font-bold text-navy-600">ODRMitra</span>
          </div>

          <h2 className="text-2xl font-bold text-gray-900">Sign In</h2>
          <p className="mt-1 text-sm text-gray-500">
            {loginType === "seller"
              ? "Login with your Udyam Registration Number"
              : "Admin portal access"}
          </p>

          {/* Toggle */}
          <div className="mt-6 flex rounded-lg bg-gray-100 p-1">
            <button
              onClick={() => setLoginType("seller")}
              className={`flex flex-1 items-center justify-center gap-2 rounded-md py-2.5 text-sm font-medium transition-all ${
                loginType === "seller"
                  ? "bg-white text-saffron-700 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <Factory className="h-4 w-4" />
              Seller / MSME
            </button>
            <button
              onClick={() => setLoginType("admin")}
              className={`flex flex-1 items-center justify-center gap-2 rounded-md py-2.5 text-sm font-medium transition-all ${
                loginType === "admin"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              <Settings className="h-4 w-4" />
              Admin
            </button>
          </div>

          {/* Seller Login */}
          {loginType === "seller" && (
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700">
                Udyam Registration Number
              </label>
              <div className="relative mt-1">
                <Building2 className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="e.g. UDYAM-MH-01-0012345"
                  value={udyamNumber}
                  onChange={(e) => setUdyamNumber(e.target.value.toUpperCase())}
                  onKeyDown={(e) => e.key === "Enter" && handleSellerLogin()}
                  className="w-full rounded-lg border border-gray-300 py-3 pl-11 pr-4 text-sm tracking-wider uppercase focus:border-saffron-400 focus:outline-none focus:ring-2 focus:ring-saffron-400/20"
                />
              </div>

              <button
                onClick={() => handleSellerLogin()}
                disabled={loading}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-saffron-500 py-3 text-sm font-semibold text-white transition-colors hover:bg-saffron-600 disabled:opacity-50"
              >
                {loading ? (
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>

              {/* Demo accounts */}
              <div className="mt-8">
                <p className="mb-3 text-xs font-medium uppercase tracking-wider text-gray-400">
                  Demo Accounts (click to login)
                </p>
                <div className="space-y-2">
                  {SELLER_DEMOS.map((u) => (
                    <button
                      key={u.udyam}
                      onClick={() => {
                        setUdyamNumber(u.udyam);
                        handleSellerLogin(u.udyam);
                      }}
                      disabled={loading}
                      className="flex w-full items-center gap-3 rounded-lg border border-gray-200 px-4 py-3 text-left transition-colors hover:border-saffron-300 hover:bg-saffron-50 disabled:opacity-50"
                    >
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-saffron-100 text-sm font-bold text-saffron-700">
                        {u.name[0]}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">{u.name}</p>
                        <p className="text-xs text-gray-500">{u.org}</p>
                      </div>
                      <span className="font-mono text-[10px] text-gray-400">{u.udyam}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Admin Login */}
          {loginType === "admin" && (
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700">
                Mobile Number
              </label>
              <div className="relative mt-1">
                <Phone className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="tel"
                  placeholder="Enter 10-digit mobile number"
                  value={adminMobile}
                  onChange={(e) => setAdminMobile(e.target.value.replace(/\D/g, "").slice(0, 10))}
                  onKeyDown={(e) => e.key === "Enter" && handleAdminLogin()}
                  className="w-full rounded-lg border border-gray-300 py-3 pl-11 pr-4 text-lg tracking-wider focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>

              <button
                onClick={() => handleAdminLogin()}
                disabled={loading}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? (
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>

              {/* Demo account */}
              <div className="mt-8">
                <p className="mb-3 text-xs font-medium uppercase tracking-wider text-gray-400">
                  Demo Account (click to login)
                </p>
                <button
                  onClick={() => {
                    setAdminMobile(ADMIN_DEMO.mobile);
                    handleAdminLogin(ADMIN_DEMO.mobile);
                  }}
                  disabled={loading}
                  className="flex w-full items-center gap-3 rounded-lg border border-gray-200 px-4 py-3 text-left transition-colors hover:border-blue-300 hover:bg-blue-50 disabled:opacity-50"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700">
                    A
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{ADMIN_DEMO.name}</p>
                    <p className="text-xs text-gray-500">{ADMIN_DEMO.org}</p>
                  </div>
                  <span className="font-mono text-xs text-gray-400">{ADMIN_DEMO.mobile}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
