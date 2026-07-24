"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, LogOut, User, X } from "lucide-react";
import * as api from "@/lib/api";
import { formatMobile } from "@/lib/format";

/** Initials from a full name — first letter of the first two words. */
function initials(name: string | null): string {
  if (!name) return "?";
  const letters = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join("");
  return letters.toUpperCase() || "?";
}

interface UserMenuProps {
  name: string | null;
  role: string | null;
  onLogout: () => void;
}

export default function UserMenu({ name, role, onLogout }: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [profile, setProfile] = useState<api.UserProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [mounted, setMounted] = useState(false);

  const rowRef = useRef<HTMLButtonElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => setMounted(true), []);

  const loadProfile = useCallback(() => {
    if (profile || loading) return;
    setLoading(true);
    setError(null);
    api
      .getMe()
      .then(setProfile)
      .catch((e: Error) => setError(e.message || "Could not load profile"))
      .finally(() => setLoading(false));
  }, [profile, loading]);

  // Fetch when the card first opens — the header needs business name and email,
  // which the auth store does not hold.
  useEffect(() => {
    if (open) loadProfile();
  }, [open, loadProfile]);

  // Close the card on outside click.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!cardRef.current?.contains(t) && !rowRef.current?.contains(t)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  // Escape closes the modal first, then the card.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (profileOpen) {
        setProfileOpen(false);
        rowRef.current?.focus();
      } else if (open) {
        setOpen(false);
        rowRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, profileOpen]);

  useEffect(() => {
    if (profileOpen) closeRef.current?.focus();
  }, [profileOpen]);

  const openProfile = () => {
    setOpen(false);
    setProfileOpen(true);
    loadProfile();
  };

  return (
    <div className="relative">
      {/* Popup card */}
      {open && (
        <div
          ref={cardRef}
          role="menu"
          className="absolute bottom-full left-0 right-0 mb-2 overflow-hidden rounded-xl border border-navy-500 bg-navy-700 shadow-xl"
        >
          {/* Identity */}
          <div className="flex items-center gap-3 px-4 py-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-saffron-500 text-sm font-semibold text-white">
              {initials(name)}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">{name}</p>
              {loading && !profile ? (
                <div className="mt-1 h-3 w-28 animate-pulse rounded bg-navy-500" />
              ) : (
                profile?.organization_name && (
                  <p className="truncate text-xs text-navy-200">
                    {profile.organization_name}
                  </p>
                )
              )}
            </div>
          </div>

          <div className="border-t border-navy-500" />

          {/* Email */}
          <div className="px-4 pt-3">
            {loading && !profile ? (
              <div className="h-3 w-36 animate-pulse rounded bg-navy-500" />
            ) : (
              profile?.email && (
                <p className="truncate text-xs text-navy-300">{profile.email}</p>
              )
            )}
          </div>

          {/* Actions */}
          <div className="p-2 pt-2">
            <button
              role="menuitem"
              onClick={openProfile}
              className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-sm text-navy-100 transition-colors hover:bg-navy-500 hover:text-white"
            >
              <User className="h-4 w-4" />
              Profile
            </button>
          </div>

          <div className="border-t border-navy-500" />

          <div className="p-2">
            <button
              role="menuitem"
              onClick={onLogout}
              className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-sm text-red-400 transition-colors hover:bg-red-500/10 hover:text-red-300"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </div>
      )}

      {/* Collapsed row */}
      <button
        ref={rowRef}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition-colors hover:bg-navy-500"
      >
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-saffron-500 text-xs font-semibold text-white">
          {initials(name)}
        </div>
        <span className="min-w-0 flex-1 truncate text-sm font-semibold text-white">
          {name}
        </span>
        <ChevronDown className="h-4 w-4 shrink-0 text-navy-200" />
      </button>

      {/* Profile modal — portalled to body: the sidebar's translate creates a
          containing block that would otherwise trap a fixed-position overlay. */}
      {profileOpen &&
        mounted &&
        createPortal(
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
            onClick={() => setProfileOpen(false)}
          >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Profile"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-sm overflow-hidden rounded-xl bg-white shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-start gap-3 border-b border-gray-200 p-5">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-saffron-500 text-base font-semibold text-white">
                {initials(name)}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-base font-semibold text-navy-600">
                  {name}
                </p>
                {role && (
                  <span className="mt-1 inline-block rounded-full bg-navy-50 px-2 py-0.5 text-xs font-medium capitalize text-navy-600">
                    {role}
                  </span>
                )}
              </div>
              <button
                ref={closeRef}
                onClick={() => setProfileOpen(false)}
                aria-label="Close"
                className="rounded-lg p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Details */}
            <div className="space-y-4 p-5">
              {loading && !profile ? (
                <>
                  <div className="h-10 animate-pulse rounded bg-gray-100" />
                  <div className="h-10 animate-pulse rounded bg-gray-100" />
                  <div className="h-10 animate-pulse rounded bg-gray-100" />
                </>
              ) : error && !profile ? (
                <div className="text-sm">
                  <p className="text-red-600">{error}</p>
                  <button
                    onClick={loadProfile}
                    className="mt-2 rounded-lg bg-navy-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-navy-500"
                  >
                    Retry
                  </button>
                </div>
              ) : (
                <>
                  <Field label="Business" value={profile?.organization_name} />
                  <Field
                    label="Udyam Reg. No."
                    value={profile?.udyam_registration}
                    mono
                  />
                  <Field
                    label="Mobile (linked to Udyam)"
                    value={formatMobile(profile?.mobile_number)}
                    mono
                  />
                </>
              )}
            </div>
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string | null | undefined;
  mono?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p
        className={`mt-0.5 text-sm text-gray-900 ${mono ? "font-mono" : "font-medium"}`}
      >
        {value || "—"}
      </p>
    </div>
  );
}
