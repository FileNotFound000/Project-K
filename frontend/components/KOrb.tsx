"use client";

import React from "react";
import { motion, Variants } from "framer-motion";

interface KOrbProps {
    isSpeaking: boolean;
    isListening: boolean;
}

const KOrb: React.FC<KOrbProps> = ({ isSpeaking, isListening }) => {
    // ... same variants ...
    const coreVariants: Variants = {
        speaking: {
            scale: [1, 1.5, 1],
            opacity: [0.5, 0.8, 0.5],
            transition: { duration: 0.4, repeat: Infinity, ease: "easeInOut" }
        },
        listening: {
            scale: [1, 1.1, 1],
            opacity: [0.4, 0.6, 0.4],
            transition: { duration: 2, repeat: Infinity, ease: "easeInOut" }
        },
        idle: {
            scale: 1,
            opacity: 0.3,
            transition: { duration: 0.5, ease: "easeInOut" }
        }
    };

    const currentState = isSpeaking ? "speaking" : isListening ? "listening" : "idle";

    return (
        <div className="relative flex items-center justify-center w-96 h-96">
            {/* Core Glow - Adjusted to be more neutral/white for 'K' or keep violet? Keeping violet for now unless requested otherwise */}
            <motion.div
                className="absolute w-40 h-40 bg-violet-600 rounded-full blur-2xl"
                variants={coreVariants}
                animate={currentState}
            />

            {/* Inner Core */}
            <motion.div
                className="absolute w-32 h-32 bg-gradient-to-br from-violet-500 to-blue-600 rounded-full shadow-[0_0_50px_rgba(139,92,246,0.5)]"
                animate={{
                    scale: isSpeaking ? 1.1 : 1,
                }}
                transition={{
                    duration: 0.3,
                    ease: "easeInOut",
                }}
            />

            {/* Rotating Rings */}
            {[0, 1, 2].map((i) => (
                <motion.div
                    key={i}
                    className={`absolute rounded-full border border-violet-400/30 border-t-transparent border-l-transparent`}
                    style={{
                        width: `${16 + i * 4}rem`,
                        height: `${16 + i * 4}rem`,
                    }}
                    animate={{
                        rotate: i % 2 === 0 ? 360 : -360,
                        scale: isListening ? 1.05 : 1,
                    }}
                    transition={{
                        rotate: { duration: 10 + i * 5, repeat: Infinity, ease: "linear" },
                        scale: { duration: 1, ease: "easeInOut" },
                    }}
                />
            ))}

            {/* Particles */}
            <div className="absolute w-full h-full bg-violet-900/10 rounded-full blur-3xl -z-10" />
        </div>
    );
};

export default KOrb;
