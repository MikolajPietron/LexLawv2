'use client';

import { useState, useRef, useEffect } from 'react';
import { searchRulings, getFullJudgment, SearchResponse, FullJudgment } from '../../lib/api';
import { 
  ArrowUp, 
  ChevronRight, 
  X, 
  Building2,
  FileText,
  Clock,
  Wand2,
  Users
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

interface Message {
  type: 'user' | 'results';
  content: string;
  results?: SearchResponse;
  timestamp: Date;
}

function Loader() {
  return (
    <div className="flex items-center gap-3 py-1">
      <div className="h-4 w-4 border-2 border-neutral-700 border-t-violet-500 rounded-full animate-spin" />
      <span className="text-neutral-400 text-sm">Przeszukuję bazę orzeczeń...</span>
    </div>
  );
}

export default function Home() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedJudgment, setSelectedJudgment] = useState<FullJudgment | null>(null);
  const [loadingJudgment, setLoadingJudgment] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage: Message = {
      type: 'user',
      content: query,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    const currentQuery = query;
    setQuery('');
    setLoading(true);

    try {
      const data = await searchRulings(currentQuery, 5, true);
      setMessages(prev => [...prev, {
        type: 'results',
        content: `${data.results.length} wyników`,
        results: data,
        timestamp: new Date(),
      }]);
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

  const hasMessages = messages.length > 0;

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white">
      {/* Header with gradient border */}
      <header className="fixed top-0 left-0 right-0 z-40 bg-[#0A0A0A]">
        <div className="h-14 px-6 flex items-center justify-between max-w-screen-xl mx-auto">
          <h1 className="text-lg font-semibold tracking-tight">
            Lex<span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">Search</span>
          </h1>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 text-[11px] text-neutral-400">
            <Wand2 className="w-3 h-3" />
            <span>AI Search</span>
          </div>
        </div>
        {/* Gradient line */}
        <div className="h-px bg-gradient-to-r from-transparent via-violet-500/50 to-transparent" />
      </header>

      {/* Main */}
      <main className="pt-14 min-h-screen flex flex-col">
        {!hasMessages ? (
          /* Welcome State */
          <div className="flex-1 flex flex-col items-center justify-center px-4 pb-24">
            {/* Gradient glow behind title */}
            <div className="relative mb-6">
              <div className="absolute inset-0 blur-3xl opacity-30 bg-gradient-to-r from-violet-600 to-fuchsia-600 rounded-full scale-150" />
              <h2 className="relative text-4xl font-bold tracking-tight bg-gradient-to-b from-white to-neutral-400 bg-clip-text text-transparent">
                Czego szukasz?
              </h2>
            </div>
            
            <p className="text-neutral-500 text-sm mb-10 text-center max-w-md">
              Przeszukuj polskie orzeczenia sądowe używając naturalnego języka
            </p>

            {/* Input with gradient border */}
            <form onSubmit={handleSearch} className="w-full max-w-xl mb-8">
              <div className="relative group">
                {/* Gradient border effect */}
                <div className="absolute -inset-[1px] rounded-xl bg-gradient-to-r from-violet-600/50 via-fuchsia-600/50 to-violet-600/50 opacity-0 group-focus-within:opacity-100 blur-sm transition-opacity duration-500" />
                <div className="absolute -inset-[1px] rounded-xl bg-gradient-to-r from-violet-600 via-fuchsia-600 to-violet-600 opacity-0 group-focus-within:opacity-100 transition-opacity duration-500" />
                
                <div className="relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="np. odszkodowanie za wypadek przy pracy..."
                    className="w-full h-14 px-5 pr-14 rounded-xl bg-[#141414] border border-neutral-800 text-white placeholder:text-neutral-600 focus:outline-none focus:border-transparent transition-colors"
                  />
                  <button
                    type="submit"
                    disabled={!query.trim()}
                    className="absolute right-2 top-2 h-10 w-10 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
                  >
                    <ArrowUp className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </form>

            {/* Suggestions */}
            <div className="flex flex-wrap justify-center gap-2">
              {[
                'Oszustwo kredytowe',
                'Alimenty na dziecko',
                'Wypadek przy pracy',
                'Umowa o pracę'
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setQuery(s);
                    inputRef.current?.focus();
                  }}
                  className="px-4 py-2 text-sm rounded-lg bg-white/5 text-neutral-400 hover:text-white hover:bg-white/10 border border-transparent hover:border-neutral-800 transition-all duration-200"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Chat State */
          <>
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-screen-lg mx-auto px-4 py-6 space-y-8">
                {messages.map((msg, idx) => (
                  <div key={idx}>
                    {msg.type === 'user' ? (
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center text-xs font-semibold flex-shrink-0">
                          U
                        </div>
                        <div className="pt-1.5">
                          <p className="text-[15px] text-white leading-relaxed">{msg.content}</p>
                        </div>
                      </div>
                    ) : msg.results && (
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-full bg-[#1A1A1A] border border-neutral-800 flex items-center justify-center flex-shrink-0">
                          <span className="text-sm">⚖️</span>
                        </div>
                        <div className="flex-1 min-w-0 pt-1">
                          <div className="mb-4">
                            <span className="text-[15px] text-white">Znaleziono {msg.results.results.length} orzeczeń</span>
                            <span className="inline-flex items-center gap-1.5 ml-3 text-xs text-violet-400">
                              <Wand2 className="w-3 h-3" />
                              {msg.results.optimized_query}
                            </span>
                          </div>

                          <div className="space-y-3">
                            {msg.results.results.map((result, i) => (
                              <div
                                key={i}
                                className="group p-4 rounded-xl bg-[#111111] border border-neutral-800/50 hover:border-neutral-700 transition-all duration-200"
                              >
                                <div className="flex items-start justify-between gap-4 mb-3">
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-2.5 mb-1.5">
                                      <h3 className="text-sm font-medium text-white">
                                        {result.signature}
                                      </h3>
                                      <span className="text-xs px-2 py-0.5 rounded-full bg-gradient-to-r from-violet-500/20 to-fuchsia-500/20 text-violet-300 border border-violet-500/20 tabular-nums">
                                        {result.score.toFixed(2)}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-neutral-500">
                                      <Clock className="w-3 h-3" />
                                      <span>{result.judgment_date}</span>
                                      <span className="text-neutral-700">•</span>
                                      <span>{result.court_name || COURT_TYPES[result.court_type]}</span>
                                    </div>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2 mb-3">
                                  {result.court_type && COURT_TYPES[result.court_type] && (
                                    <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-white/5 text-neutral-400">
                                      <Building2 className="w-3 h-3" />
                                      {COURT_TYPES[result.court_type]}
                                    </span>
                                  )}
                                  {result.judgment_type && JUDGMENT_TYPES[result.judgment_type] && (
                                    <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-white/5 text-neutral-400">
                                      <FileText className="w-3 h-3" />
                                      {JUDGMENT_TYPES[result.judgment_type]}
                                    </span>
                                  )}
                                  {result.judges && result.judges.length > 0 && (
                                  <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-white/5 text-neutral-400">
                                    <Users className="w-3 h-3" />
                                    <span>
                                      {`Skład sędziowski: ` + "  "}
                                      {" " +result.judges.slice(0, 3).join(', ')}
                                      {result.judges.length > 3 && ` (+${result.judges.length - 3})`}
                                    </span>
                                  </span>
                                  )}
                                </div>

                               

                                <p className="text-sm text-neutral-400 line-clamp-2 mb-4 leading-relaxed">
                                  {result.matched_chunk}
                                </p>

                                <button
                                  onClick={() => handleShowFull(result.origin_id)}
                                  disabled={loadingJudgment}
                                  className="inline-flex items-center gap-1 text-xs font-medium text-violet-400 hover:text-violet-300 transition-colors"
                                >
                                  Pełna treść
                                  <ChevronRight className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}

                {loading && (
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-[#1A1A1A] border border-neutral-800 flex items-center justify-center flex-shrink-0">
                      <span className="text-sm">⚖️</span>
                    </div>
                    <div className="pt-1.5">
                      <Loader />
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Bottom Input */}
            <div className="sticky bottom-0 bg-gradient-to-t from-[#0A0A0A] via-[#0A0A0A] to-transparent pt-6 pb-4 px-4">
              <form onSubmit={handleSearch} className="max-w-screen-lg mx-auto">
                <div className="relative">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Następne pytanie..."
                    className="w-full h-12 px-4 pr-12 rounded-xl bg-[#141414] border border-neutral-800 text-white text-sm placeholder:text-neutral-600 focus:outline-none focus:border-violet-500/50 transition-colors"
                  />
                  <button
                    type="submit"
                    disabled={loading || !query.trim()}
                    className="absolute right-1.5 top-1.5 h-9 w-9 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
                  >
                    <ArrowUp className="w-4 h-4" />
                  </button>
                </div>
              </form>
            </div>
          </>
        )}
      </main>

      {/* Modal */}
      {selectedJudgment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-black/80 backdrop-blur-sm" 
            onClick={() => setSelectedJudgment(null)} 
          />
          <div className="relative w-full max-w-2xl max-h-[85vh] rounded-2xl bg-[#111111] border border-neutral-800 overflow-hidden flex flex-col">
            {/* Modal header with gradient accent */}
            <div className="relative">
              <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-violet-500/50 to-transparent" />
              <div className="flex items-center justify-between px-6 py-4">
                <div>
                  <h2 className="text-base font-medium text-white">{selectedJudgment.signature}</h2>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    {selectedJudgment.judgment_date} • {COURT_TYPES[selectedJudgment.court_type] || selectedJudgment.court_type}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedJudgment(null)}
                  className="w-8 h-8 rounded-lg hover:bg-white/5 flex items-center justify-center transition-colors"
                >
                  <X className="w-4 h-4 text-neutral-400" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-6 pb-6">
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