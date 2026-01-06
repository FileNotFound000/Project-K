"use client";

import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Mic, Send, StopCircle, Paperclip, X, Image as ImageIcon, Menu, Volume2, Loader2, FileText, Globe, Plus } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useVoiceInput } from "@/hooks/useVoiceInput";
import Sidebar from "@/components/Sidebar";
import KOrb from '@/components/KOrb';
import SettingsModal from "@/components/SettingsModal";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Session {
  id: string;
  title: string;
  created_at: string;
}

function stripJSON(text: string) {
  let result = "";
  let i = 0;
  while (i < text.length) {
    // Check for start of JSON block
    if (text.substring(i).startsWith('{"tool":') || text.substring(i).startsWith('{"result":')) {
      let depth = 0;
      // Consume until balanced
      while (i < text.length) {
        if (text[i] === '{') depth++;
        if (text[i] === '}') depth--;
        i++;
        if (depth === 0) break;
      }
    } else {
      result += text[i];
      i++;
    }
  }
  return result.trim();
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isResearchMode, setIsResearchMode] = useState(false);
  const [isToolsMenuOpen, setIsToolsMenuOpen] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const docInputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const { isListening, transcript, startListening, stopListening, resetTranscript, hasRecognition, isWakeWordEnabled, toggleWakeWord, isWakeWordListening } = useVoiceInput();

  // Initialize session on load
  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const res = await axios.get("http://localhost:8000/sessions");
      setSessions(res.data);
      if (res.data.length > 0 && !currentSessionId) {
        selectSession(res.data[0].id);
      } else if (res.data.length === 0) {
        createNewChat();
      }
    } catch (e) {
      console.error("Error fetching sessions:", e);
    }
  };

  // Update input text with voice transcript
  useEffect(() => {
    if (transcript) {
      console.log("Updating Input with:", transcript);
      setInputText(transcript);
    }
  }, [transcript]);

  const selectSession = async (sessionId: string) => {
    setCurrentSessionId(sessionId);
    try {
      const res = await axios.get(`http://localhost:8000/sessions/${sessionId}`);
      // Map backend messages to frontend format
      const mappedMessages = res.data.messages.map((m: any) => ({
        role: m.role === "model" ? "assistant" : m.role,
        content: m.content
      }));
      setMessages(mappedMessages);
    } catch (e) {
      console.error("Error loading session:", e);
    }
  };

  const createNewChat = async () => {
    try {
      const formData = new FormData();
      formData.append("title", "New Chat");

      const res = await axios.post("http://localhost:8000/sessions", formData);
      const newSession = { id: res.data.id, title: res.data.title, created_at: new Date().toISOString() };

      setSessions(prev => [newSession, ...prev]);
      setCurrentSessionId(res.data.id);
      setMessages([]);
    } catch (e) {
      console.error("Error creating session:", e);
    }
  };

  const handleRenameSession = async (sessionId: string, newTitle: string) => {
    try {
      // Optimistic update
      setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title: newTitle } : s));

      const formData = new FormData();
      formData.append("title", newTitle);
      await axios.put(`http://localhost:8000/sessions/${sessionId}`, formData);
    } catch (error) {
      console.error("Error renaming session:", error);
      fetchSessions(); // Revert
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      // Optimistic update
      setSessions(prev => prev.filter(s => s.id !== sessionId));

      await axios.delete(`http://localhost:8000/sessions/${sessionId}`);

      if (currentSessionId === sessionId) {
        // If we deleted the current session, switch to the first available or create new
        const remaining = sessions.filter(s => s.id !== sessionId);
        if (remaining.length > 0) {
          selectSession(remaining[0].id);
        } else {
          createNewChat();
        }
      }
    } catch (error) {
      console.error("Error deleting session:", error);
      fetchSessions(); // Revert
    }
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImage(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      await axios.post("http://localhost:8000/upload", formData);

      // Show success message (could be a toast, but for now just appending a system message)
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `I've read "${file.name}". You can now ask me questions about it.`
      }]);
    } catch (error) {
      console.error("Upload error:", error);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: `Failed to upload "${file.name}".`
      }]);
    } finally {
      setIsUploading(false);
      if (docInputRef.current) docInputRef.current.value = "";
    }
  };

  const [playingMessageIndex, setPlayingMessageIndex] = useState<number | null>(null);
  const [loadingMessageIndex, setLoadingMessageIndex] = useState<number | null>(null);

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current.oncanplaythrough = null;
      audioRef.current.onended = null;
    }
    setIsPlaying(false);
    setPlayingMessageIndex(null);
    setLoadingMessageIndex(null);
  };

  const playMessageAudio = async (text: string, index: number) => {
    console.log(`Clicked message ${index}. Current playing: ${playingMessageIndex}, isPlaying: ${isPlaying}`);

    // If clicking the same message that is playing, stop it
    if (isPlaying && playingMessageIndex === index) {
      console.log("Condition met: Stopping audio...");
      stopAudio();
      return;
    } else {
      console.log("Condition failed. Starting new audio...");
    }

    console.log("Attempting to play audio for:", text.substring(0, 20) + "...");
    setLoadingMessageIndex(index);

    try {
      const formData = new FormData();
      formData.append("text", text);
      const res = await axios.post("http://localhost:8000/tts", formData);
      console.log("TTS Response:", res.data);
      if (res.data.audio_url) {
        if (audioRef.current) {
          const audioSrc = `http://localhost:8000${res.data.audio_url}`;
          console.log("Playing audio from:", audioSrc);
          audioRef.current.src = audioSrc;

          // Wait for audio to be ready to play
          audioRef.current.oncanplaythrough = () => {
            setLoadingMessageIndex(null);
            audioRef.current?.play().catch(e => console.error("Audio play failed:", e));
            setIsPlaying(true);
            setPlayingMessageIndex(index);
          };

          audioRef.current.load(); // Trigger load

          audioRef.current.onended = () => {
            setIsPlaying(false);
            setPlayingMessageIndex(null);
          };
        } else {
          console.error("Audio ref is null");
          setLoadingMessageIndex(null);
        }
      }
    } catch (e) {
      console.error("TTS Error:", e);
      setIsPlaying(false);
      setPlayingMessageIndex(null);
      setLoadingMessageIndex(null);
    }
  };

  const sendMessage = async () => {
    if (!inputText.trim() && !selectedImage) return;

    let finalMessage = inputText;
    if (isResearchMode) {
      if (!finalMessage.toLowerCase().trim().startsWith("research")) {
        finalMessage = `Research ${finalMessage}`;
      }
    }

    const userMessage: Message = { role: "user", content: finalMessage };
    if (selectedImage && previewUrl) {
      // For display purposes, we could add the image to the message content or a separate field
      // userMessage.image = previewUrl; 
    }

    setMessages((prev) => [...prev, userMessage]);
    setInputText("");
    setSelectedImage(null);
    setPreviewUrl(null);
    setIsProcessing(true);
    resetTranscript();

    // Create a placeholder for the assistant response
    const assistantMessageId = Date.now().toString();
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const formData = new FormData();
      formData.append("message", userMessage.content);
      formData.append("session_id", currentSessionId || "");
      if (selectedImage) {
        formData.append("file", selectedImage);
      }

      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        body: formData,
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            if (!dataStr) continue;

            try {
              const data = JSON.parse(dataStr);
              if (data.text) {
                assistantContent += data.text;
                setMessages((prev) => {
                  const newMessages = [...prev];
                  const lastMsg = newMessages[newMessages.length - 1];
                  if (lastMsg.role === "assistant") {
                    lastMsg.content = assistantContent;
                  }
                  return newMessages;
                });
              }
            } catch (e) {
              console.error("Error parsing SSE data:", e);
            }
          } else if (line.startsWith("event: command")) {
            // Handle command event if needed (e.g. show a notification)
            // The command logic is already executed on backend, but we might want to show a toast?
          }
        }
      }

      // Generate audio after streaming is done (optional, or we can stream audio too later)
      // For now, TTS is disabled in streaming mode to avoid lag, or we need a separate endpoint for TTS.

    } catch (error) {
      console.error("Error sending message:", error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong." },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const playAudio = (url: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    const audio = new Audio(url);
    audioRef.current = audio;
    setIsPlaying(true);
    audio.play();
    audio.onended = () => setIsPlaying(false);
  };



  return (
    <main className="flex h-screen w-full bg-transparent text-foreground overflow-hidden relative">
      {/* Background Elements */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-900/10 rounded-full blur-[128px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-900/10 rounded-full blur-[128px]" />
      </div>

      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSessionSelect={selectSession}
        onNewChat={createNewChat}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full min-w-0 relative z-10">
        {/* Header */}
        <div className="flex-none w-full p-4 md:p-6 flex items-center justify-between gap-4 border-b border-white/5 bg-black/20 backdrop-blur-sm">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="md:hidden p-2 text-violet-300 hover:bg-white/5 rounded-lg"
            >
              <Menu size={24} />
            </button>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-blue-400 drop-shadow-[0_0_10px_rgba(139,92,246,0.3)]">
                K
              </h1>
              <p className="hidden md:block text-xs text-violet-400/60 font-mono tracking-widest mt-1">
                ADVANCED VIRTUAL ASSISTANT
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Wake Word Status */}
            <button
              onClick={toggleWakeWord}
              className={`hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all ${isWakeWordEnabled
                ? "bg-violet-500/20 border-violet-500/30 text-violet-200"
                : "bg-white/5 border-white/10 text-neutral-400 hover:text-neutral-300"
                }`}
              title={isWakeWordEnabled ? "Wake Word Active (Say 'Hey K')" : "Enable Wake Word"}
            >
              <div className={`w-2 h-2 rounded-full ${isWakeWordEnabled ? (isWakeWordListening ? "bg-violet-400 animate-pulse" : "bg-violet-400") : "bg-neutral-600"}`} />
              <span className="text-xs font-mono">{isWakeWordEnabled ? (isWakeWordListening ? "LISTENING..." : "ON STANDBY") : "VOICE OFF"}</span>
            </button>

            <div className="flex items-center gap-3 px-3 py-1.5 md:px-4 md:py-2 rounded-full bg-white/5 border border-white/10 backdrop-blur-md">
              <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_10px_#22c55e] animate-pulse" />
              <span className="font-mono text-[10px] md:text-xs text-violet-200 tracking-wider">
                STATUS: <span className="text-green-400 font-bold">ONLINE</span>
              </span>
            </div>
          </div>
        </div>
        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-violet-600/20 scrollbar-track-transparent">
          <div className="max-w-4xl mx-auto flex flex-col gap-4 pb-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-[50vh] text-violet-300/30">
                <p className="font-light tracking-widest text-lg">AWAITING INPUT</p>
                <p className="text-xs mt-2 font-mono">Select a chat or start a new one</p>
              </div>
            )}
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-2xl backdrop-blur-md shadow-sm max-w-[90%] md:max-w-[80%] group relative ${msg.role === "user"
                  ? "bg-violet-600/10 dark:bg-violet-600/10 ml-auto border border-violet-500/20 text-violet-900 light:text-violet-900 dark:text-violet-100 rounded-tr-none"
                  : "bg-blue-900/10 dark:bg-blue-900/10 mr-auto border border-blue-500/20 text-blue-900 light:text-blue-900 dark:text-blue-100 rounded-tl-none"
                  }`}
              >
                <div className="text-sm md:text-base leading-relaxed prose dark:prose-invert prose-headings:text-inherit prose-p:text-inherit prose-strong:text-inherit prose-ul:text-inherit prose-ol:text-inherit prose-li:text-inherit prose-pre:bg-transparent max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {stripJSON(msg.content)}
                  </ReactMarkdown>
                </div>

                {msg.role === "assistant" && msg.content && (
                  <button
                    onClick={() => playMessageAudio(msg.content, idx)}
                    className={`absolute -bottom-6 left-0 p-1 transition-colors ${(isPlaying && playingMessageIndex === idx) || loadingMessageIndex === idx
                      ? "text-violet-300"
                      : "text-violet-400/50 hover:text-violet-300"
                      }`}
                    title={isPlaying && playingMessageIndex === idx ? "Stop reading" : "Read aloud"}
                    disabled={loadingMessageIndex === idx}
                  >
                    {loadingMessageIndex === idx ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : isPlaying && playingMessageIndex === idx ? (
                      <StopCircle size={16} className="text-red-400 hover:text-red-300" />
                    ) : (
                      <Volume2 size={16} />
                    )}
                  </button>
                )}
              </div>
            ))}
            {isProcessing && (
              <div className="flex items-center gap-2 text-violet-400 text-xs font-mono tracking-widest ml-2 animate-pulse">
                <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                PROCESSING
              </div>
            )}
            <div ref={(el) => { el?.scrollIntoView({ behavior: "smooth" }); }} />
          </div>
        </div>

        {/* Input Area */}
        <div className="flex-none w-full p-4 pb-6 z-20">
          <div className="max-w-4xl mx-auto flex flex-col gap-2">
            {/* Image Preview */}
            {previewUrl && (
              <div className="relative w-fit self-start ml-4 animate-in fade-in slide-in-from-bottom-2">
                <img src={previewUrl} alt="Preview" className="h-24 w-auto rounded-xl border border-violet-500/30 shadow-lg bg-black/50" />
                <button
                  onClick={clearImage}
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1.5 shadow-md hover:bg-red-600 transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            <div className="w-full flex items-center gap-2 md:gap-3 bg-white/5 p-2 pr-2 md:pr-3 rounded-[2rem] border border-white/10 backdrop-blur-xl shadow-[0_0_50px_rgba(0,0,0,0.5)]">
              <button
                onClick={isListening ? stopListening : startListening}
                className={`p-3 md:p-4 rounded-full transition-all duration-300 ${isListening
                  ? "bg-red-500/20 text-red-400 hover:bg-red-500/30 shadow-[0_0_20px_rgba(239,68,68,0.4)] animate-pulse"
                  : "bg-violet-500/10 text-violet-400 hover:bg-violet-500/20 hover:shadow-[0_0_15px_rgba(139,92,246,0.3)]"
                  }`}
                disabled={!hasRecognition}
                title="Voice Input"
              >
                {isListening ? <StopCircle size={20} /> : <Mic size={20} />}
              </button>

              <input
                type="file"
                accept="image/*"
                className="hidden"
                ref={fileInputRef}
                onChange={handleImageSelect}
              />

              <input
                type="file"
                accept=".pdf,.txt,.md,.docx"
                className="hidden"
                ref={docInputRef}
                onChange={handleFileUpload}
              />

              {/* Tools Menu */}
              <div className="relative">
                <button
                  onClick={() => setIsToolsMenuOpen(!isToolsMenuOpen)}
                  className={`p-2 md:p-3 rounded-full transition-all duration-300 ${isToolsMenuOpen
                    ? "bg-violet-500/20 text-violet-300 rotate-45"
                    : "bg-violet-500/10 text-violet-400 hover:bg-violet-500/20 hover:text-violet-300"
                    }`}
                  title="Tools"
                >
                  <Plus size={20} />
                </button>

                {isToolsMenuOpen && (
                  <div className="absolute bottom-full left-0 mb-4 bg-black/90 backdrop-blur-2xl border border-white/10 rounded-2xl p-2 flex flex-col gap-1 min-w-[180px] shadow-2xl animate-in fade-in slide-in-from-bottom-2 z-50">
                    <button
                      onClick={() => { docInputRef.current?.click(); setIsToolsMenuOpen(false); }}
                      className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/10 text-sm text-violet-200 transition-colors text-left"
                    >
                      <FileText size={16} className="text-violet-400" />
                      <span>Upload Document</span>
                    </button>

                    <button
                      onClick={() => { fileInputRef.current?.click(); setIsToolsMenuOpen(false); }}
                      className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/10 text-sm text-violet-200 transition-colors text-left"
                    >
                      <Paperclip size={16} className="text-violet-400" />
                      <span>Upload Image</span>
                    </button>

                    <button
                      onClick={() => { setIsResearchMode(!isResearchMode); setIsToolsMenuOpen(false); }}
                      className={`flex items-center gap-3 p-3 rounded-xl hover:bg-white/10 text-sm transition-colors text-left ${isResearchMode ? "bg-blue-500/20 text-blue-200" : "text-violet-200"}`}
                    >
                      <Globe size={16} className={isResearchMode ? "text-blue-400" : "text-violet-400"} />
                      <span>{isResearchMode ? "Disable Research" : "Research Mode"}</span>
                    </button>
                  </div>
                )}
              </div>

              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder={hasRecognition ? "Initialize command..." : isResearchMode ? "Enter research topic..." : "Type a message..."}
                className="flex-1 bg-transparent border-none outline-none text-foreground placeholder-violet-400/30 font-mono text-sm px-2 h-full min-w-0"
              />

              <button
                onClick={sendMessage}
                disabled={(!inputText.trim() && !selectedImage) || isProcessing}
                className="p-3 md:p-3.5 rounded-full bg-gradient-to-r from-violet-600 to-blue-600 text-white hover:opacity-90 disabled:opacity-50 disabled:hover:opacity-50 transition-all shadow-lg shadow-violet-500/20"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
      <audio ref={audioRef} className="hidden" />
    </main>
  );
}
