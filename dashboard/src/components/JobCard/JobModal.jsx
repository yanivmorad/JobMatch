// src/components/JobCard/JobModal.jsx
import React, { useState } from 'react';
import { 
  X, ExternalLink, Send,   
  AlertCircle, TrendingUp, Sparkles, Clock, Building2, MapPin, ChevronDown, Loader2, RefreshCw,FileText,    
  Lightbulb,   
  Copy         
} from 'lucide-react';

const JobModal = ({ job, onClose, onAction, onDelete, onUpdateStatus, onRetry }) => {
  const [showFullDesc, setShowFullDesc] = useState(false);
  const [isEditing, setIsEditing] = useState(['FAILED_SCRAPE', 'NO_DATA'].includes(job.status));
  const [editTitle, setEditTitle] = useState(job.job_title || '');
  const [editCompany, setEditCompany] = useState(job.company || '');
  const [editDesc, setEditDesc] = useState(job.full_description || '');
  const [isSaving, setIsSaving] = useState(false);
  const [isRescanLoading, setIsRescanLoading] = useState(false);
  const [showFullAnalysis, setShowFullAnalysis] = useState(false);
  const [showFullSummary, setShowFullSummary] = useState(false);

  const isManual = job.url?.startsWith('manual-') || !job.url?.includes('http');

  const getScoreColor = (score) => {
    if (score >= 80) return { text: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-200", fill: "bg-emerald-500" };
    if (score >= 50) return { text: "text-amber-600", bg: "bg-amber-50", border: "border-amber-200", fill: "bg-amber-500" };
    return { text: "text-rose-600", bg: "bg-rose-50", border: "border-rose-200", fill: "bg-rose-500" };
  };

  const getScoreStyle = (score) => {
    const s = getScoreColor(score);
    return `${s.border} ${s.text} ${s.bg}`;
  };

  const handleSave = async () => {
    if (!editTitle || !editCompany || !editDesc) {
      alert("נא למלא את כל השדות");
      return;
    }
    setIsSaving(true);
    const success = await onAction(job, 'manual_update', {
      title: editTitle,
      company: editCompany,
      description: editDesc
    });
    if (success) setIsEditing(false);
    setIsSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-[100] p-2 md:p-6 animate-in fade-in duration-300" dir="rtl" onClick={onClose}>
      <div className="bg-slate-50 rounded-[2rem] w-full max-w-6xl max-h-[95vh] overflow-hidden shadow-2xl flex flex-col border border-white/20 animate-in zoom-in-95" onClick={(e) => e.stopPropagation()}>
        
        {/* --- Header: ניקיון ופוקוס --- */}
        <div className="px-8 py-5 bg-white border-b border-slate-200 flex justify-between items-center transition-all">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <Building2 size={14} className="shrink-0" />
              <span className="text-xs font-bold uppercase truncate">{isEditing ? 'מצב עריכה' : (job.company || 'חברה לא ידועה')}</span>
              {job.location && (
                <>
                  <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                  <MapPin size={14} className="shrink-0" />
                  <span className="text-xs font-bold uppercase truncate">{job.location}</span>
                </>
              )}
            </div>
            {isEditing ? (
              <div className="flex gap-2 max-w-xl">
                <input className="text-xl font-bold text-slate-900 border-b-2 border-blue-500 outline-none w-full bg-blue-50/30 px-2 py-1" value={editTitle} onChange={e => setEditTitle(e.target.value)} placeholder="כותרת המשרה" />
              </div>
            ) : (
              <h2 className="text-2xl font-black text-slate-900 tracking-tight leading-none truncate">{job.job_title || job.url}</h2>
            )}
          </div>

          <div className="flex items-center gap-3 mr-4">
            <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-all">
              <X size={24} />
            </button>
          </div>
        </div>

        {/* --- Content Area --- */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 md:p-8 bg-slate-50/30">
          {isEditing ? (
            <section className="space-y-6 max-w-4xl mx-auto py-4">
              <div className="bg-white rounded-[1.5rem] shadow-sm border border-slate-200 overflow-hidden">
                <textarea 
                  className="w-full h-[50vh] p-8 bg-transparent outline-none text-slate-800 text-lg leading-relaxed resize-none"
                  value={editDesc} 
                  onChange={e => setEditDesc(e.target.value)} 
                  placeholder="הדבק כאן את תוכן המשרה..."
                />
              </div>
              <button onClick={handleSave} disabled={isSaving} className="w-full py-4 bg-blue-600 text-white rounded-xl font-black text-xl hover:bg-blue-700 transition-all shadow-lg active:scale-95 disabled:opacity-50 flex items-center justify-center gap-3">
                {isSaving ? <Loader2 className="animate-spin" /> : <Sparkles size={24} />} שמור ונתח משרה
              </button>
            </section>
          ) : (
            <div className="max-w-7xl mx-auto">
              
              {/* Top Dashboard: Decision Cards */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-5 mb-6">
                
                {/* Score Indicators - 5 columns */}
                <div className="md:col-span-5 grid grid-cols-2 gap-4">
                  {[
                    { label: "התאמה", val: job.suitability_score },
                    { label: "סיכוי", val: job.acceptance_probability }
                  ].map((s, i) => {
                    const style = getScoreColor(s.val);
                    return (
                      <div key={i} className={`bg-white rounded-3xl p-5 border border-slate-200 shadow-sm flex flex-col items-center justify-between relative overflow-hidden group`}>
                         <div className={`absolute bottom-0 left-0 h-1 transition-all duration-1000 ${style.fill}`} style={{ width: `${s.val}%` }}></div>
                         <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">{s.label}</span>
                         <div className="relative">
                            <span className={`text-4xl font-black ${style.text}`}>{s.val}%</span>
                         </div>
                         <div className="w-full h-1.5 bg-slate-100 rounded-full mt-3 overflow-hidden">
                            <div className={`h-full transition-all duration-1000 ${style.fill}`} style={{ width: `${s.val}%` }}></div>
                         </div>
                      </div>
                    );
                  })}
                </div>

                {/* Recommendation Hero - 7 columns */}
                <div className="md:col-span-7 bg-gradient-to-br from-amber-400 to-amber-500 rounded-3xl p-6 flex items-center gap-6 shadow-xl shadow-amber-200/40 relative overflow-hidden text-white">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -translate-y-16 translate-x-16 blur-xl"></div>
                  <div className="p-4 bg-white/20 rounded-2xl backdrop-blur-md">
                     <Lightbulb size={32} className="text-amber-950" />
                  </div>
                  <div className="flex-1">
                    <span className="text-[10px] font-black text-amber-950/60 uppercase tracking-widest block mb-1">השורה התחתונה</span>
                    <p className="text-xl md:text-2xl font-black text-amber-950 leading-tight">{job.recommendation}</p>
                  </div>
                </div>
              </div>

              {/* Main Grid: Left Context & Right Sidebar */}
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
                
                {/* Left: Deep Analysis (3/4) */}
                <div className="lg:col-span-3 space-y-5">
                  
                  {/* Summary Card */}
                  <div className="bg-white rounded-3xl p-6 border border-slate-200 transition-all hover:shadow-md">
                    <div className="flex items-center gap-2 mb-4">
                       <FileText size={18} className="text-blue-500" />
                       <h3 className="font-bold text-slate-800">סיכום המשרה</h3>
                    </div>
                    <div className="relative">
                      <p className={`text-slate-700 text-base leading-relaxed italic ${!showFullSummary ? 'line-clamp-3' : ''}`}>
                        "{job.job_summary_hebrew}"
                      </p>
                      {!showFullSummary && (
                        <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent pointer-events-none"></div>
                      )}
                    </div>
                    <button onClick={() => setShowFullSummary(!showFullSummary)} className="mt-2 text-blue-600 font-bold text-xs flex items-center gap-1 hover:underline">
                      {showFullSummary ? 'הצג פחות' : 'קרא עוד'}
                      <ChevronDown size={14} className={showFullSummary ? 'rotate-180' : ''} />
                    </button>
                  </div>

                  {/* Detailed Fit Analysis */}
                  <div className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-sm">
                    <div className="px-6 py-4 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between">
                       <div className="flex items-center gap-2">
                          <Sparkles size={18} className="text-indigo-500" />
                          <h3 className="font-bold text-slate-800">ניתוח התאמה מפורט</h3>
                       </div>
                    </div>
                    <div className="p-8 relative">
                      <div className={`text-slate-700 text-base leading-relaxed whitespace-pre-line ${!showFullAnalysis ? 'max-h-[250px] overflow-hidden' : ''}`}>
                        {job.formatted_message}
                        {!showFullAnalysis && (
                          <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white to-transparent pointer-events-none"></div>
                        )}
                      </div>
                      <div className="flex justify-center mt-4">
                        <button onClick={() => setShowFullAnalysis(!showFullAnalysis)} className="px-6 py-2 bg-slate-900 text-white rounded-full text-xs font-bold hover:bg-black transition-all flex items-center gap-2">
                           {showFullAnalysis ? 'הצג פחות' : 'להמשך קריאה'}
                           <ChevronDown size={14} className={showFullAnalysis ? 'rotate-180' : ''} />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Red/Indigo Insights */}
                  <div className="grid md:grid-cols-2 gap-5">
                    <div className="bg-rose-50/30 rounded-3xl p-6 border border-rose-100">
                      <div className="flex items-center gap-2 mb-4 text-rose-600">
                         <AlertCircle size={18} />
                         <span className="font-black text-sm uppercase tracking-wider">נקודות תורפה</span>
                      </div>
                      <ul className="space-y-3">
                        {job.showstoppers?.map((item, i) => (
                          <li key={i} className="flex gap-2 text-slate-700 text-sm leading-snug">
                             <span className="text-rose-400 font-bold">•</span> {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="bg-indigo-50/30 rounded-3xl p-6 border border-indigo-100">
                      <div className="flex items-center gap-2 mb-4 text-indigo-600">
                         <TrendingUp size={18} />
                         <span className="font-black text-sm uppercase tracking-wider">פערי ידע</span>
                      </div>
                      <ul className="space-y-3">
                        {job.gap_analysis?.map((item, i) => (
                          <li key={i} className="flex gap-2 text-slate-700 text-sm leading-snug">
                             <span className="text-indigo-400 font-bold">•</span> {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Right: Action Center (1/4) */}
                <div className="lg:col-span-1 space-y-4 lg:sticky lg:top-8">
                  
                  {/* Major Actions */}
                  <div className="bg-slate-900 rounded-[2rem] p-6 text-white shadow-xl shadow-slate-200 border-b-8 border-slate-800">
                    <h3 className="text-center font-black text-sm uppercase tracking-widest mb-5 text-slate-400">לוח בקרה</h3>
                    
                    <div className="space-y-3">
                      {job.url && (
                        <a href={job.url} target="_blank" rel="noopener noreferrer" className="w-full py-4 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg active:scale-95">
                           להגשה <ExternalLink size={18} />
                        </a>
                      )}
                      
                      <button onClick={() => { onUpdateStatus(job.url, 'applied'); onClose(); }} className="w-full py-4 bg-emerald-600 hover:bg-emerald-500 rounded-xl font-bold flex items-center justify-center gap-2 transition-all active:scale-95">
                         <Send size={18} /> דיווח: הוגש
                      </button>

                      <button onClick={() => { onUpdateStatus(job.url, 'not_relevant'); onClose(); }} className="w-full py-3 bg-white/10 hover:bg-white/20 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all">
                         <X size={16} /> לא רלוונטי
                      </button>
                    </div>

                    {job.url && (
                      <button onClick={() => navigator.clipboard.writeText(job.url)} className="w-full mt-4 text-slate-500 hover:text-white text-[10px] font-bold flex items-center justify-center gap-1 transition-colors uppercase tracking-widest">
                         העתק לינק <Copy size={12} />
                      </button>
                    )}
                  </div>

                  {/* Utility Panel */}
                  <div className="bg-white rounded-3xl p-5 border border-slate-200 space-y-4">
                    <div className="space-y-3">
                      {!isManual && (
                        <button onClick={async () => { setIsRescanLoading(true); await onRetry(job.url); setIsRescanLoading(false); onClose(); }} className="w-full py-3 text-amber-600 bg-amber-50 hover:bg-amber-100 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all">
                           {isRescanLoading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                           סריקה מחדש
                        </button>
                      )}
                      
                      <div className="grid grid-cols-2 gap-2">
                        <button onClick={() => setIsEditing(true)} className="py-3 bg-slate-50 hover:bg-slate-100 text-slate-600 rounded-xl font-bold text-xs">עריכה</button>
                        <button onClick={() => { onDelete(job); onClose(); }} className="py-3 bg-slate-50 hover:bg-rose-50 hover:text-rose-600 text-slate-400 rounded-xl font-bold text-xs transition-colors">מחיקה</button>
                      </div>
                    </div>
                  </div>

                  {/* Metadata Sidebar Item */}
                  <div className="bg-slate-200/40 rounded-3xl p-5 space-y-3">
                    <div className="flex items-center justify-between text-[10px] font-black uppercase text-slate-500">
                       <span>תאריך</span>
                       <span>{new Date(job.analyzed_at || job.created_at).toLocaleDateString('he-IL')}</span>
                    </div>
                    {job.location && (
                      <div className="flex items-center justify-between text-[10px] font-black uppercase text-slate-500">
                         <span>מיקום</span>
                         <span>{job.location}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Original Content - Discrete but accessible */}
              <div className="mt-12 mb-6 border-t border-slate-200 pt-8 flex flex-col items-center">
                 <button onClick={() => setShowFullDesc(!showFullDesc)} className="text-slate-400 hover:text-slate-600 font-bold text-[10px] uppercase tracking-[0.2em] flex items-center gap-2 transition-all px-6 py-2 rounded-full border border-slate-200 bg-white">
                    {showFullDesc ? 'הסתר מידע מקורי' : 'צפה במקור המשרה המלא'}
                    <ChevronDown size={14} className={showFullDesc ? 'rotate-180' : ''} />
                 </button>
                 {showFullDesc && (
                   <div className="mt-6 w-full max-w-4xl bg-white border border-slate-100 rounded-3xl p-8 text-slate-500 text-sm leading-relaxed whitespace-pre-wrap animate-in fade-in slide-in-from-top-4">
                     {job.full_description}
                   </div>
                 )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default JobModal;
