"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Smartphone,
  Plus,
  Loader2,
  CheckCircle,
  XCircle,
  RefreshCw,
  Trash2,
} from "lucide-react";
import * as api from "@/lib/api";
import toast from "react-hot-toast";

export default function WhatsAppBotsPage() {
  const [bots, setBots] = useState<api.AdminBot[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [qrData, setQrData] = useState<{ qr: string; bot_id: string } | null>(null);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadBots = useCallback(async () => {
    try {
      const data = await api.adminListBots();
      setBots(data);
    } catch {
      toast.error("Failed to load bots");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBots();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadBots]);

  const startPolling = (botId: string, initialQr?: string) => {
    if (initialQr) {
      setQrData({ qr: initialQr, bot_id: botId });
    }
    setPolling(true);
    pollRef.current = setInterval(async () => {
      try {
        const status = await api.adminGetBotStatus(botId);
        if (status.connected) {
          if (pollRef.current) clearInterval(pollRef.current);
          setPolling(false);
          setQrData(null);
          toast.success(`Connected: +${status.phone_number}`);
          loadBots();
        } else if (status.qr_code) {
          // QR appeared (or refreshed) — update display
          setQrData({ qr: status.qr_code, bot_id: botId });
        }
      } catch {
        // Ignore polling errors
      }
    }, 3000);
  };

  const connectNew = async () => {
    setConnecting(true);
    try {
      const data = await api.adminConnectBot();
      if (data.connected) {
        toast.success(`Connected: +${data.phone_number}`);
        loadBots();
      } else {
        // Start polling — QR may arrive immediately or after a few seconds
        startPolling(data.bot_id, data.qr_code || undefined);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setConnecting(false);
    }
  };

  const disconnectBot = async (botId: string) => {
    try {
      await api.adminDisconnectBot(botId);
      toast.success("Bot disconnected");
      loadBots();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Disconnect failed");
    }
  };

  const resetBot = async (botId: string) => {
    try {
      await api.adminResetBot(botId);
      toast.success("Bot session reset");
      loadBots();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Reset failed");
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Smartphone className="h-6 w-6 text-green-600" />
            WhatsApp Bots
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage connected WhatsApp bot instances
          </p>
        </div>
        <button
          onClick={connectNew}
          disabled={connecting}
          className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
        >
          {connecting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4" />
          )}
          Connect New Bot
        </button>
      </div>

      {/* QR Code Modal */}
      {qrData && (
        <div className="mb-6 rounded-xl border-2 border-dashed border-green-300 bg-green-50 p-6">
          <div className="flex flex-col items-center gap-4">
            <h3 className="text-sm font-semibold text-green-800">Scan QR Code with WhatsApp</h3>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={qrData.qr} alt="WhatsApp QR" className="w-64 h-64 rounded-lg" />
            <p className="text-xs text-green-700">
              Open WhatsApp &gt; Settings &gt; Linked Devices &gt; Link a Device
            </p>
            {polling && (
              <div className="flex items-center gap-2 text-xs text-green-700">
                <Loader2 className="h-3 w-3 animate-spin" />
                Waiting for scan...
              </div>
            )}
            <button
              onClick={() => {
                if (pollRef.current) clearInterval(pollRef.current);
                setPolling(false);
                setQrData(null);
              }}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Bots Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : bots.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Smartphone className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p className="text-sm">No bots connected yet.</p>
          <p className="text-xs mt-1">Click &quot;Connect New Bot&quot; to get started.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Label
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Phone Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Connected
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {bots.map((bot) => (
                <tr key={bot.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">
                    {bot.label || "Bot"}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 font-mono">
                    {bot.phone_number ? `+${bot.phone_number}` : "—"}
                  </td>
                  <td className="px-6 py-4">
                    {bot.status === "connected" ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
                        <CheckCircle className="h-3 w-3" /> Connected
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
                        <XCircle className="h-3 w-3" /> {bot.status}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-xs text-gray-500">
                    {bot.created_at ? new Date(bot.created_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => resetBot(bot.id)}
                        className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                        title="Reset session"
                      >
                        <RefreshCw className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => disconnectBot(bot.id)}
                        className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                        title="Disconnect"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
