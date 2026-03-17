'use client';

import React, { useState } from 'react';
import { useAuth, useUser } from '@clerk/nextjs';
import { useAuthModal } from '../../components/AuthContext';
import { Check, Sparkles, AlertCircle, ChevronRight, Crown, Shield } from 'lucide-react';
import { createCheckoutSession } from '../../../lib/api';

export default function PricingPage() {
  const { isSignedIn, getToken } = useAuth();
  const { openSignIn } = useAuthModal();
  const { user } = useUser();
  const [loading, setLoading] = useState(false);

  // Logic Preserved
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
    <div className="min-h-screen relative font-sans text-white">
      {/* Background with blur */}
      <div
        className="fixed inset-0 bg-[url('/bgimg.jpg')] bg-cover bg-center"
        style={{ filter: 'blur(8px) brightness(0.4)', transform: 'scale(1.1)' }}
      />
      
      <main className="relative z-10 min-h-screen flex flex-col items-center pt-32 px-6 pb-20">
        
        {/* Header Section */}
        <div className="text-center mb-16 max-w-2xl relative">
          <div className="absolute -top-20 left-1/2 -translate-x-1/2 w-64 h-64 bg-[#e05929]/20 rounded-full blur-3xl pointer-events-none" />
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6 drop-shadow-sm tracking-tight">
            Wybierz plan dla siebie
          </h1>
          <p className="text-lg text-neutral-400 font-medium">
            Odblokuj pełny potencjał Lexara i przyspiesz swoją pracę z prawem.
          </p>
        </div>

        {isSuccess && (
          <div className="mb-12 px-6 py-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-medium flex items-center gap-3 animate-in fade-in slide-in-from-top-4 duration-500 shadow-lg shadow-emerald-500/5">
            <div className="p-1 bg-emerald-500/20 rounded-full">
              <Check className="w-4 h-4" />
            </div>
            Płatność zakończona sukcesem! Twój plan został ulepszony do Pro.
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-5xl items-stretch">
          
          {/* Free Tier Card */}
          <div className="relative group rounded-3xl p-[1px] bg-gradient-to-b from-white/10 to-transparent hover:from-white/20 transition-all duration-300">
            <div className="h-full bg-black/40 backdrop-blur-xl rounded-[23px] p-8 flex flex-col border border-white/5">
              
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-2.5 rounded-xl bg-white/5 border border-white/5 text-neutral-400 group-hover:bg-white/10 transition-colors">
                    <Shield className="w-6 h-6" />
                  </div>
                  <h3 className="text-xl font-semibold text-neutral-200">Start</h3>
                </div>
                
                <div className="flex items-baseline gap-1 mb-2">
                  <span className="text-5xl font-bold text-white tracking-tight">0 zł</span>
                  <span className="text-neutral-500 font-medium path-bottom-1">/ na zawsze</span>
                </div>
                
                <p className="text-neutral-400 text-sm leading-relaxed">
                  Idealny do szybkiego sprawdzenia orzeczeń i przetestowania możliwości AI.
                </p>
              </div>

              <div className="space-y-4 mb-10 flex-1">
                <FeatureItem text="3 wyszukania dziennie (blik)" />
                <FeatureItem text="10 wyszukań dziennie (zalogowany)" />
                <FeatureItem text="Podstawowe odpowiedzi AI" />
                <FeatureItem text="Dostęp do treści orzeczeń" />
              </div>

              <div className="mt-auto">
                {!isPro ? (
                  <div className="w-full py-4 text-center rounded-xl border border-white/10 bg-white/5 text-neutral-400 text-sm font-medium">
                    Twój obecny plan
                  </div>
                ) : (
                  <div className="w-full py-4 text-center text-sm text-neutral-500 font-medium">
                    Plan podstawowy
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Pro Tier Card - Highlighted */}
          <div className="relative group rounded-3xl p-[1px] bg-gradient-to-b from-[#e05929] to-[#e05929]/10 shadow-2xl shadow-[#e05929]/10 hover:shadow-[#e05929]/20 transition-all duration-500 scale-[1.02] md:-mt-4 md:-mb-4 z-10">
            <div className="h-full bg-[#0a0a0a]/90 backdrop-blur-xl rounded-[23px] p-8 flex flex-col relative overflow-hidden">
              
              {/* Highlight Glow */}
              <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-[#e05929] to-transparent opacity-50" />
              <div className="absolute top-0 right-0 w-64 h-64 bg-[#e05929]/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none" />

              <div className="mb-8 relative">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-[#e05929]/10 border border-[#e05929]/20 text-[#e05929]">
                      <Crown className="w-6 h-6" />
                    </div>
                    <h3 className="text-xl font-semibold text-white">Pro</h3>
                  </div>
                  <div className="px-3 py-1 rounded-full bg-[#e05929] text-white text-[10px] font-bold tracking-wider uppercase shadow-lg shadow-[#e05929]/20">
                    Polecany
                  </div>
                </div>
                
                <div className="flex items-baseline gap-1 mb-2">
                  <span className="text-5xl font-bold text-white tracking-tight">29 zł</span>
                  <span className="text-neutral-400 font-medium text-sm">/ jednorazowo</span>
                </div>
                
                <p className="text-neutral-300 text-sm leading-relaxed">
                  Pełna moc analizy prawnej bez żadnych limitów. Dla profesjonalistów.
                </p>
              </div>

              <div className="space-y-4 mb-10 flex-1 relative">
                <FeatureItem text="Nielimitowane wyszukiwania" highlighted />
                <FeatureItem text="Nielimitowane pytania do AI" highlighted />
                <FeatureItem text="Priorytetowe sortowanie wyników" />
                <FeatureItem text="Analiza długich dokumentów" />
                <FeatureItem text="Wsparcie techniczne 24/7" />
              </div>

              <div className="mt-auto relative">
                {isPro ? (
                  <div className="w-full py-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold text-sm flex items-center justify-center gap-2">
                    <Check className="w-4 h-4" />
                    Plan aktywny
                  </div>
                ) : isSignedIn ? (
                  <button
                    onClick={handleUpgrade}
                    disabled={loading}
                    className="group/btn w-full py-4 rounded-xl bg-[#e05929] hover:bg-[#ff6b3d] text-white font-semibold text-sm shadow-lg shadow-[#e05929]/25 transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <>
                        Wybierz plan Pro
                        <ChevronRight className="w-4 h-4 group-hover/btn:translate-x-0.5 transition-transform" />
                      </>
                    )}
                  </button>
                ) : (
                  <button
  onClick={openSignIn}
  className="group/btn w-full py-4 rounded-xl bg-[#e05929] hover:bg-[#ff6b3d] text-white font-semibold text-sm shadow-lg shadow-[#e05929]/25 transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 cursor-pointer flex items-center justify-center gap-2"
>
  Zaloguj się aby kupić
  <ChevronRight className="w-4 h-4 group-hover/btn:translate-x-0.5 transition-transform" />
</button>
                )}
              </div>
            </div>
          </div>

        </div>
        
        {/* Footer Note */}
        <p className="mt-16 text-neutral-500 text-sm text-center max-w-lg">
          Wszystkie ceny są cenami brutto. Płatność jest jednorazowa i zapewnia dożywotni dostęp do funkcji Pro w ramach obecnej wersji.
        </p>

      </main>
    </div>
  );
}

function FeatureItem({ text, highlighted = false }: { text: string; highlighted?: boolean }) {
  return (
    <div className="flex items-start gap-3 group/item">
      <div className={`mt-0.5 p-0.5 rounded-full transition-colors ${highlighted ? 'bg-[#e05929]/20 group-hover/item:bg-[#e05929]/30' : 'bg-white/10 group-hover/item:bg-white/20'}`}>
        <Check className={`w-3.5 h-3.5 ${highlighted ? 'text-[#e05929]' : 'text-neutral-400'}`} />
      </div>
      <span className={`text-sm font-medium transition-colors ${highlighted ? 'text-white' : 'text-neutral-400 group-hover/item:text-neutral-300'}`}>
        {text}
      </span>
    </div>
  );
}