"use client";

import { MessageCircle } from "lucide-react";

export default function TelegramBotsPage() {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-50 mb-4">
        <MessageCircle className="h-8 w-8 text-blue-400" />
      </div>
      <h2 className="text-xl font-semibold text-gray-900 mb-2">Telegram Bot Integration</h2>
      <p className="text-sm text-gray-500 max-w-sm text-center">
        Telegram bot management is coming soon. You&apos;ll be able to connect and manage
        Telegram bots for automated dispute follow-ups.
      </p>
    </div>
  );
}
