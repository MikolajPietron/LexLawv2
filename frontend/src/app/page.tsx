'use client';

import { useState, useRef } from 'react';
import { searchRulings, getFullJudgment, SearchResponse, FullJudgment } from '../../lib/api';
import ColorBends from '../components/ColorBends';
import Orb from '../components/Orb';
import Prism from '../components/Prism';
import Aurora from '../components/Aurora';
import RippleGrid from '../components/RippleGrid';
import { 
  Search,
  X, 
  Building2,
  FileText,
  Calendar,
  Users,
  ExternalLink,
  Sparkles
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
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedJudgment, setSelectedJudgment] = useState<FullJudgment | null>(null);
  const [loadingJudgment, setLoadingJudgment] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    try {
      const data = await searchRulings(query, 5, true);
      setResults(data);
    } catch (error) {
      console.error(error);
    }
    setLoading(false);
  };

  const handleShowFull = async (originId: number) => {
    setLoadingJudgment(true);
    try {
      const judgment = await getFullJudgment(originId);
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
    <div className="h-full relative">
      <div className="bg-scene" />
      <div className="bg-blobs">
     <div style={{ position: 'absolute', inset: 0 }}>
  <RippleGrid
    enableRainbow={false}
    gridColor="#c084fc"
    rippleIntensity={0.006}
    gridSize={20}
    gridThickness={15}
    mouseInteraction={true}
    mouseInteractionRadius={1.2}
    opacity={0.9}
  />
</div>
       
      </div>
   {/* Background */}


{/* Content */}
<main className={`relative z-10 pt-[60px] min-h-screen flex flex-col ${!hasResults ? 'justify-center' : ''}`}>y
        {/* Hero / Search Section */}
        <div className={`w-full transition-all duration-500 ${hasResults ? 'py-8' : 'py-0 -mt-10'}`}>
          <div className={`mx-auto px-6 ${hasResults ? 'max-w-4xl' : 'max-w-2xl'}`}>

            {/* Hero text — only before results */}
            {!hasResults && (
              <div className="text-center mb-10">
                <h1 className="text-4xl font-semibold text-white tracking-tight mb-3">
                  Wyszukiwarka orzeczeń sądowych
                </h1>
                <p className="text-neutral-500 text-base">
                  Przeszukuj tysiące polskich orzeczeń sądowych za pomocą AI.
                </p>
              </div>
            )}

            {/* Search bar — unchanged */}
            <form onSubmit={handleSearch}>
              <div className="flex items-center gap-3 px-4 py-3 h-18 rounded-2xl bg-neutral-900 border border-offwhite focus-within:border-white transition-colors">
                <Search className="w-6 h-6 text-neutral-500 flex-shrink-0 text-white" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="np. odszkodowanie za wypadek przy pracy..."
                  className="flex-1 bg-transparent text-white text-m placeholder:text-neutral-600 focus:outline-none"
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
            </form>

            {/* Example queries — only before results */}
            {!hasResults && (
              <div className="flex flex-wrap justify-center gap-2 mt-5">
                {EXAMPLE_QUERIES.map((example) => (
                  <button
                    key={example}
                    onClick={() => handleExampleClick(example)}
                    className="text-xs text-neutral-500 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.06] hover:border-white/[0.15] hover:text-neutral-300 transition-all cursor-pointer"
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
                  className="text-xs uppercase tracking-wider text-neutral-600 hover:text-white transition-colors"
                >
                  Nowe wyszukiwanie
                </button>
              </div>

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
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-neutral-500">
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
                        className="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-400 hover:text-[#c084fc] hover:underline underline-offset-4 transition-colors"
                      >
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