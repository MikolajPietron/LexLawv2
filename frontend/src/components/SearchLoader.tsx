'use client';

import React, { useState, useEffect } from 'react';
import { Scale } from 'lucide-react';

const STEPS = [
  'Analizuję zapytanie...',
  'Przeszukuję bazę orzeczeń...',
  'Dopasowuję wyniki...',
  'Generuję odpowiedź AI...',
];

export default function SearchLoader() {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStepIndex((prev) => (prev + 1) % STEPS.length);
    }, 2200);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ animation: 'loaderFadeIn 0.3s ease-out' }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/85 backdrop-blur-xl" />

      {/* Content */}
      <div className="relative flex flex-col items-center">

        {/* Orbiting rings container */}
        <div className="relative w-32 h-32 mb-10">
          {/* Glow pulse */}
          <div
            className="absolute inset-[-20px] rounded-full bg-[#e05929]/8 blur-3xl"
            style={{ animation: 'loaderGlow 2.4s ease-in-out infinite' }}
          />

          {/* Outer ring */}
          <div
            className="absolute inset-0 rounded-full border border-[#e05929]/25"
            style={{ animation: 'loaderSpin 3s linear infinite' }}
          >
            <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-[#e05929] shadow-lg shadow-[#e05929]/50" />
          </div>

          {/* Middle ring */}
          <div
            className="absolute inset-4 rounded-full border border-[#e05929]/15"
            style={{ animation: 'loaderSpin 2s linear infinite reverse' }}
          >
            <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-[#e05929]/70" />
          </div>

          {/* Inner ring */}
          <div
            className="absolute inset-8 rounded-full border border-white/[0.06]"
            style={{ animation: 'loaderSpin 4s linear infinite' }}
          >
            <div className="absolute top-1/2 -right-0.5 -translate-y-1/2 w-1 h-1 rounded-full bg-white/40" />
          </div>

          {/* Center icon */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div
              className="w-14 h-14 rounded-2xl bg-[#e05929]/10 border border-[#e05929]/20 flex items-center justify-center"
              style={{ animation: 'loaderPulse 2.4s ease-in-out infinite' }}
            >
              <Scale className="w-6 h-6 text-[#e05929]" />
            </div>
          </div>
        </div>

        {/* Title */}
        <h2
          className="text-xl font-bold text-white tracking-tight mb-3"
          style={{ animation: 'loaderContentUp 0.5s ease-out 0.1s both' }}
        >
          Szukam orzeczeń
        </h2>

        {/* Rotating step text */}
        <p
          key={stepIndex}
          className="text-sm text-neutral-400 mb-8 h-5"
          style={{ animation: 'loaderStepSwap 2.2s ease-in-out' }}
        >
          {STEPS[stepIndex]}
        </p>

        {/* Progress bar */}
        <div
          className="w-48 h-[3px] rounded-full bg-white/[0.06] overflow-hidden"
          style={{ animation: 'loaderContentUp 0.5s ease-out 0.3s both' }}
        >
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#e05929] to-[#ff6b3d]"
            style={{ animation: 'loaderProgress 2.2s ease-in-out infinite' }}
          />
        </div>
      </div>
    </div>
  );
}