"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Mic,
  Bot,
  User,
  FileText,
  CheckCircle,
  Circle,
  ArrowRight,
  Loader2,
  Square,
  Volume2,
  VolumeX,
  Search,
} from "lucide-react";
import * as api from "@/lib/api";
import toast from "react-hot-toast";

// ─── Types ───
interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

interface ExtractedFields {
  [key: string]: string | undefined;
}

type Phase = "idle" | "user-speaking" | "processing" | "agent-speaking" | "finalizing";
type AssistantMode = "new-case" | "existing-case";

const FIELD_LABELS: Record<string, string> = {
  title: "Case Title",
  respondent_name: "Buyer Name",
  respondent_company: "Buyer Company",
  respondent_mobile: "Buyer Mobile",
  seller_mobile: "Your WhatsApp",
  goods_services_description: "Goods / Services",
  invoice_amount: "Invoice Amount",
};

const FIELD_ORDER = Object.keys(FIELD_LABELS);

// ─── VAD Constants ───
const SPEAKING_THRESHOLD = 0.03;
const SILENCE_DURATION = 1500;
const MAX_RECORDING_MS = 15000; // Auto-stop after 15 seconds to stay within STT limit
const NO_SPEECH_TIMEOUT_MS = 5000; // If user doesn't speak for 5 seconds, restart listening

// ─── Gradient Orb Component ───
function GradientOrb({ phase }: { phase: Phase }) {
  const colors: Record<Phase, { from: string; to: string; shadow: string }> = {
    idle: {
      from: "#f97316",
      to: "#fbbf24",
      shadow: "rgba(249,115,22,0.25)",
    },
    "user-speaking": {
      from: "#3b82f6",
      to: "#60a5fa",
      shadow: "rgba(59,130,246,0.35)",
    },
    processing: {
      from: "#f59e0b",
      to: "#f97316",
      shadow: "rgba(245,158,11,0.3)",
    },
    "agent-speaking": {
      from: "#f97316",
      to: "#ef4444",
      shadow: "rgba(249,115,22,0.35)",
    },
    finalizing: {
      from: "#10b981",
      to: "#34d399",
      shadow: "rgba(16,185,129,0.35)",
    },
  };

  const c = colors[phase];
  const isActive = phase !== "idle";

  return (
    <div className="relative flex items-center justify-center">
      {/* Outer glow rings */}
      {isActive && (
        <>
          <div
            className="absolute rounded-full animate-ping"
            style={{
              width: 280,
              height: 280,
              background: `radial-gradient(circle, ${c.shadow}, transparent 70%)`,
              animationDuration: "2s",
            }}
          />
          <div
            className="absolute rounded-full animate-pulse"
            style={{
              width: 260,
              height: 260,
              background: `radial-gradient(circle, ${c.shadow}, transparent 60%)`,
              animationDuration: "1.5s",
            }}
          />
        </>
      )}

      {/* Main orb */}
      <div
        className="relative rounded-full transition-all duration-700"
        style={{
          width: 220,
          height: 220,
          background: `radial-gradient(circle at 35% 35%, ${c.from}40, ${c.to}80, ${c.from}30)`,
          boxShadow: `0 0 80px ${c.shadow}, 0 0 120px ${c.shadow}`,
          transform: isActive ? "scale(1.05)" : "scale(1)",
        }}
      >
        {/* Inner highlight */}
        <div
          className="absolute rounded-full"
          style={{
            top: "15%",
            left: "20%",
            width: "40%",
            height: "40%",
            background: `radial-gradient(circle, rgba(255,255,255,0.3), transparent)`,
            filter: "blur(10px)",
          }}
        />
      </div>
    </div>
  );
}

// ─── Main Page ───
export default function FileCasePage() {
  const router = useRouter();
  const [active, setActive] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [sessionId, setSessionId] = useState<string>();
  const [fields, setFields] = useState<ExtractedFields>({});
  const [submitting, setSubmitting] = useState(false);
  const [showFields, setShowFields] = useState(false);
  const [muted, setMuted] = useState(false);
  const [conversationActive, setConversationActive] = useState(false);
  const [mode, setMode] = useState<AssistantMode>("new-case");
  const [selectedDisputeId, setSelectedDisputeId] = useState<string>("");
  const [disputes, setDisputes] = useState<api.Dispute[]>([]);
  const [loadingDisputes, setLoadingDisputes] = useState(false);

  // Audio refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxRecordTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const noSpeechTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasSpokenRef = useRef(false);
  const scriptNodeRef = useRef<ScriptProcessorNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const responseAudioRef = useRef<HTMLAudioElement | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const isRecordingRef = useRef(false);
  const conversationActiveRef = useRef(false); // Controls the auto-listen loop
  const startRecordingRef = useRef<(() => Promise<void>) | null>(null);
  const stoppingRef = useRef(false); // Prevents recorder.onstop from re-triggering pipeline
  const pendingAssistantMsgRef = useRef<string | null>(null); // Show text only when TTS starts
  const messagesRef = useRef<Message[]>([]); // Keep messages accessible in closures
  const awaitingTTSRef = useRef(false); // When true, playTTS is awaiting audio completion — skip auto-record

  useEffect(() => {
    messagesRef.current = messages;
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    setLoadingDisputes(true);
    api.listDisputes()
      .then(setDisputes)
      .catch(() => {})
      .finally(() => setLoadingDisputes(false));
  }, []);

  // Audio element for TTS playback — auto-restart recording when TTS ends
  useEffect(() => {
    responseAudioRef.current = new Audio();
    responseAudioRef.current.onended = () => {
      // If playTTS is awaiting completion (e.g. for FILING_COMPLETE), let it handle next steps
      if (awaitingTTSRef.current) return;
      if (conversationActiveRef.current && !stoppingRef.current) {
        // Auto-start listening again after agent finishes speaking
        startRecordingRef.current?.();
      } else {
        setPhase("idle");
      }
    };
    responseAudioRef.current.onerror = () => {
      if (awaitingTTSRef.current) return;
      if (conversationActiveRef.current && !stoppingRef.current) {
        startRecordingRef.current?.();
      } else {
        setPhase("idle");
      }
    };
    return () => {
      responseAudioRef.current?.pause();
      streamRef.current?.getTracks().forEach((t) => t.stop());
      audioContextRef.current?.close();
    };
  }, []);

  // ─── Sarvam APIs ───
  const sendSTT = async (audioBlob: Blob): Promise<string> => {
    const form = new FormData();
    form.append("file", audioBlob, "input.wav");
    const res = await fetch("/api/v1/voice/stt", { method: "POST", body: form });
    if (!res.ok) throw new Error("STT failed");
    return (await res.json()).transcript || "";
  };

  const sendLID = async (text: string): Promise<string> => {
    const form = new FormData();
    form.append("text", text);
    const res = await fetch("/api/v1/voice/lid", { method: "POST", body: form });
    return (await res.json()).language_code || "hi-IN";
  };

  /**
   * Play TTS audio. Two modes:
   * - awaitCompletion=false (default): fire-and-forget, onended in useEffect handles next step
   * - awaitCompletion=true: returns a promise that resolves when audio finishes
   */
  const playTTS = async (text: string, langCode: string, awaitCompletion = false) => {
    if (!conversationActiveRef.current || muted || !text) {
      // Show text immediately when muted or no text
      if (pendingAssistantMsgRef.current) {
        const msg = pendingAssistantMsgRef.current;
        pendingAssistantMsgRef.current = null;
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: msg, timestamp: Date.now() },
        ]);
      }
      if (conversationActiveRef.current && (muted || !text)) {
        startRecordingRef.current?.();
      } else {
        setPhase("idle");
      }
      return;
    }
    const form = new FormData();
    form.append("text", text);
    form.append("lang_code", langCode);
    const res = await fetch("/api/v1/voice/tts", { method: "POST", body: form });
    if (!res.ok) {
      setPhase("idle");
      return;
    }
    const data = await res.json();
    if (data.audio_id && responseAudioRef.current) {
      setPhase("agent-speaking");
      // Show the text bubble when audio starts playing
      const flushPendingMsg = () => {
        if (pendingAssistantMsgRef.current) {
          const msg = pendingAssistantMsgRef.current;
          pendingAssistantMsgRef.current = null;
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: msg, timestamp: Date.now() },
          ]);
        }
        responseAudioRef.current?.removeEventListener("playing", flushPendingMsg);
      };
      responseAudioRef.current.addEventListener("playing", flushPendingMsg);
      responseAudioRef.current.src = `/api/v1/voice/audio/${data.audio_id}`;

      if (awaitCompletion) {
        // Block until audio finishes — used by processPipeline for FILING_COMPLETE
        awaitingTTSRef.current = true;
        await new Promise<void>((resolve) => {
          let resolved = false;
          const doResolve = () => {
            if (resolved) return;
            resolved = true;
            audio.removeEventListener("ended", doResolve);
            audio.removeEventListener("error", doResolve);
            audio.removeEventListener("pause", onPause);
            awaitingTTSRef.current = false;
            resolve();
          };
          const onPause = () => {
            if (stoppingRef.current) doResolve();
          };
          const audio = responseAudioRef.current!;
          audio.addEventListener("ended", doResolve);
          audio.addEventListener("error", doResolve);
          audio.addEventListener("pause", onPause);
          setTimeout(doResolve, 30000); // Safety timeout
          audio.play().catch(() => {
            flushPendingMsg();
            setPhase("idle");
            doResolve();
          });
        });
      } else {
        // Fire-and-forget — useEffect onended handles recording restart
        responseAudioRef.current.play().catch(() => {
          flushPendingMsg();
          setPhase("idle");
        });
      }
    } else {
      // No audio — show text immediately
      if (pendingAssistantMsgRef.current) {
        const msg = pendingAssistantMsgRef.current;
        pendingAssistantMsgRef.current = null;
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: msg, timestamp: Date.now() },
        ]);
      }
      setPhase("idle");
    }
  };

  // ─── Pipeline: STT → LLM → TTS ───
  const processPipeline = useCallback(
    async (audioBlob: Blob) => {
      setPhase("processing");
      try {
        // Bail out if conversation was stopped while we were processing
        if (!conversationActiveRef.current) {
          setPhase("idle");
          return;
        }

        const transcript = await sendSTT(audioBlob);

        if (!conversationActiveRef.current) {
          setPhase("idle");
          return;
        }

        if (!transcript) {
          // Auto-restart listening if conversation is active
          if (conversationActiveRef.current) {
            startRecordingRef.current?.();
          } else {
            setPhase("idle");
          }
          return;
        }

        setMessages((prev) => [
          ...prev,
          { role: "user", content: transcript, timestamp: Date.now() },
        ]);

        const langCode = await sendLID(transcript);

        if (!conversationActiveRef.current) {
          setPhase("idle");
          return;
        }

        const disputeId = mode === "existing-case" ? selectedDisputeId : undefined;
        const res = await api.sendMessage(transcript, sessionId, disputeId || undefined, "voice");

        if (!conversationActiveRef.current) {
          setPhase("idle");
          return;
        }

        setSessionId(res.session_id);

        const rawResponse = res.response;

        // Extract [FIELDS]{...}[/FIELDS] block
        let latestFields: Record<string, string> = {};
        const fieldsMatch = rawResponse.match(/\[FIELDS\]([\s\S]*?)\[\/FIELDS\]/);
        if (fieldsMatch) {
          try {
            const parsed = JSON.parse(fieldsMatch[1]);
            const updates: ExtractedFields = {};
            for (const [k, v] of Object.entries(parsed)) {
              if (v && k in FIELD_LABELS) updates[k] = String(v);
            }
            if (Object.keys(updates).length > 0) {
              setFields((prev) => {
                const merged = { ...prev, ...updates };
                // Build clean Record<string, string> (filter out undefined)
                latestFields = Object.fromEntries(
                  Object.entries(merged).filter(([, v]) => v !== undefined)
                ) as Record<string, string>;
                return merged;
              });
            }
          } catch {
            // JSON parse failed, ignore
          }
        }

        // Check for [FILING_COMPLETE]
        const isComplete = rawResponse.includes("[FILING_COMPLETE]");

        // Clean response for display and TTS (remove tags)
        const cleanResponse = rawResponse
          .replace(/\[FIELDS\][\s\S]*?\[\/FIELDS\]/, "")
          .replace(/\[FILING_COMPLETE\]/g, "")
          .trim();

        // Store as pending — text will appear when TTS starts playing
        pendingAssistantMsgRef.current = cleanResponse;

        if (isComplete && mode === "new-case") {
          // Filing complete — await TTS so user hears the full final message
          await playTTS(cleanResponse, langCode, true);

          // TTS done — stop conversation, show loader, extract fields via LLM, redirect
          conversationActiveRef.current = false;
          setConversationActive(false);
          setPhase("finalizing");

          // Build transcript from messages (include the latest response too)
          const transcript = [...messagesRef.current, { role: "assistant", content: cleanResponse }]
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((m) => ({ role: m.role, content: m.content }));

          const handoffFields = Object.keys(latestFields).length > 0 ? latestFields : fields;
          try {
            const result = await api.handoffToWhatsApp(
              handoffFields as Record<string, string>,
              sessionId,
              transcript
            );
            toast.success("Case saved! Redirecting...");
            router.push(`/disputes/${result.dispute_id}`);
          } catch {
            toast.error("Could not save case. Please try again.");
            setPhase("idle");
          }
        } else {
          // Normal flow — fire-and-forget TTS; useEffect onended will restart recording
          await playTTS(cleanResponse, langCode);
        }
      } catch {
        const errMsg = "Sorry, kuch error aa gaya. Please try again.";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: errMsg, timestamp: Date.now() },
        ]);
        // Auto-restart listening
        if (conversationActiveRef.current) {
          setTimeout(() => startRecordingRef.current?.(), 1000);
        } else {
          setPhase("idle");
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sessionId, muted, mode, selectedDisputeId]
  );

  // ─── Recording with VAD ───
  const startRecording = useCallback(async () => {
    if (responseAudioRef.current && !responseAudioRef.current.paused) {
      responseAudioRef.current.pause();
      responseAudioRef.current.currentTime = 0;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const ctx = new AudioContext();
      audioContextRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.7;
      source.connect(analyser);
      analyserRef.current = analyser;

      // VAD
      const scriptNode = ctx.createScriptProcessor(2048, 1, 1);
      analyser.connect(scriptNode);
      scriptNodeRef.current = scriptNode;
      hasSpokenRef.current = false;

      scriptNode.onaudioprocess = () => {
        if (!isRecordingRef.current) return;
        const vadData = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(vadData);
        let sum = 0;
        for (let i = 0; i < vadData.length; i++) {
          const n = vadData[i] / 128.0 - 1.0;
          sum += n * n;
        }
        const rms = Math.sqrt(sum / vadData.length);

        if (rms > SPEAKING_THRESHOLD) {
          hasSpokenRef.current = true;
          // User started speaking — cancel no-speech timeout
          if (noSpeechTimerRef.current) {
            clearTimeout(noSpeechTimerRef.current);
            noSpeechTimerRef.current = null;
          }
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
          }
        } else if (hasSpokenRef.current && !silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => {
            stopRecording();
          }, SILENCE_DURATION);
        }
      };
      scriptNode.connect(ctx.destination);

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        audioChunksRef.current = [];
        cleanupRecording();
        // Don't trigger pipeline if user clicked Stop
        if (stoppingRef.current || !conversationActiveRef.current) {
          stoppingRef.current = false;
          setPhase("idle");
          return;
        }
        if (blob.size > 0) {
          processPipeline(blob);
        } else {
          setPhase("idle");
        }
      };

      recorder.start();
      isRecordingRef.current = true;
      setPhase("user-speaking");

      // Safety: auto-stop after MAX_RECORDING_MS to stay within STT 30s limit
      maxRecordTimerRef.current = setTimeout(() => {
        if (isRecordingRef.current) {
          stopRecording();
        }
      }, MAX_RECORDING_MS);

      // No-speech timeout: if user doesn't speak within 5s, nudge and repeat last question
      noSpeechTimerRef.current = setTimeout(async () => {
        if (isRecordingRef.current && !hasSpokenRef.current) {
          // User hasn't spoken — stop recording silently
          stoppingRef.current = true;
          if (mediaRecorderRef.current?.state === "recording") {
            try { mediaRecorderRef.current.stop(); } catch { /* ignore */ }
          }
          isRecordingRef.current = false;
          cleanupRecording();
          stoppingRef.current = false;

          if (!conversationActiveRef.current) {
            setPhase("idle");
            return;
          }

          // Find the last assistant message to repeat
          const lastAssistantMsg = [...messagesRef.current].reverse().find((m) => m.role === "assistant");
          const nudge = lastAssistantMsg
            ? `Ji, mujhe kuch input nahi mila. ${lastAssistantMsg.content}`
            : "Ji, mujhe kuch sunai nahi diya. Kya aap dobara bol sakte hain?";

          // Show nudge + speak it, then auto-restart listening
          pendingAssistantMsgRef.current = nudge;
          await playTTS(nudge, "hi-IN");
        }
      }, NO_SPEECH_TIMEOUT_MS);
    } catch {
      toast.error("Microphone access denied");
      setPhase("idle");
    }
  }, [processPipeline]);

  // Keep ref in sync so onended callback can call it
  useEffect(() => {
    startRecordingRef.current = startRecording;
  }, [startRecording]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    isRecordingRef.current = false;
  }, []);

  const stopConversation = useCallback(async () => {
    // Set flags FIRST so in-flight pipeline checks and recorder.onstop bail out
    stoppingRef.current = true;
    conversationActiveRef.current = false;
    setConversationActive(false);
    isRecordingRef.current = false;

    // Stop media recorder
    if (mediaRecorderRef.current?.state === "recording") {
      try { mediaRecorderRef.current.stop(); } catch { /* ignore */ }
    }
    mediaRecorderRef.current = null;

    // Stop audio playback
    if (responseAudioRef.current) {
      responseAudioRef.current.pause();
      responseAudioRef.current.currentTime = 0;
      responseAudioRef.current.src = "";
    }

    cleanupRecording();
    setPhase("idle");

    // Flush any pending assistant message so it's not lost
    if (pendingAssistantMsgRef.current) {
      const msg = pendingAssistantMsgRef.current;
      pendingAssistantMsgRef.current = null;
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: msg, timestamp: Date.now() },
      ]);
    }

    // Reset stopping flag after a tick (in case recorder.onstop fires async)
    setTimeout(() => { stoppingRef.current = false; }, 100);

    // Auto-handoff partial data (new-case only)
    if (mode === "new-case") {
      const hasAnyField = Object.values(fields).some((v) => !!v);
      if (hasAnyField) {
        setPhase("finalizing");
        // Build transcript from current messages
        const transcript = messagesRef.current
          .filter((m) => m.role === "user" || m.role === "assistant")
          .map((m) => ({ role: m.role, content: m.content }));

        const handoffFields = fields.seller_mobile
          ? (fields as Record<string, string>)
          : { ...fields, seller_mobile: "pending" } as Record<string, string>;

        try {
          const result = await api.handoffToWhatsApp(
            handoffFields,
            sessionId,
            transcript
          );
          toast.success(
            fields.seller_mobile
              ? "Details saved! Check WhatsApp for remaining questions."
              : "Partial details saved. Please call again to complete filing."
          );
          router.push(`/disputes/${result.dispute_id}`);
        } catch {
          toast.error("Could not save details. Please try again.");
          setPhase("idle");
        }
      }
    }
  }, [fields, sessionId, mode, router]);

  const cleanupRecording = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (maxRecordTimerRef.current) {
      clearTimeout(maxRecordTimerRef.current);
      maxRecordTimerRef.current = null;
    }
    if (noSpeechTimerRef.current) {
      clearTimeout(noSpeechTimerRef.current);
      noSpeechTimerRef.current = null;
    }
    if (scriptNodeRef.current) {
      scriptNodeRef.current.onaudioprocess = null;
      scriptNodeRef.current.disconnect();
      scriptNodeRef.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (audioContextRef.current?.state !== "closed") {
      audioContextRef.current?.close();
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    hasSpokenRef.current = false;
  };

  const toggleMic = useCallback(() => {
    if (conversationActiveRef.current) {
      // Conversation is running — stop it
      stopConversation();
    } else {
      // Start continuous conversation loop
      conversationActiveRef.current = true;
      setConversationActive(true);
      startRecording();
    }
  }, [stopConversation, startRecording]);

  const startSession = async () => {
    setActive(true);
    conversationActiveRef.current = true;
    setConversationActive(true);

    const greeting =
      mode === "existing-case" && selectedDisputeId
        ? "Namaskar! Main aapki purane claim ki jankari mein kya sahayata kar sakta hun."
        : "Namaskar! MSME ODR Mitra mein aapka swagat hai. Bataiye, main aapki kis prakar se madad kar sakta hoon?";

    setMessages([
      { role: "assistant", content: greeting, timestamp: Date.now() },
    ]);
    // Play greeting — when it ends, onended will auto-start recording
    setTimeout(() => playTTS(greeting, "hi-IN"), 300);
  };

  const handleSubmit = async () => {
    if (!fields.seller_mobile) {
      toast.error("Please provide at least your WhatsApp number");
      return;
    }
    stopRecording();
    responseAudioRef.current?.pause();
    setSubmitting(true);
    try {
      const result = await api.handoffToWhatsApp(
        fields as Record<string, string>,
        sessionId
      );
      toast.success("Case filed! Check WhatsApp for next steps.");
      router.push(`/disputes/${result.dispute_id}`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to file case");
    } finally {
      setSubmitting(false);
    }
  };

  const filledCount = FIELD_ORDER.filter((k) => fields[k]).length;

  const phaseLabel: Record<Phase, string> = {
    idle: conversationActive ? "Ready..." : "Click to start",
    "user-speaking": "Listening...",
    processing: "Processing...",
    "agent-speaking": "Speaking...",
    finalizing: "Saving your case...",
  };

  const canStart =
    mode === "new-case" || (mode === "existing-case" && !!selectedDisputeId);

  // ─── INITIAL STATE — Sarvam-style ───
  if (!active) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ minHeight: "calc(100vh - 140px)" }}
      >
        <div className="flex w-full max-w-4xl gap-12">
          {/* Left: Description + Mode Selector */}
          <div className="flex-1 pt-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              AI Case Filing Assistant
            </h1>
            <div className="space-y-3 text-sm text-gray-600 leading-relaxed">
              <p>
                You are speaking with <strong>ODRMitra</strong>, an AI assistant
                for filing MSME delayed payment disputes.
              </p>
              {mode === "new-case" ? (
                <>
                  <p>
                    ODRMitra will ask you <strong>6 quick questions</strong> — your name,
                    buyer name, buyer mobile, your WhatsApp number, what you supplied, and the invoice
                    amount. Then our WhatsApp agent will collect remaining details.
                  </p>
                  <p>
                    Keep responses short. The assistant asks one question at a time.
                  </p>
                </>
              ) : (
                <p>
                  Select one of your existing cases below. ODRMitra will answer
                  your questions about the case status, legal provisions, and
                  next steps.
                </p>
              )}
              <p className="text-gray-400 text-xs mt-6">
                Language: Hindi / English / Hinglish
              </p>
            </div>

            {/* Mode Selector Cards */}
            <div className="mt-6 grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                  setMode("new-case");
                  setSelectedDisputeId("");
                }}
                className={`flex items-center gap-3 rounded-xl border-2 px-4 py-3.5 text-left transition-all duration-200 ${
                  mode === "new-case"
                    ? "border-saffron-500 bg-saffron-50 shadow-sm"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
              >
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                    mode === "new-case"
                      ? "bg-saffron-500 text-white"
                      : "bg-gray-100 text-gray-400"
                  }`}
                >
                  <FileText className="h-4 w-4" />
                </div>
                <div>
                  <p
                    className={`text-sm font-semibold ${
                      mode === "new-case" ? "text-gray-900" : "text-gray-600"
                    }`}
                  >
                    File New Case
                  </p>
                  <p className="text-xs text-gray-400">Start a new dispute</p>
                </div>
              </button>

              <button
                onClick={() => setMode("existing-case")}
                className={`flex items-center gap-3 rounded-xl border-2 px-4 py-3.5 text-left transition-all duration-200 ${
                  mode === "existing-case"
                    ? "border-saffron-500 bg-saffron-50 shadow-sm"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
              >
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                    mode === "existing-case"
                      ? "bg-saffron-500 text-white"
                      : "bg-gray-100 text-gray-400"
                  }`}
                >
                  <Search className="h-4 w-4" />
                </div>
                <div>
                  <p
                    className={`text-sm font-semibold ${
                      mode === "existing-case" ? "text-gray-900" : "text-gray-600"
                    }`}
                  >
                    Check Existing Case
                  </p>
                  <p className="text-xs text-gray-400">Inquire about a case</p>
                </div>
              </button>
            </div>

            {/* Dispute Dropdown (existing-case mode) */}
            {mode === "existing-case" && (
              <div className="mt-4">
                <label className="block text-xs font-medium text-gray-500 mb-1.5">
                  Select your case
                </label>
                <select
                  value={selectedDisputeId}
                  onChange={(e) => setSelectedDisputeId(e.target.value)}
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-gray-700 shadow-sm focus:border-saffron-400 focus:outline-none focus:ring-1 focus:ring-saffron-400"
                >
                  <option value="">
                    {loadingDisputes ? "Loading cases..." : "— Select a case —"}
                  </option>
                  {disputes.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title} — {d.case_number} — {d.status}
                    </option>
                  ))}
                </select>
                {!loadingDisputes && disputes.length === 0 && (
                  <p className="mt-1.5 text-xs text-gray-400">
                    No existing cases found. File a new case first.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Right: Orb + Start Button */}
          <div className="flex flex-col items-center justify-center gap-8">
            <GradientOrb phase="idle" />
            <button
              onClick={startSession}
              disabled={!canStart}
              className="flex items-center gap-2.5 rounded-full bg-gray-900 px-8 py-3.5 text-sm font-semibold text-white shadow-lg hover:bg-gray-800 hover:shadow-xl transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-lg"
            >
              <Mic className="h-4 w-4" />
              Start Speaking
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─── ACTIVE STATE ───
  return (
    <div className="flex h-[calc(100vh-140px)] gap-0">
      {/* ─── LEFT: Orb + Conversation ─── */}
      <div className="flex flex-1 flex-col">
        {/* Orb section */}
        <div className="flex flex-col items-center justify-center py-6 relative">
          <GradientOrb phase={phase} />

          {/* Phase label */}
          <div className="mt-6 flex items-center gap-2">
            {phase === "user-speaking" && (
              <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
            )}
            {phase === "processing" && (
              <Loader2 className="h-4 w-4 animate-spin text-amber-500" />
            )}
            {phase === "agent-speaking" && (
              <Volume2 className="h-4 w-4 text-saffron-500" />
            )}
            {phase === "idle" && (
              <div className="h-2 w-2 rounded-full bg-green-500" />
            )}
            <span
              className={`text-sm font-medium ${
                phase === "user-speaking"
                  ? "text-blue-600"
                  : phase === "processing"
                  ? "text-amber-600"
                  : phase === "agent-speaking"
                  ? "text-saffron-600"
                  : "text-gray-500"
              }`}
            >
              {phaseLabel[phase]}
            </span>
          </div>

          {/* Mic / Stop button */}
          <button
            onClick={toggleMic}
            className={`mt-4 flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold transition-all duration-300 ${
              conversationActive
                ? "bg-red-600 text-white shadow-lg shadow-red-500/30 hover:bg-red-700"
                : "bg-gray-900 text-white hover:bg-gray-800 shadow-lg hover:shadow-xl"
            }`}
          >
            {conversationActive ? (
              <>
                <Square className="h-4 w-4" fill="white" />
                Stop Conversation
              </>
            ) : (
              <>
                <Mic className="h-4 w-4" />
                Start Speaking
              </>
            )}
          </button>

          {/* Mute toggle */}
          <button
            onClick={() => {
              setMuted((m) => !m);
              if (!muted && responseAudioRef.current) {
                responseAudioRef.current.pause();
                setPhase("idle");
              }
            }}
            className="absolute top-4 right-4 flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 transition-colors"
            title={muted ? "Unmute" : "Mute"}
          >
            {muted ? (
              <VolumeX className="h-3.5 w-3.5" />
            ) : (
              <Volume2 className="h-3.5 w-3.5" />
            )}
          </button>
        </div>

        {/* Conversation transcript */}
        <div className="flex-1 overflow-y-auto border-t border-gray-100 px-6 py-4">
          <div className="max-w-lg mx-auto space-y-3">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-2.5 ${
                  msg.role === "user" ? "flex-row-reverse" : ""
                }`}
                style={{ animation: "fadeSlideUp 0.3s ease-out" }}
              >
                <div
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-saffron-100 text-saffron-700"
                  }`}
                >
                  {msg.role === "user" ? (
                    <User className="h-3.5 w-3.5" />
                  ) : (
                    <Bot className="h-3.5 w-3.5" />
                  )}
                </div>
                <div
                  className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-50 text-gray-800 border border-gray-100"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}

            {phase === "processing" && (
              <div className="flex gap-2.5" style={{ animation: "fadeSlideUp 0.3s ease-out" }}>
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-amber-100 text-amber-700">
                  <Bot className="h-3.5 w-3.5" />
                </div>
                <div className="rounded-2xl bg-amber-50 border border-amber-100 px-3.5 py-2.5">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-500" />
                    <span className="text-xs text-amber-600">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={transcriptEndRef} />
          </div>
        </div>
      </div>

      {/* ─── RIGHT: Case Fields Panel (new-case only) ─── */}
      {mode === "new-case" && (
      <div className="w-80 shrink-0 border-l border-gray-100 bg-gray-50/50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Case Fields</h3>
            <p className="text-xs text-gray-400 mt-0.5">
              {filledCount}/{FIELD_ORDER.length} collected
            </p>
          </div>
          <button
            onClick={() => setShowFields((s) => !s)}
            className="text-xs text-navy-600 hover:text-navy-700 font-medium"
          >
            {showFields ? "Collapse" : "Expand"}
          </button>
        </div>

        {/* Progress bar */}
        <div className="px-5 py-3">
          <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
            <div
              className="h-1.5 rounded-full bg-gradient-to-r from-saffron-400 to-saffron-500 transition-all duration-700"
              style={{
                width: `${(filledCount / FIELD_ORDER.length) * 100}%`,
              }}
            />
          </div>
        </div>

        {/* Fields list */}
        <div className="flex-1 overflow-y-auto px-5 pb-4 space-y-1.5">
          {FIELD_ORDER.map((key) => {
            const value = fields[key];
            const filled = !!value;
            return (
              <div
                key={key}
                className={`rounded-lg px-3 py-2.5 transition-all duration-500 ${
                  filled
                    ? "bg-green-50 border border-green-200"
                    : "bg-white border border-gray-100"
                }`}
                style={
                  filled
                    ? { animation: "fadeSlideUp 0.4s ease-out" }
                    : undefined
                }
              >
                <div className="flex items-center gap-2">
                  {filled ? (
                    <CheckCircle className="h-3.5 w-3.5 text-green-500 shrink-0" />
                  ) : (
                    <Circle className="h-3.5 w-3.5 text-gray-300 shrink-0" />
                  )}
                  <span className="text-xs font-medium text-gray-500">
                    {FIELD_LABELS[key]}
                  </span>
                </div>
                {filled && showFields && (
                  <p className="text-sm font-medium text-gray-900 truncate pl-[22px] mt-0.5">
                    {value}
                  </p>
                )}
              </div>
            );
          })}
        </div>

        {/* Submit */}
        <div className="border-t border-gray-100 p-4">
          <button
            onClick={handleSubmit}
            disabled={submitting || filledCount < 2}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-saffron-500 to-saffron-600 py-3 text-sm font-semibold text-white shadow-lg shadow-saffron-500/20 transition-all hover:shadow-saffron-500/40 disabled:opacity-40 disabled:shadow-none"
          >
            {submitting ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                <FileText className="h-4 w-4" />
                Submit Case
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </div>
      )}

      <style jsx global>{`
        @keyframes fadeSlideUp {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
