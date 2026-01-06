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
}

export const useVoiceInput = (): UseVoiceInputReturn => {
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState("");
    const [recognition, setRecognition] = useState<any>(null);
    const [wakeWordRecognition, setWakeWordRecognition] = useState<any>(null);
    const [isWakeWordEnabled, setIsWakeWordEnabled] = useState(false);
    const [isWakeWordListening, setIsWakeWordListening] = useState(false);

    // Refs to avoid stale closures in event handlers
    const isListeningRef = useRef(false);
    const isWakeWordEnabledRef = useRef(false);

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
                const transcriptText = event.results[current][0].transcript;
                console.log("Main Recognition Result:", transcriptText);
                setTranscript(transcriptText);
            };

            setRecognition(recognitionInstance);

            // Cleanup
            return () => {
                recognitionInstance.abort();
            };
        }
    }, []); // Only run once on mount

    // Wake Word Recognition Setup
    useEffect(() => {
        if (typeof window !== "undefined" && "webkitSpeechRecognition" in window) {
            // @ts-ignore
            const wakeInstance = new window.webkitSpeechRecognition();
            wakeInstance.continuous = true;
            wakeInstance.interimResults = true;
            wakeInstance.lang = "en-US";

            wakeInstance.onstart = () => setIsWakeWordListening(true);

            wakeInstance.onend = () => {
                setIsWakeWordListening(false);
                // Auto-restart logic
                if (isWakeWordEnabledRef.current && !isListeningRef.current) {
                    console.log("Wake word listener stopped. Restarting...");
                    try {
                        wakeInstance.start();
                    } catch (e) {
                        // Ignore
                    }
                }
            };

            wakeInstance.onresult = (event: any) => {
                const results = event.results;
                const lastResult = results[results.length - 1];
                const text = lastResult[0].transcript.toLowerCase().trim();

                // Wake Word Detection Logic
                // We use regex to ensure we match whole words or specific phrases, reducing false positives from "ether", "whether", etc.
                const wakeWordRegex = /(^|\s)(hey k|k|kay|computer)(\s|$|[.,!?])/i;
                if (wakeWordRegex.test(text)) {
                    console.log(`Wake Word Detected on: "${text}"`);
                    wakeInstance.abort(); // Force stop immediately
                    setIsWakeWordListening(false);

                    // Small delay to ensure mic is released before starting main recognition
                    setTimeout(() => {
                        startListeningRef.current?.();
                    }, 250);
                }
            };

            setWakeWordRecognition(wakeInstance);

            return () => {
                wakeInstance.abort();
            };
        }
    }, []);

    // Ref to hold the current startListening function to call it from the wake word closure
    const startListeningRef = useRef<() => void>(() => { });

    const startListening = useCallback(() => {
        // Stop wake word first
        if (wakeWordRecognition) {
            try { wakeWordRecognition.abort(); } catch (e) { }
        }

        if (recognition) {
            try {
                recognition.start();
            } catch (e) {
                console.error("Error starting recognition:", e);
            }
        }
    }, [recognition, wakeWordRecognition]);

    // Update the ref whenever startListening changes
    useEffect(() => {
        startListeningRef.current = startListening;
    }, [startListening]);

    const stopListening = useCallback(() => {
        if (recognition) {
            recognition.stop();
        }
    }, [recognition]);

    const startWakeWordListener = useCallback(() => {
        if (wakeWordRecognition && !isListeningRef.current) {
            try {
                wakeWordRecognition.start();
            } catch (e) {
                console.log("Wake word already started or error:", e);
            }
        }
    }, [wakeWordRecognition]);

    const stopWakeWordListener = useCallback(() => {
        if (wakeWordRecognition) {
            try {
                wakeWordRecognition.stop();
            } catch (e) { }
        }
    }, [wakeWordRecognition]);

    const toggleWakeWord = useCallback(() => {
        if (isWakeWordEnabled) {
            setIsWakeWordEnabled(false);
            // The effect watching [isWakeWordEnabled] will handle stopping
        } else {
            setIsWakeWordEnabled(true);
            // The effect watching [isWakeWordEnabled] will handle starting
        }
    }, [isWakeWordEnabled]);

    // Watcher to start/stop wake word based on enabled state
    useEffect(() => {
        // Use refs to avoid dependency loops if needed, but state is fine here
        if (isWakeWordEnabled && !isListening) {
            const timer = setTimeout(() => {
                startWakeWordListener();
            }, 100);
            return () => clearTimeout(timer);
        } else if (!isWakeWordEnabled) {
            stopWakeWordListener();
        }
    }, [isWakeWordEnabled, isListening, startWakeWordListener, stopWakeWordListener]);

    const resetTranscript = useCallback(() => {
        setTranscript("");
    }, []);

    return {
        isListening,
        transcript,
        startListening,
        stopListening,
        resetTranscript,
        hasRecognition: !!recognition,
        isWakeWordEnabled,
        toggleWakeWord,
        isWakeWordListening
    };
};
