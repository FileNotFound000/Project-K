"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface UseVoiceInputReturn {
    isListening: boolean;
    transcript: string;
    startListening: () => void;
    stopListening: () => void;
    resetTranscript: () => void;
    hasRecognition: boolean;
    isWakeWordEnabled: boolean;
    toggleWakeWord: () => void;
    isWakeWordListening: boolean;
    isBackendConnected: boolean;
    finalTranscript: string | null;
    resetFinalTranscript: () => void;
}

export const useVoiceInput = (): UseVoiceInputReturn => {
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState("");
    const [recognition, setRecognition] = useState<any>(null);
    const [wakeWordRecognition, setWakeWordRecognition] = useState<any>(null);
    const [isWakeWordEnabled, setIsWakeWordEnabled] = useState(false);
    const [isWakeWordListening, setIsWakeWordListening] = useState(false);
    const [isBackendConnected, setIsBackendConnected] = useState(false);
    const [finalTranscript, setFinalTranscript] = useState<string | null>(null);

    // Force load voices on mount (Chrome requirement)
    useEffect(() => {
        if (typeof window !== "undefined" && "speechSynthesis" in window) {
            window.speechSynthesis.getVoices();
        }
    }, []);

    // Helper for Local TTS
    const speak = useCallback((text: string, onEnd?: () => void) => {
        if (typeof window !== "undefined" && "speechSynthesis" in window) {
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);

            // Attempt to select a clear English voice
            const voices = window.speechSynthesis.getVoices();
            const preferredVoice = voices.find(v =>
                (v.name.includes("Google") || v.name.includes("Microsoft")) && v.lang.includes("en")
            ) || voices.find(v => v.lang.includes("en")) || voices[0];

            if (preferredVoice) {
                utterance.voice = preferredVoice;
                console.log("Using Voice:", preferredVoice.name);
            }

            utterance.volume = 1;
            utterance.rate = 1; /* Normal speed */
            utterance.pitch = 1;

            utterance.onstart = () => console.log("TTS Current Status: Started");

            utterance.onend = () => {
                console.log("TTS Current Status: Ended");
                if (onEnd) setTimeout(onEnd, 100);
            };

            utterance.onerror = (e) => {
                console.error("TTS Current Status: Error", e);
                // Even on error, we should probably continue to listening so the user isn't stuck
                if (onEnd) onEnd();
            };

            window.speechSynthesis.speak(utterance);
        } else {
            console.warn("TTS not supported");
            onEnd?.();
        }
    }, []);

    // Refs to avoid stale closures in event handlers
    const isListeningRef = useRef(false);
    const isWakeWordEnabledRef = useRef(false);
    // New ref to track transition state
    const isSwitchingToMainRef = useRef(false);

    // Sync refs
    useEffect(() => {
        isListeningRef.current = isListening;
    }, [isListening]);

    useEffect(() => {
        isWakeWordEnabledRef.current = isWakeWordEnabled;
    }, [isWakeWordEnabled]);

    // Main Recognition Setup
    useEffect(() => {
        if (typeof window !== "undefined" && "webkitSpeechRecognition" in window) {
            // @ts-ignore
            const recognitionInstance = new window.webkitSpeechRecognition();
            recognitionInstance.continuous = false;
            recognitionInstance.interimResults = true;
            recognitionInstance.lang = "en-US";

            recognitionInstance.onstart = () => {
                setIsListening(true);
                // When main starts, we are definitely done switching
                isSwitchingToMainRef.current = false;
            };

            recognitionInstance.onend = () => {
                setIsListening(false);
                // Restart wake word if it's supposed to be enabled
                if (isWakeWordEnabledRef.current) {
                    startWakeWordListener();
                }
            };

            recognitionInstance.onresult = (event: any) => {
                const current = event.resultIndex;
                const result = event.results[current];
                const transcriptText = result[0].transcript;
                console.log("Main Recognition Result:", transcriptText);
                setTranscript(transcriptText);

                if (result.isFinal) {
                    console.log("Final Transcript Detected:", transcriptText);
                    setFinalTranscript(transcriptText);
                }
            };

            recognitionInstance.onerror = (event: any) => {
                console.error("Main Recognition Error:", event.error);
                setIsListening(false);
            };

            setRecognition(recognitionInstance);

            // Cleanup
            return () => {
                recognitionInstance.abort();
            };
        }
    }, []); // Only run once on mount

    const startListening = useCallback(() => {
        if (recognition) {
            try {
                setFinalTranscript(null);
                recognition.start();
            } catch (e) {
                console.error("Error starting recognition:", e);
            }
        }
    }, [recognition]);

    const stopListening = useCallback(() => {
        if (recognition) {
            recognition.stop();
        }
    }, [recognition]);

    // WebSocket for Backend Wake Word (VOSK)
    useEffect(() => {
        let ws: WebSocket | null = null;
        let reconnectTimer: NodeJS.Timeout;

        const connect = () => {
            if (typeof window === "undefined") return;

            ws = new WebSocket("ws://localhost:8000/ws/voice_status");

            ws.onopen = () => {
                console.log("Connected to Voice Backend");
                setIsBackendConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === "WAKE_WORD_DETECTED") {
                        console.log("Backend Wake Word Detected:", data.text);
                        // Only auto-start if enabled and not already listening
                        if (isWakeWordEnabledRef.current && !isListeningRef.current && !isSwitchingToMainRef.current) {
                            // Turn on "switching" flag early to prevent duplicate triggers
                            isSwitchingToMainRef.current = true;
                            speak("Yes Boss", () => {
                                startListening();
                            });
                        }
                    }
                } catch (e) {
                    console.error("WS Parse Error", e);
                }
            };

            ws.onerror = (e) => {
                console.error("Voice WS Error", e);
                setIsBackendConnected(false);
            };

            ws.onclose = () => {
                console.log("Voice WS Closed. Reconnecting...");
                setIsBackendConnected(false);
                reconnectTimer = setTimeout(connect, 3000);
            };
        };

        if (isWakeWordEnabled) {
            connect();
        }

        return () => {
            if (ws) ws.close();
            clearTimeout(reconnectTimer);
        };
    }, [isWakeWordEnabled, startListening, speak]);

    // Cleanup: No longer need startWakeWordListener / stopWakeWordListener as backend handles it
    // But keeping empty functions to avoid breaking return signature if needed

    const startWakeWordListener = useCallback(() => { }, []);
    const stopWakeWordListener = useCallback(() => { }, []);

    const toggleWakeWord = useCallback(() => {
        setIsWakeWordEnabled(prev => !prev);
    }, []);

    // Watcher to start/stop wake word based on enabled state
    // (Now just handled by WebSocket connection effect)

    const resetTranscript = useCallback(() => {
        setTranscript("");
    }, []);

    const resetFinalTranscript = useCallback(() => {
        setFinalTranscript(null);
    }, []);

    return {
        isListening,
        transcript,
        finalTranscript,
        resetFinalTranscript,
        startListening,
        stopListening,
        resetTranscript,
        hasRecognition: !!recognition,
        isWakeWordEnabled,
        toggleWakeWord,
        isWakeWordListening,
        isBackendConnected
    };
};
