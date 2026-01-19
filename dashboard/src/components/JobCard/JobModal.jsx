import React, { useState } from 'react';
import { 
  X, ExternalLink, Send, XCircle, FileText, Lightbulb, 
  AlertCircle, TrendingUp, Target, Building2, Calendar, ChevronDown, ChevronUp, Sparkles, Link2
} from 'lucide-react';

const JobModal = ({ job, onClose, onAction }) => {
  const [showFullDesc, setShowFullDesc] = useState(false);
  
  const isManual = job.url?.startsWith('manual-') || !job.url?.includes('http');

  const getScoreColor = (score) => {
    if (score >= 80) return { bg: 'bg-emerald-500', text: 'text-emerald-600', border: 'border-emerald-100', lightBg: 'bg-emerald-50' };
    if (score >= 50) return { bg: 'bg-amber-500', text: 'text-amber-600', border: 'border-amber-100', lightBg: 'bg-amber-50' };
    return { bg: 'bg-rose-500', text: 'text-rose-600', border: 'border-rose-100', lightBg: 'bg-rose-50' };
  };

  const suitability = getScoreColor(job.suitability_score);
  const probability = getScoreColor(job.acceptance_probability);

  return (
    <div 
      className="fixed inset-0 bg-slate-900/60 backdrop-blur-lg flex items-center justify-center z-[100] p-4 md:p-8 animate-in fade-in duration-300 cursor-pointer" 
      dir="rtl"
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-[2rem] max-w-5xl w-full max-h-[90vh] overflow-hidden shadow-[0_40px_100px_-20px_rgba(0,0,0,0.25)] flex flex-col border border-slate-100"
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* Header עם אזור בטוח מהאיקס */}
        <div className="relative p-8 md:p-10 bg-white border-b border-slate-50">
          {/* איקס מינימליסטי ושקוף - מודגש רק ב-hover */}
          <button 
            onClick={onClose} 
            className="absolute top-6 left-6 p-2.5 bg-white/60 hover:bg-white/90 text-slate-400 hover:text-slate-900 rounded-full transition-all z-20 border border-slate-200/50 shadow-sm backdrop-blur-sm opacity-50 hover:opacity-100"
            aria-label="סגור"
          >
            <X size={20} />
          </button>

          <div className="flex flex-col md:flex-row justify-between items-start gap-8 md:pl-20">
            <div className="space-y-4 flex-1">
              <div className="flex items-center gap-2 text-blue-600 font-bold text-sm bg-blue-50 px-3 py-1.5 rounded-full w-fit">
                <Building2 size={16} />
                <span>{job.company}</span>
              </div>
              <h2 className="text-3xl md:text-4xl font-black text-slate-900 leading-tight tracking-tight">
                {job.job_title}
              </h2>
              <div className="flex items-center gap-4 text-slate-500 text-sm font-medium pt-1 flex-wrap">
                <span className="flex items-center gap-1.5"><Calendar size={14} /> {new Date(job.analyzed_at).toLocaleDateString('he-IL')}</span>
                {!isManual && <span className="flex items-center gap-1.5 text-blue-500/80"><Link2 size={14} /> משרה מקישור חיצוני</span>}
              </div>
            </div>

            {/* ציונים עם רקע מוסט וז-אינדקס */}
            <div className="flex gap-4 self-center md:self-start bg-white/70 backdrop-blur-sm rounded-2xl p-2 z-10">
              <div className={`rounded-2xl p-4 min-w-[120px] text-center border ${suitability.border} ${suitability.lightBg} shadow-sm transition-transform hover:scale-[1.02]`}>
                <div className={`text-[11px] font-bold uppercase mb-1 ${suitability.text} opacity-80`}>התאמה</div>
                <div className={`text-3xl font-black ${suitability.text}`}>{job.suitability_score}%</div>
              </div>
              <div className={`rounded-2xl p-4 min-w-[120px] text-center border ${probability.border} ${probability.lightBg} shadow-sm transition-transform hover:scale-[1.02]`}>
                <div className={`text-[11px] font-bold uppercase mb-1 ${probability.text} opacity-80`}>סיכוי</div>
                <div className={`text-3xl font-black ${probability.text}`}>{job.acceptance_probability}%</div>
              </div>
            </div>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto bg-[#fafbfc] custom-scrollbar">
          <div className="p-8 md:p-12 space-y-14 max-w-4xl mx-auto">
            
            {/* ניתוח AI */}
            <section className="space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-lg shadow-blue-100">
                  <Sparkles className="text-white" size={20} />
                </div>
                <h3 className="text-2xl font-black text-slate-800 tracking-tight">ניתוח מקצועי מה-AI</h3>
              </div>
              <div className="bg-white rounded-[2rem] p-8 md:p-10 border border-slate-100 shadow-sm leading-[1.9] text-slate-600 text-lg font-medium">
                {job.formatted_message}
              </div>
            </section>

            {/* חסמים ופערים */}
            <div className="grid md:grid-cols-2 gap-8">
              <section className="bg-white rounded-[2rem] p-8 border border-slate-100 shadow-sm space-y-6 transition-all hover:shadow-md">
                <div className="flex items-center gap-2.5 text-rose-600 font-black text-lg">
                  <AlertCircle size={22} />
                  <span>חסמים קריטיים</span>
                </div>
                <div className="space-y-4">
                  {job.showstoppers.map((item, i) => (
                    <div key={i} className="flex gap-3 text-slate-600 text-base leading-relaxed">
                      <span className="w-2 h-2 rounded-full bg-rose-400 mt-2 shrink-0" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="bg-white rounded-[2rem] p-8 border border-slate-100 shadow-sm space-y-6 transition-all hover:shadow-md">
                <div className="flex items-center gap-2.5 text-indigo-600 font-black text-lg">
                  <TrendingUp size={22} />
                  <span>פערי ידע לגישור</span>
                </div>
                <div className="space-y-4">
                  {job.gap_analysis.map((item, i) => (
                    <div key={i} className="flex gap-3 text-slate-600 text-base leading-relaxed">
                      <span className="w-2 h-2 rounded-full bg-indigo-400 mt-2 shrink-0" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            {/* טיפ זהב */}
            <section className="bg-gradient-to-r from-amber-50/60 to-amber-50/40 rounded-3xl p-8 border border-amber-100 flex gap-6 items-start transition-all hover:shadow-md">
              <div className="bg-amber-100 p-3.5 rounded-2xl text-amber-600 shrink-0 shadow-sm">
                <Lightbulb size={28} />
              </div>
              <div className="space-y-2 flex-1">
                <h4 className="font-black text-amber-900 text-lg tracking-tight">טיפ אסטרטגי להגשה</h4>
                <p className="text-amber-900/80 leading-relaxed italic font-medium text-xl">
                  "{job.recommendation}"
                </p>
              </div>
            </section>

            {/* פרטי משרה */}
            <section className="pt-4 pb-12">
              <button 
                onClick={() => setShowFullDesc(!showFullDesc)}
                className="w-full flex items-center justify-between p-6 bg-white border border-slate-200 rounded-2xl hover:bg-slate-50 transition-all font-bold text-slate-700 shadow-sm hover:shadow-md"
              >
                <div className="flex items-center gap-3">
                  <FileText size={20} className="text-slate-400" />
                  <span>{isManual ? 'לפרטי המשרה המלאים (טקסט מקורי)' : 'צפה בתקציר ופרטים נוספים'}</span>
                </div>
                <span className={`transform transition-transform ${showFullDesc ? 'rotate-180' : ''}`}>
                  <ChevronDown size={20} />
                </span>
              </button>
              
              {showFullDesc && (
                <div className="mt-4 p-8 bg-slate-50/50 border border-slate-100 rounded-2xl text-slate-600 text-base leading-relaxed whitespace-pre-wrap animate-in slide-in-from-top-4 duration-300">
                  {isManual ? job.full_description : job.job_summary_hebrew}
                </div>
              )}
            </section>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-8 md:p-10 bg-white border-t border-slate-100 flex flex-col md:flex-row gap-5 items-center">
          {!isManual && (
            <a 
              href={job.url} 
              target="_blank" 
              rel="noreferrer"
              className="w-full md:flex-[2.5] bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-black py-6 rounded-2xl transition-all flex items-center justify-center gap-4 shadow-xl shadow-blue-100 text-xl"
            >
              <ExternalLink size={24} />
              <span>הגש מועמדות במקור</span>
            </a>
          )}
          
          <div className="flex gap-4 w-full md:flex-1">
            {job.user_action !== 'applied' && (
              <button 
                onClick={() => onAction('applied')}
                className="flex-1 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white font-black py-6 rounded-2xl transition-all flex items-center justify-center gap-3 shadow-lg shadow-emerald-50 text-lg"
              >
                <Send size={20} />
                <span>שלחתי קו"ח</span>
              </button>
            )}
            {job.user_action !== 'rejected' && (
              <button 
                onClick={() => onAction('rejected')}
                className="flex-1 bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700 text-white font-black py-6 rounded-2xl transition-all flex items-center justify-center gap-3 shadow-lg shadow-rose-50 text-lg"
              >
                <XCircle size={20} />
                <span>קיבלתי דחייה</span>
              </button>
            )}
            <button 
              onClick={() => onAction('ignored')}
              className="flex-1 bg-white border-2 border-slate-100 hover:border-slate-200 hover:bg-slate-50 text-slate-400 hover:text-slate-600 font-black py-6 rounded-2xl transition-all flex items-center justify-center gap-3 text-lg"
            >
              <AlertCircle size={20} />
              <span>הסר משרה</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JobModal;