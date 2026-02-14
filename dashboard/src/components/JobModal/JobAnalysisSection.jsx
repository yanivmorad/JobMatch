import React from 'react';
import { Lightbulb, FileText, ChevronDown, Sparkles } from 'lucide-react';

const JobAnalysisSection = ({ job, showFullSummary, setShowFullSummary, showFullAnalysis, setShowFullAnalysis }) => {
  return (
    <>
      {/* RECOMMENDATION HERO */}
      <div className="bg-gradient-to-br from-amber-400 via-amber-500 to-amber-600 rounded-3xl p-6 md:p-8 flex items-center gap-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-40 h-40 bg-white/10 rounded-full -translate-y-20 translate-x-20 blur-2xl"></div>
        <div className="p-4 bg-white/20 rounded-2xl backdrop-blur-sm shrink-0">
          <Lightbulb size={32} className="text-white" />
        </div>
        <div className="relative z-10">
          <span className="text-[10px] font-black text-white/70 uppercase tracking-widest block mb-1">המלצה</span>
          <p className="text-xl md:text-2xl font-black text-white leading-tight">
            {job.recommendation}
          </p>
        </div>
      </div>

      {/* JOB SUMMARY */}
      <div className="bg-white rounded-3xl p-6 md:p-8 border border-slate-200 shadow-sm transition-all">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-50 rounded-lg">
            <FileText size={18} className="text-blue-600" />
          </div>
          <h2 className="text-lg font-black text-slate-900">סיכום המשרה</h2>
        </div>
        <div className="relative">
          <p className={`text-slate-700 text-lg leading-relaxed transition-all duration-300 ${!showFullSummary ? 'line-clamp-3' : ''}`}>
            {job.job_summary_hebrew}
          </p>
          <button 
            onClick={() => setShowFullSummary(!showFullSummary)}
            className="mt-3 text-blue-600 hover:text-blue-700 font-bold text-sm flex items-center gap-1 transition-colors"
          >
            {showFullSummary ? 'הצג פחות' : 'המשך קריאה...'}
            <ChevronDown size={14} className={`transition-transform duration-300 ${showFullSummary ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </div>

      {/* DETAILED ANALYSIS */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-8 py-5 bg-gradient-to-br from-slate-50 to-white border-b border-slate-100 flex items-center gap-3">
          <div className="p-2 bg-indigo-50 rounded-lg">
            <Sparkles size={18} className="text-indigo-600" />
          </div>
          <h2 className="text-lg font-black text-slate-900">ניתוח התאמה מפורט</h2>
        </div>
        <div className="p-8 relative">
          <div className={`text-slate-700 text-base leading-relaxed whitespace-pre-line transition-all duration-500 ${!showFullAnalysis ? 'max-h-[250px] overflow-hidden' : ''}`}>
            {job.formatted_message}
          </div>
          {!showFullAnalysis && (
            <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white via-white/80 to-transparent pointer-events-none"></div>
          )}
          <div className="flex justify-center mt-4">
            <button 
              onClick={() => setShowFullAnalysis(!showFullAnalysis)} 
              className="px-6 py-2.5 bg-slate-900 hover:bg-black text-white rounded-full text-sm font-bold flex items-center gap-2 transition-all shadow-md hover:shadow-lg active:scale-95"
            >
              {showFullAnalysis ? 'הצג פחות' : 'קרא את הניתוח המלא'}
              <ChevronDown size={14} className={`transition-transform duration-300 ${showFullAnalysis ? 'rotate-180' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default JobAnalysisSection;
