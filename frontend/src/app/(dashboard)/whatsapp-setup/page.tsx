"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Loader2, CheckCircle, XCircle, RefreshCw, Smartphone } from "lucide-react";
import toast from "react-hot-toast";

const API_BASE = "/api/v1";

interface WhatsAppStatus {
  status: string;
  connected: boolean;
  phone_number: string | null;
  qr_code: string | null;
}

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export default function WhatsAppSetupPage() {
  const [status, setStatus] = useState<WhatsAppStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await apiRequest<WhatsAppStatus>("/channel/whatsapp/status");
      setStatus(data);
      return data;
    } catch {
      return null;
    }
  }, []);

  // Initial status check
  useEffect(() => {
    fetchStatus();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchStatus]);

  const startConnection = async () => {
    setLoading(true);
    try {
      const data = await apiRequest<WhatsAppStatus>("/channel/whatsapp/connect", {
        method: "POST",
      });
      setStatus(data);

      if (data.status === "connected") {
        toast.success(`Connected: +${data.phone_number}`);
      } else {
        // Start polling for QR scan completion
        setPolling(true);
        pollRef.current = setInterval(async () => {
          const updated = await fetchStatus();
          if (updated?.connected) {
            if (pollRef.current) clearInterval(pollRef.current);
            setPolling(false);
            toast.success(`Connected: +${updated.phone_number}`);
          }
        }, 3000);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setLoading(false);
    }
  };

  const disconnect = async () => {
    try {
      await apiRequest("/channel/whatsapp/disconnect", { method: "POST" });
      setStatus({ status: "disconnected", connected: false, phone_number: null, qr_code: null });
      if (pollRef.current) clearInterval(pollRef.current);
      setPolling(false);
      toast.success("Disconnected");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Disconnect failed");
    }
  };

  const reset = async () => {
    setLoading(true);
    try {
      if (pollRef.current) clearInterval(pollRef.current);
      setPolling(false);
      await apiRequest("/channel/whatsapp/reset", { method: "POST" });
      toast.success("Session reset. Click Connect to scan QR again.");
      setStatus({ status: "disconnected", connected: false, phone_number: null, qr_code: null });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setLoading(false);
    }
  };

  const isConnected = status?.connected;
  const hasQR = status?.qr_code && !isConnected;

  return (
    <div className="max-w-lg mx-auto py-12 px-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Smartphone className="h-6 w-6 text-green-600" />
          WhatsApp Bot Setup
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Connect your WhatsApp to enable automated case follow-ups.
        </p>
      </div>

      {/* Status Card */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        {/* Connection Status */}
        <div className="flex items-center gap-3 mb-6">
          {isConnected ? (
            <>
              <CheckCircle className="h-5 w-5 text-green-500" />
              <div>
                <p className="text-sm font-semibold text-green-700">Connected</p>
                <p className="text-xs text-gray-500">+{status?.phone_number}</p>
              </div>
            </>
          ) : status?.status === "connecting" || status?.status === "qr" ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin text-amber-500" />
              <div>
                <p className="text-sm font-semibold text-amber-700">Connecting...</p>
                <p className="text-xs text-gray-500">Scan the QR code below</p>
              </div>
            </>
          ) : (
            <>
              <XCircle className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-sm font-semibold text-gray-600">Not Connected</p>
                <p className="text-xs text-gray-500">Click Connect to start</p>
              </div>
            </>
          )}
        </div>

        {/* QR Code */}
        {hasQR && (
          <div className="flex flex-col items-center gap-3 mb-6">
            <div className="rounded-lg border-2 border-dashed border-gray-200 p-4 bg-white">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={status.qr_code!}
                alt="WhatsApp QR Code"
                className="w-64 h-64"
              />
            </div>
            <p className="text-xs text-gray-500 text-center">
              Open WhatsApp on your phone &gt; Settings &gt; Linked Devices &gt; Link a Device
            </p>
            {polling && (
              <div className="flex items-center gap-2 text-xs text-amber-600">
                <Loader2 className="h-3 w-3 animate-spin" />
                Waiting for scan...
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          {!isConnected ? (
            <button
              onClick={startConnection}
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Smartphone className="h-4 w-4" />
              )}
              Connect WhatsApp
            </button>
          ) : (
            <button
              onClick={disconnect}
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-100 transition-colors"
            >
              Disconnect
            </button>
          )}

          <button
            onClick={reset}
            disabled={loading}
            className="flex items-center justify-center gap-2 rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            title="Reset session"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Info */}
      <div className="mt-6 rounded-lg bg-blue-50 border border-blue-100 p-4">
        <p className="text-xs text-blue-700 leading-relaxed">
          <strong>How it works:</strong> After a seller files a case via voice, the WhatsApp
          bot automatically messages them to collect remaining details (documents, GSTIN, PAN, etc.).
          This is a one-time admin setup — connect once and the bot handles all follow-ups.
        </p>
      </div>
    </div>
  );
}
