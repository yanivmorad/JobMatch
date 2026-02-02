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

  const isManual = job.url?.startsWith('manual-') || !job.url?.includes('http');

  // רכיב עזר לציונים קטנים ומעוצבים
  const ScoreBadge = ({ label, score, colorClass }) => (
    <div className={`flex flex-col items-center justify-center px-6 py-3 rounded-2xl border ${colorClass} bg-white shadow-sm`}>
      <span className="text-[10px] font-bold opacity-60 uppercase mb-1">{label}</span>
      <span className="text-2xl font-black">{score}%</span>
    </div>
  );

  const getScoreStyle = (score) => {
    if (score >= 80) return "border-emerald-200 text-emerald-600 bg-emerald-50/30";
    if (score >= 50) return "border-amber-200 text-amber-600 bg-amber-50/30";
    return "border-rose-200 text-rose-600 bg-rose-50/30";
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
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-[100] p-4 md:p-6 animate-in fade-in duration-300" dir="rtl" onClick={onClose}>
      <div className="bg-slate-50 rounded-[2.5rem] w-full max-w-5xl max-h-[92vh] overflow-hidden shadow-2xl flex flex-col border border-white animate-in zoom-in-95" onClick={(e) => e.stopPropagation()}>
        
        {/* --- Header: פרטי משרה וציונים --- */}
        <div className="px-8 py-6 bg-white border-b border-slate-200 flex flex-col md:flex-row justify-between items-start gap-6">
          <div className="flex-1 space-y-3">
            <div className="flex flex-wrap items-center gap-3 text-slate-400">
              <span className="flex items-center gap-1.5 px-3 py-1 bg-slate-100 rounded-lg text-xs font-bold text-slate-600 uppercase tracking-wide">
                <Building2 size={14} /> {isEditing ? 'עריכה' : (job.company || 'חברה לא ידועה')}
              </span>
              {job.location && (
                <span className="flex items-center gap-1.5 px-3 py-1 bg-slate-100 rounded-lg text-xs font-bold text-slate-600 uppercase tracking-wide">
                  <MapPin size={14} /> {job.location}
                </span>
              )}
              <span className="flex items-center gap-1.5 text-xs font-medium mr-2">
                <Clock size={14} /> {new Date(job.analyzed_at || job.created_at).toLocaleDateString('he-IL')}
              </span>
            </div>
            
            {isEditing ? (
              <div className="space-y-3 w-full max-w-xl">
                <input className="text-2xl font-black text-slate-900 border-b-2 border-blue-500 outline-none w-full bg-blue-50/50 px-3 py-2 rounded-t-xl" value={editTitle} onChange={e => setEditTitle(e.target.value)} placeholder="כותרת המשרה" />
                <input className="text-lg font-bold text-slate-600 border-b border-slate-200 outline-none w-full bg-slate-50 px-3 py-1 rounded" value={editCompany} onChange={e => setEditCompany(e.target.value)} placeholder="שם החברה" />
              </div>
            ) : (
              <h2 className="text-3xl font-black text-slate-900 tracking-tight leading-tight">{job.job_title || job.url}</h2>
            )}
          </div>

          <div className="flex items-center gap-4 self-center md:self-start">
            {!isEditing && job.status === 'COMPLETED' && (
              <div className="flex gap-3">
                <ScoreBadge label="התאמה" score={job.suitability_score} colorClass={getScoreStyle(job.suitability_score)} />
                <ScoreBadge label="סיכוי" score={job.acceptance_probability} colorClass={getScoreStyle(job.acceptance_probability)} />
              </div>
            )}
            <button onClick={onClose} className="p-2 text-slate-300 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-all">
              <X size={24} />
            </button>
          </div>
        </div>

{/* --- Content Area --- */}
<div className="flex-1 overflow-y-auto custom-scrollbar p-6 md:p-10 bg-slate-50/50">
  {isEditing ? (
    <section className="space-y-6 max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4">
      <div className="bg-white p-2 rounded-[2rem] shadow-sm border border-slate-200">
        <textarea 
          className="w-full h-80 p-8 bg-transparent outline-none text-slate-800 text-lg leading-relaxed resize-none"
          value={editDesc} 
          onChange={e => setEditDesc(e.target.value)} 
          placeholder="הדבק כאן את תוכן המשרה..."
        />
      </div>
      <button onClick={handleSave} disabled={isSaving} className="w-full py-5 bg-blue-600 text-white rounded-2xl font-black text-xl hover:bg-blue-700 transition-all shadow-xl shadow-blue-100 disabled:opacity-50 flex items-center justify-center gap-3">
        {isSaving ? <Loader2 className="animate-spin" /> : <Sparkles size={24} />} שמור ונתח משרה
      </button>
    </section>
  ) : (
    <div className="max-w-5xl mx-auto space-y-8">
      
      {/* 1. Top Bar: המלצה, תקציר ולינק למשרה */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
        
        {/* כרטיס המלצה - 3 עמודות */}
        <div className="md:col-span-3 bg-amber-400 rounded-[2rem] p-6 flex flex-col justify-center items-center text-center shadow-lg shadow-amber-200/50 border-b-8 border-amber-500/30">
          <span className="text-amber-900/60 text-[10px] font-black uppercase tracking-[0.2em] mb-1">השורה התחתונה</span>
          <p className="text-2xl font-black text-amber-950 leading-tight">
            {job.recommendation}
          </p>
        </div>

        {/* כרטיס תקציר - 6 עמודות */}
        <div className="md:col-span-6 bg-white rounded-[2rem] p-6 border border-slate-200 shadow-sm flex flex-col justify-center">
          <h4 className="text-slate-400 font-bold text-[10px] uppercase tracking-widest mb-2 flex items-center gap-2">
            <span className="w-6 h-[1px] bg-slate-200"></span> במה מדובר?
          </h4>
          <p className="text-slate-700 text-lg font-medium leading-relaxed italic line-clamp-3">
            "{job.job_summary_hebrew}"
          </p>
        </div>

        {/* כרטיס לינק למשרה - 3 עמודות - חדש! */}
        <div className="md:col-span-3 bg-slate-900 rounded-[2rem] p-6 flex flex-col justify-center items-center shadow-xl shadow-slate-200 border-b-8 border-slate-800 group transition-all">
          {job.url ? (
            <>
              <span className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-3">מקור המשרה</span>
              <div className="flex flex-col gap-2 w-full">
                <a 
                  href={job.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="bg-blue-600 hover:bg-blue-500 text-white p-3 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-colors shadow-lg shadow-blue-900/20"
                >
                  למעבר למשרה <ExternalLink size={16} />
                </a>
                <button 
                  onClick={() => {navigator.clipboard.writeText(job.url)}}
                  className="text-slate-400 hover:text-white text-[10px] font-bold uppercase transition-colors flex items-center justify-center gap-1"
                >
                  העתק לינק <Copy size={12} />
                </button>
              </div>
            </>
          ) : (
            <div className="text-center">
               <span className="text-slate-500 text-[10px] font-black uppercase">אין לינק זמין</span>
               <p className="text-slate-600 text-xs mt-1 italic">משרה מטקסט חופשי</p>
            </div>
          )}
        </div>
      </div>

      {/* 2. ניתוח התאמה מפורט */}
      <section className="bg-white rounded-[2.5rem] border border-slate-200 shadow-sm overflow-hidden relative">
        <div className="px-10 py-6 border-b border-slate-50 bg-slate-50/30 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-xl">
              <Sparkles size={20} />
            </div>
            <h3 className="text-slate-900 font-black text-xl tracking-tight">ניתוח התאמה אישי</h3>
          </div>
          <div className="flex gap-1">
             <div className="w-2 h-2 rounded-full bg-slate-200 animate-pulse"></div>
             <div className="w-2 h-2 rounded-full bg-slate-200"></div>
          </div>
        </div>
        
        <div className="p-10 relative">
          <div className={`text-slate-700 text-lg leading-[2] transition-all duration-700 ease-in-out whitespace-pre-line ${!showFullAnalysis ? 'max-h-[220px] overflow-hidden' : 'max-h-none'}`}>
            {job.formatted_message}
            {!showFullAnalysis && (
              <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white via-white/90 to-transparent z-10" />
            )}
          </div>
          
          <div className="relative z-20 flex justify-center mt-4">
            <button 
              onClick={() => setShowFullAnalysis(!showFullAnalysis)}
              className="px-8 py-3 bg-slate-900 text-white rounded-full font-bold text-sm hover:bg-black transition-all shadow-lg flex items-center gap-2 group"
            >
              {showFullAnalysis ? 'הצג פחות' : 'קרא את הניתוח המלא'}
              <ChevronDown size={16} className={`transition-transform duration-300 ${showFullAnalysis ? 'rotate-180' : 'group-hover:translate-y-0.5'}`} />
            </button>
          </div>
        </div>
      </section>

      {/* 3. Insights Grid */}
      <div className="grid md:grid-cols-2 gap-8">
        {/* נקודות תורפה */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-2">
            <div className="w-2 h-6 bg-rose-500 rounded-full"></div>
            <h4 className="text-slate-900 font-bold tracking-tight">נקודות תורפה</h4>
          </div>
          <div className="grid gap-3">
            {job.showstoppers?.map((item, i) => (
              <div key={i} className="group bg-white hover:bg-rose-50/30 p-5 rounded-2xl border border-slate-200 hover:border-rose-200 transition-all flex gap-4 items-start shadow-sm">
                <AlertCircle className="text-rose-500 shrink-0 mt-0.5" size={18} />
                <p className="text-slate-700 font-medium text-[15px] leading-snug">{item}</p>
              </div>
            ))}
          </div>
        </div>

        {/* פערי ידע */}
        <div className="space-y-4">
          <div className="flex items-center gap-2 px-2">
            <div className="w-2 h-6 bg-indigo-500 rounded-full"></div>
            <h4 className="text-slate-900 font-bold tracking-tight">פערי ידע ודרישות</h4>
          </div>
          <div className="grid gap-3">
            {job.gap_analysis?.map((item, i) => (
              <div key={i} className="group bg-white hover:bg-indigo-50/30 p-5 rounded-2xl border border-slate-200 hover:border-indigo-200 transition-all flex gap-4 items-start shadow-sm">
                <TrendingUp className="text-indigo-500 shrink-0 mt-0.5" size={18} />
                <p className="text-slate-700 font-medium text-[15px] leading-snug">{item}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4. Footer Info: מקור */}
      <div className="pt-10 flex flex-col items-center gap-6">
        <div className="h-[1px] w-40 bg-gradient-to-r from-transparent via-slate-200 to-transparent"></div>
        <button 
          onClick={() => setShowFullDesc(!showFullDesc)} 
          className="text-slate-400 hover:text-blue-600 text-[10px] font-black uppercase tracking-[0.2em] flex items-center gap-2 transition-colors group"
        >
          {showFullDesc ? 'הסתר טקסט מקורי' : 'צפה בטקסט המקורי של המשרה'}
          <div className="p-1 rounded-full group-hover:bg-blue-50 transition-colors">
            <ChevronDown size={14} className={showFullDesc ? 'rotate-180' : ''} />
          </div>
        </button>
        {showFullDesc && (
          <div className="w-full max-w-4xl bg-white rounded-3xl p-10 border border-slate-100 text-slate-500 text-sm leading-[1.8] whitespace-pre-wrap animate-in fade-in zoom-in-95 duration-300">
            {job.full_description}
          </div>
        )}
      </div>
    </div>
  )}
</div>

        {/* --- Footer: פעולות --- */}
        {!isEditing && (
          <div className="px-8 py-6 bg-white border-t border-slate-200 flex flex-wrap gap-3 items-center">
            <button 
              onClick={() => { onUpdateStatus(job.url, 'applied'); onClose(); }}
              className="flex-1 min-w-[200px] flex items-center justify-center gap-2 py-4 bg-slate-900 text-white font-bold rounded-xl hover:bg-black transition-all shadow-md active:scale-95"
            >
              <Send size={18} /> שלחתי קורות חיים
            </button>
            
            <button 
              onClick={() => { onUpdateStatus(job.url, 'not_relevant'); onClose(); }}
              className="flex-1 min-w-[200px] flex items-center justify-center gap-2 py-4 bg-white border border-slate-200 text-slate-600 font-bold rounded-xl hover:bg-slate-50 transition-all"
            >
              <X size={18} /> לא רלוונטי
            </button>

            <div className="h-10 w-px bg-slate-200 mx-2 hidden md:block" />

            <div className="flex gap-2">
              {!isManual && (
                <button 
                  onClick={async () => {
                    setIsRescanLoading(true);
                    await onRetry(job.url);
                    setIsRescanLoading(false);
                    onClose();
                  }}
                  className="p-4 text-amber-600 hover:bg-amber-50 rounded-xl transition-colors"
                  title="סריקה מחדש"
                >
                  {isRescanLoading ? <Loader2 size={20} className="animate-spin" /> : <RefreshCw size={20} />}
                </button>
              )}
              <button onClick={() => setIsEditing(true)} className="px-5 py-4 text-blue-600 font-bold hover:bg-blue-50 rounded-xl transition-colors">עריכה</button>
              <button onClick={() => { onDelete(job); onClose(); }} className="px-5 py-4 text-slate-400 hover:text-rose-600 transition-colors text-sm">מחיקה</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default JobModal;