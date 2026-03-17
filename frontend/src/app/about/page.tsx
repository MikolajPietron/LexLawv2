import type { Metadata } from 'next';
import { 
  BrainCircuit, 
  Search, 
  Zap, 
  Scale,
  Database,
  Clock,
  Server,
  Bot
} from 'lucide-react';

export const metadata: Metadata = {
  title: "O Lexara | AI Legal Search Engine",
  description: "Lexara is an advanced AI-powered legal search engine for Polish court rulings. Using RAG technology, we provide instant, context-aware answers to complex legal questions.",
  keywords: ["legal technology", "AI law", "Polish court rulings", "semantic search", "RAG", "Lexara", "legal research"],
};

export default function AboutPage() {
  return (
    <div className="min-h-screen relative font-sans text-white">
      {/* Background */}
      <div
        className="fixed inset-0 bg-[url('/bgimg.jpg')] bg-cover bg-center"
        style={{ filter: 'blur(8px) brightness(0.4)', transform: 'scale(1.1)' }}
      />
      
      <main className="relative z-10 min-h-screen flex flex-col items-center pt-32 px-4 sm:px-6 pb-20">
        
        {/* Hero */}
        <section className="text-center mb-20 max-w-3xl relative">
          <div className="absolute -top-20 left-1/2 -translate-x-1/2 w-64 h-64 bg-[#e05929]/15 rounded-full blur-3xl pointer-events-none" />
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.06] border border-white/[0.1] text-xs font-medium text-neutral-400 uppercase tracking-widest mb-8">
            <Scale className="w-3.5 h-3.5 text-[#e05929]" />
            O platformie
          </div>
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-6 tracking-tight" style={{ fontFamily: "'Agrandir WideLight', sans-serif", letterSpacing: '0.05em' }}>
            Nowa era wyszukiwania
            <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#e05929] to-[#ff8a65]">orzeczeń sądowych</span>
          </h1>
          <p className="text-base sm:text-lg text-neutral-400 leading-relaxed max-w-2xl mx-auto">
            Lexara łączy zaawansowany AI z milionami polskich orzeczeń, 
            aby dostarczyć precyzyjne odpowiedzi na złożone pytania prawne w sekundach.
          </p>
        </section>

        {/* Feature Grid */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 w-full max-w-5xl mb-20">
          <FeatureCard 
            icon={<BrainCircuit className="w-6 h-6" />}
            color="text-[#e05929]"
            bgColor="bg-[#e05929]/10 border-[#e05929]/20"
            title="Rozumienie semantyczne"
            description="W przeciwieństwie do tradycyjnych wyszukiwarek, Lexara rozumie intencje stojące za zapytaniem dzięki embeddingom wektorowym i dużym modelom językowym."
          />
          <FeatureCard 
            icon={<Search className="w-6 h-6" />}
            color="text-blue-400"
            bgColor="bg-blue-500/10 border-blue-500/20"
            title="Ogromna baza danych"
            description="Dostęp do milionów orzeczeń sądów powszechnych, Sądu Najwyższego i Trybunału Konstytucyjnego w milisekundach."
          />
          <FeatureCard 
            icon={<Zap className="w-6 h-6" />}
            color="text-amber-400"
            bgColor="bg-amber-500/10 border-amber-500/20"
            title="Natychmiastowe odpowiedzi"
            description="Generowanie bezpośrednich odpowiedzi na podstawie powiązanych orzeczeń, wraz z cytatami i odnośnikami."
          />
        </section>

        {/* How it works */}
        <section className="w-full max-w-5xl mb-20">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3 tracking-tight">Jak to działa?</h2>
            <p className="text-neutral-500 text-sm">Trzy kroki od pytania do odpowiedzi</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
            <StepCard 
              step="01"
              title="Zadaj pytanie"
              description="Wpisz swoje zapytanie prawne w języku naturalnym — tak jak pytasz prawnika."
            />
            <StepCard 
              step="02"
              title="AI analizuje"
              description="System optymalizuje zapytanie, przeszukuje bazę wektorową i znajduje najlepiej pasujące orzeczenia."
            />
            <StepCard 
              step="03"
              title="Otrzymaj odpowiedź"
              description="Dostajesz syntetyczną odpowiedź AI oraz listę orzeczeń z ich treścią i oceną trafności."
            />
          </div>
        </section>

        {/* Mission */}
        <section className="w-full max-w-5xl rounded-2xl sm:rounded-3xl p-[1px] bg-gradient-to-b from-white/[0.12] to-transparent mb-20">
          <div className="bg-black/50 backdrop-blur-xl rounded-[15px] sm:rounded-[23px] p-6 sm:p-10 md:p-14">
            <div className="flex flex-col md:flex-row items-start gap-8 md:gap-12">
              <div className="flex-1 space-y-5">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#e05929]/10 border border-[#e05929]/20 text-xs font-medium text-[#e05929] uppercase tracking-widest">
                  Nasza misja
                </div>
                <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                  Demokratyzacja dostępu do wiedzy prawnej
                </h2>
                <p className="text-neutral-400 leading-relaxed">
                  Badanie prawa zawsze było czasochłonne i kosztowne. 
                  Naszą misją jest budowanie narzędzi, które są wydajne, precyzyjne i łatwe w użyciu — 
                  tak aby każdy mógł poruszać się w polskim systemie prawnym z pewnością.
                </p>
                <p className="text-neutral-400 leading-relaxed">
                  Niezależnie od tego, czy jesteś prawnikiem, studentem, czy przedsiębiorcą — 
                  Lexara daje Ci narzędzia do szybkiego i pewnego odnalezienia potrzebnych orzeczeń.
                </p>
              </div>
              <div className="flex-shrink-0 hidden md:flex items-center justify-center w-48">
                <div className="relative">
                  <div className="absolute inset-0 bg-gradient-to-tr from-[#e05929]/20 to-blue-500/10 rounded-full blur-3xl scale-150" />
                  <Scale className="w-32 h-32 text-white/[0.07] relative" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="w-full max-w-5xl">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
            <StatCard icon={<Database className="w-4 h-4" />} value="2M+" label="Przeanalizowanych orzeczeń" />
            <StatCard icon={<Server className="w-4 h-4" />} value="99%" label="Dostępność" />
            <StatCard icon={<Clock className="w-4 h-4" />} value="<2s" label="Średni czas wyszukiwania" />
            <StatCard icon={<Bot className="w-4 h-4" />} value="24/7" label="Dostępność AI" />
          </div>
        </section>

      </main>
    </div>
  );
}

function FeatureCard({ icon, color, bgColor, title, description }: { 
  icon: React.ReactNode; color: string; bgColor: string; title: string; description: string 
}) {
  return (
    <div className="group rounded-2xl p-[1px] bg-gradient-to-b from-white/[0.08] to-transparent hover:from-white/[0.15] transition-all duration-300">
      <div className="h-full bg-black/40 backdrop-blur-xl rounded-[15px] p-6 sm:p-7 border border-white/[0.04]">
        <div className={`mb-4 p-2.5 rounded-xl ${bgColor} border w-fit ${color}`}>
          {icon}
        </div>
        <h3 className="text-base font-semibold text-white mb-2">{title}</h3>
        <p className="text-sm text-neutral-400 leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

function StepCard({ step, title, description }: { step: string; title: string; description: string }) {
  return (
    <div className="relative rounded-2xl bg-white/[0.03] backdrop-blur-md border border-white/[0.06] p-6 sm:p-7 hover:bg-white/[0.06] hover:border-white/[0.12] transition-all duration-300">
      <span className="text-4xl sm:text-5xl font-bold text-white/[0.04] absolute top-4 right-5 select-none">{step}</span>
      <div className="relative">
        <div className="w-8 h-8 rounded-lg bg-[#e05929]/10 border border-[#e05929]/20 flex items-center justify-center mb-4">
          <span className="text-xs font-bold text-[#e05929]">{step}</span>
        </div>
        <h3 className="text-base font-semibold text-white mb-2">{title}</h3>
        <p className="text-sm text-neutral-400 leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

function StatCard({ icon, value, label }: { icon: React.ReactNode; value: string; label: string }) {
  return (
    <div className="rounded-2xl bg-white/[0.03] backdrop-blur-md border border-white/[0.06] p-5 sm:p-6 text-center hover:bg-white/[0.06] hover:border-white/[0.1] transition-all duration-300">
      <div className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-white/[0.06] text-neutral-500 mb-3">
        {icon}
      </div>
      <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{value}</div>
      <div className="text-xs font-medium text-neutral-500 uppercase tracking-wider">{label}</div>
    </div>
  );
}