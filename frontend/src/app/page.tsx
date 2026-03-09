'use client';

import { useState, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { SignInButton } from '@clerk/nextjs';
import { askQuestion, getFullJudgment, AskResponse, FullJudgment, RateLimitError } from '../../lib/api';
import ColorBends from '../components/ColorBends';
import Orb from '../components/Orb';
import Prism from '../components/Prism';
import Aurora from '../components/Aurora';
import RippleGrid from '../components/RippleGrid';
import BackgroundImg from '../../public/bgimg.jpg';
import { GlassCard } from 'react-glass-ui';
import { 
  Search,
  X, 
  Building2,
  FileText,
  Calendar,
  Users,
  ExternalLink,
  Sparkles,
  BotMessageSquare
} from 'lucide-react';

const COURT_TYPES: Record<string, string> = {
  COMMON: 'Sąd powszechny',
  SUPREME: 'Sąd Najwyższy',
  CONSTITUTIONAL_TRIBUNAL: 'Trybunał Konstytucyjny',
  NATIONAL_APPEAL_CHAMBER: 'KIO',
};

const JUDGMENT_TYPES: Record<string, string> = {
  SENTENCE: 'Wyrok',
  DECISION: 'Postanowienie',
  RESOLUTION: 'Uchwała',
  REASONS: 'Uzasadnienie',
};

const EXAMPLE_QUERIES = [
  'odszkodowanie za wypadek przy pracy',
  'alimenty na dziecko',
  'art. 278 KK kradzież',
  'rozwiązanie umowy o pracę',
];

export default function Home() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedJudgment, setSelectedJudgment] = useState<FullJudgment | null>(null);
  const [loadingJudgment, setLoadingJudgment] = useState(false);
  const [rateLimitInfo, setRateLimitInfo] = useState<RateLimitError | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { getToken } = useAuth();
    const [answerExpanded, setAnswerExpanded] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    setRateLimitInfo(null);
    try {
      const token = await getToken();
      const data = await askQuestion(query, 5, true, token);
      setResults(data);
    } catch (error) {
      if (error && typeof error === 'object' && 'detail' in error && (error as RateLimitError).detail === 'rate_limit') {
        setRateLimitInfo(error as RateLimitError);
      } else {
        console.error(error);
      }
    }
    setLoading(false);
  };

  const handleShowFull = async (originId: number) => {
    setLoadingJudgment(true);
    try {
      const token = await getToken();
      const judgment = await getFullJudgment(originId, token);
      setSelectedJudgment(judgment);
    } catch (error) {
      console.error(error);
    }
    setLoadingJudgment(false);
  };

  const handleExampleClick = (example: string) => {
    setQuery(example);
    inputRef.current?.focus();
  };

  const hasResults = results !== null;

  return (
    <div className="min-h-screen relative">
      {/* Blurred background image */}
      <div
        className="fixed inset-0 bg-[url('/bgimg.jpg')] bg-cover bg-center"
        style={{ filter: 'blur(4px)', transform: 'scale(1.05)' }}
      />
      {/* Content */}
      <main className={`relative z-10 min-h-screen flex flex-col ${!hasResults ? 'items-center justify-center' : 'pt-[60px]'}`}>
        {/* Hero / Search Section */}
        <div className={`w-full transition-all duration-500 ${hasResults ? 'py-8' : 'py-0'}`}>
          <div className={`mx-auto px-6 ${hasResults ? 'max-w-4xl' : 'max-w-4xl'}`}>

            {/* Hero text — only before results */}
            {!hasResults && (
              <div className="text-center mb-10">
                <h1 className="text-5xl font-semibold text-white mb-6" style={{ fontFamily: "'Agrandir WideLight', sans-serif", letterSpacing: '0.1em' }}>
                  Wyszukiwarka orzeczeń sądowych
                </h1>
                <p className="text-[#cbced4] text-base mb-24" style={{ fontFamily: "'Agrandir WideLight', sans-serif", letterSpacing: '0.1em' }}>
                  Przeszukuj miliony polskich orzeczeń sądowych za pomocą AI.
                </p>
              </div>
            )}

            {/* Search bar */}
            <form onSubmit={handleSearch}>
              <div style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }} suppressHydrationWarning>
                <GlassCard
                  height={60}
                  blur={12}
                  brightness={90}
                  saturation={120}
                  borderRadius={20}
                  borderSize={1}
                  borderColor="#ffffff"
                  borderOpacity={0.2}
                  backgroundOpacity={0.1}
                  backgroundColor="#ffffff"
                  padding="12px 24px"
                  flexibility={0.5}
                  onHoverScale={1.01}
                  chromaticAberration={12}
                  distortion={0}
                  contentCenter
                  itemsCenter
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '500px' }}>
                    <Search className="w-6 h-6 text-white flex-shrink-0" />
                    <input
                      ref={inputRef}
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="np. odszkodowanie za wypadek przy pracy..."
                      className="flex-1 bg-transparent text-white text-m placeholder:text-white focus:outline-none"
                    />
                    <button
                      type="submit"
                      disabled={!query.trim() || loading}
                      className="flex-shrink-0 h-8 px-4 rounded-lg bg-white text-black text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-neutral-200 transition-all"
                    >
                      {loading ? (
                        <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                      ) : (
                        'Szukaj'
                      )}
                    </button>
                  </div>
                </GlassCard>
              </div>
            </form>

            {/* Rate limit banner */}
            {rateLimitInfo && (
              <div className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-300">
                {rateLimitInfo.authenticated ? (
                  <p>Dzienny limit wyszukiwań ({rateLimitInfo.limit}) został wyczerpany. Spróbuj ponownie jutro.</p>
                ) : (
                  <div className="flex items-center justify-between">
                    <p>Limit darmowych wyszukiwań wyczerpany. Zaloguj się, aby kontynuować.</p>
                    <SignInButton>
                      <button className="ml-4 flex-shrink-0 px-4 py-1.5 rounded-lg bg-white text-black text-sm font-medium hover:bg-neutral-200 transition-all cursor-pointer">
                        Zaloguj się
                      </button>
                    </SignInButton>
                  </div>
                )}
              </div>
            )}

            {/* Example queries — only before results */}
            {!hasResults && !rateLimitInfo && (
              <div className="flex flex-wrap justify-center gap-2 mt-5">
                {EXAMPLE_QUERIES.map((example) => (
                  <button
                    key={example}
                    onClick={() => handleExampleClick(example)}
                    className="text-xs text-white px-3 py-1.5 rounded-lg bg-white/[0.1] border border-white/[0.6] hover:border-white/[0.15] hover:text-neutral-300 transition-all cursor-pointer"
                  >
                    {example}
                  </button>
                ))}
              </div>
            )}

          </div>
        </div>

        {/* Results Section */}
        {hasResults && (
          <div className="flex-1 pb-12">
            <div className="max-w-4xl mx-auto px-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <p className="text-sm uppercase tracking-widest text-neutral-500">
                    Znaleziono {results.results.length} orzeczeń
                  </p>
                  {results.optimized_query && (
                    <p className="text-xs text-neutral-600 mt-1.5 flex items-center gap-1.5">
                      <Sparkles className="w-3 h-3 text-neutral-500" />
                      <span>Zoptymalizowane: <span className="text-neutral-400">{results.optimized_query}</span></span>
                    </p>
                  )}
                </div>
                <button
                  onClick={() => setResults(null)}
                  className="text-xs uppercase tracking-wider text-white hover:text-white transition-colors"
                >
                  Nowe wyszukiwanie
                </button>
              </div>

                            {/* AI Answer Card */}
              {results.answer && (() => {
                const paragraphs = results.answer.split('\n\n');
                const firstParagraph = paragraphs[0];
                const rest = paragraphs.slice(1).join('\n\n');

                return (
                  <div className="mb-6 rounded-xl bg-white/[0.04] backdrop-blur-md border border-white/[0.08] border-l-2 border-l-[#e05929] shadow-lg shadow-black/20">
                    <div className="p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <BotMessageSquare className="w-4 h-4 text-[#e05929]" />
                        <h3 className="text-sm font-semibold text-white">Odpowiedź AI</h3>
                      </div>
                      <p className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap">{firstParagraph}</p>

                      {rest && (
                        <>
                          <div
                            className="grid transition-[grid-template-rows] duration-500 ease-in-out"
                            style={{ gridTemplateRows: answerExpanded ? '1fr' : '0fr' }}
                          >
                            <div className="overflow-hidden">
                              <p className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap pt-4">{rest}</p>
                            </div>
                          </div>

                          <button
                            onClick={() => setAnswerExpanded(!answerExpanded)}
                            className="mt-3 flex items-center gap-1.5 text-xs font-medium text-white hover:text-white hover:scale-[1.05] duration-300 transition-all cursor-pointer"
                          >
                            {answerExpanded ? 'Zwiń' : 'Rozwiń pełną odpowiedź'}
                            <svg
                              className={`w-3.5 h-3.5 transition-transform duration-300 ${answerExpanded ? 'rotate-180' : ''}`}
                              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })()}
              <div className="space-y-3">
                {results.results.map((result, i) => {
                  const pct = Math.round(result.score * 100);
                  const barColor =
                    result.score >= 0.75
                      ? 'bg-emerald-500'
                      : result.score >= 0.5
                        ? 'bg-amber-500'
                        : 'bg-neutral-500';
                  const textColor =
                    result.score >= 0.75
                      ? 'text-emerald-400'
                      : result.score >= 0.5
                        ? 'text-amber-400'
                        : 'text-neutral-400';

                  return (
                    <div
                      key={i}
                      className="p-5 rounded-xl bg-white/[0.04] backdrop-blur-md border border-white/[0.08] hover:border-white/[0.18] hover:bg-white/[0.06] shadow-lg shadow-black/20 transition-all duration-300"
                    >
                      <div className="flex items-start justify-between gap-4 mb-3">
                        <div>
                          <h4 className="text-sm font-semibold text-white mb-1.5">
                            {result.signature}
                          </h4>
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-neutral-300">
                            <span className="flex items-center gap-1.5">
                              <Calendar className="w-3 h-3" />
                              {result.judgment_date}
                            </span>
                            {result.court_name && (
                              <span className="flex items-center gap-1.5">
                                <Building2 className="w-3 h-3" />
                                {result.court_name}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="flex-shrink-0 w-16">
                          <span className={`block text-xs font-medium tabular-nums text-right ${textColor}`}>
                            {pct}%
                          </span>
                          <div className="mt-1 h-1 w-full rounded-full bg-white/[0.08] overflow-hidden">
                            <div
                              className={`h-full rounded-full ${barColor} transition-all duration-500`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {result.court_type && COURT_TYPES[result.court_type] && (
                          <span className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-md bg-white/[0.06] text-neutral-400 border border-white/[0.1]">
                            <Building2 className="w-2.5 h-2.5" />
                            {COURT_TYPES[result.court_type]}
                          </span>
                        )}
                        {result.judgment_type && JUDGMENT_TYPES[result.judgment_type] && (
                          <span className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-md bg-white/[0.06] text-neutral-400 border border-white/[0.1]">
                            <FileText className="w-2.5 h-2.5" />
                            {JUDGMENT_TYPES[result.judgment_type]}
                          </span>
                        )}
                        {result.judges && result.judges.length > 0 && (
                          <span className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-md bg-white/[0.06] text-neutral-400 border border-white/[0.1]">
                            <Users className="w-2.5 h-2.5" />
                            {result.judges.slice(0, 2).join(', ')}
                            {result.judges.length > 2 && ` +${result.judges.length - 2}`}
                          </span>
                        )}
                      </div>

                      <p className="text-sm text-neutral-300 leading-relaxed mb-3 line-clamp-3">
                        {result.matched_chunk}
                      </p>

                      <button
                        onClick={() => handleShowFull(result.origin_id)}
                        disabled={loadingJudgment}
className="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-100 hover:text-white hover:underline underline-offset-4 transition-colors"                      >
                        Pokaż pełną treść
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Modal */}
      {selectedJudgment && (
        <div className="fixed inset-0 z-50 flex items-end justify-center pb-4 sm:pb-6">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm modal-overlay" 
            onClick={() => setSelectedJudgment(null)} 
          />
          <div className="modal-panel relative w-full sm:max-w-5xl sm:mx-4 max-h-[calc(100vh-80px)] rounded-2xl bg-black/60 backdrop-blur-xl border border-white/[0.1] overflow-hidden flex flex-col shadow-2xl shadow-black/40">
            <div className="modal-header flex-shrink-0 sticky top-0 bg-black/40 backdrop-blur-xl border-b border-white/[0.08]">
              <div className="flex items-start justify-between p-6">
                <div>
                  <h2 className="text-base font-semibold text-white">{selectedJudgment.signature}</h2>
                  <p className="text-xs text-neutral-500 mt-1.5 flex items-center gap-2">
                    <Calendar className="w-3 h-3" />
                    {selectedJudgment.judgment_date}
                    <span className="text-neutral-700">·</span>
                    {COURT_TYPES[selectedJudgment.court_type] || selectedJudgment.court_type}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedJudgment(null)}
                  className="w-9 h-9 rounded-lg bg-white/[0.06] hover:bg-white/[0.12] flex items-center justify-center transition-colors"
                >
                  <X className="w-4 h-4 text-neutral-400" />
                </button>
              </div>
            </div>
            <div className="modal-body flex-1 overflow-y-auto p-6">
              <p className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap">
                {selectedJudgment.text}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}