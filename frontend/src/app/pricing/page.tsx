'use client';

import React, { useState } from 'react';
import { useAuth, useUser, SignInButton } from '@clerk/nextjs';
import { Check, Sparkles, Zap, ChevronRight } from 'lucide-react';
import { createCheckoutSession } from '../../../lib/api';

export default function PricingPage() {
  const { isSignedIn, getToken } = useAuth();
  const { user } = useUser();
  const [loading, setLoading] = useState(false);

  const tier = (user?.publicMetadata as any)?.tier || 'free';
  const isPro = tier === 'pro';

  const handleUpgrade = async () => {
    if (!isSignedIn) return;
    setLoading(true);
    try {
      const token = await getToken();
      if (!token) return;
      const { url } = await createCheckoutSession(
        `${window.location.origin}/pricing?success=true`,
        `${window.location.origin}/pricing`,
        token
      );
      window.location.href = url;
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const isSuccess = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('success') === 'true';

  return (
    <div className="min-h-screen relative">
      <div
        className="fixed inset-0 bg-[url('/bgimg.jpg')] bg-cover bg-center"
        style={{ filter: 'blur(4px)', transform: 'scale(1.05)' }}
      />
      <main className="relative z-10 min-h-screen flex flex-col items-center pt-[100px] px-6">
        <h1 className="text-4xl font-semibold text-white mb-3">Pricing</h1>
        <p className="text-neutral-400 text-base mb-12 max-w-lg text-center">
          Unlock unlimited access to Polish court ruling search and AI-powered answers.
        </p>

        {isSuccess && (
          <div className="mb-8 px-6 py-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm max-w-md text-center">
            Payment successful! Your account has been upgraded to Pro.
          </div>
        )}

        <div className="flex flex-col md:flex-row gap-6 w-full max-w-3xl">
          {/* Free tier */}
          <div className="flex-1 p-6 rounded-2xl bg-black/60 backdrop-blur-xl border border-white/[0.08]">
            <p className="text-sm font-semibold text-neutral-400 mb-1">Free</p>
            <p className="text-3xl font-bold text-white mb-1">0 zł</p>
            <p className="text-xs text-neutral-500 mb-6">forever</p>
            <div className="space-y-3 mb-8">
              {[
                '3 searches / day (anonymous)',
                '10 searches / day (signed in)',
                'AI-generated answers',
                'Full judgment text',
              ].map((f) => (
                <div key={f} className="flex items-center gap-2 text-sm">
                  <Check className="w-4 h-4 text-neutral-500" />
                  <span className="text-neutral-300">{f}</span>
                </div>
              ))}
            </div>
            {!isPro && (
              <div className="py-2.5 rounded-lg border border-white/[0.1] text-center text-sm text-neutral-500">
                Current plan
              </div>
            )}
          </div>

          {/* Pro tier */}
          <div className="flex-1 p-6 rounded-2xl bg-black/60 backdrop-blur-xl border border-[#e05929]/30 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#e05929] to-transparent" />
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-4 h-4 text-[#e05929]" />
              <p className="text-sm font-semibold text-[#e05929]">Pro</p>
            </div>
            <p className="text-3xl font-bold text-white mb-1">29 zł</p>
            <p className="text-xs text-neutral-500 mb-6">/ month</p>
            <div className="space-y-3 mb-8">
              {[
                'Unlimited searches per day',
                'Unlimited AI answers',
                'Priority reranking',
                'Advanced filters (coming soon)',
                'Export results (coming soon)',
              ].map((f) => (
                <div key={f} className="flex items-center gap-2 text-sm">
                  <Check className="w-4 h-4 text-[#e05929]" />
                  <span className="text-neutral-300">{f}</span>
                </div>
              ))}
            </div>
            {isPro ? (
              <div className="py-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-center text-sm text-emerald-400">
                Active
              </div>
            ) : isSignedIn ? (
              <button
                onClick={handleUpgrade}
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-[#e05929] text-white text-sm font-medium hover:bg-[#c94d23] transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    Upgrade to Pro
                    <ChevronRight className="w-4 h-4" />
                  </>
                )}
              </button>
            ) : (
              <SignInButton>
                <button className="w-full py-2.5 rounded-lg bg-[#e05929] text-white text-sm font-medium hover:bg-[#c94d23] transition-colors flex items-center justify-center gap-2 cursor-pointer">
                  Sign in to upgrade
                  <ChevronRight className="w-4 h-4" />
                </button>
              </SignInButton>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}