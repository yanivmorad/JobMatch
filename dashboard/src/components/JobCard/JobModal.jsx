import React, { useState } from 'react';
import { 
  X, ExternalLink, Send, FileText, Lightbulb, 
  AlertCircle, TrendingUp, Sparkles, Clock, Building2, MapPin, ChevronDown, Loader2, RefreshCw
} from 'lucide-react';
import { STATUS_CONFIG } from '../../constants/statusConfig';

const JobModal = ({ job, onClose, onAction, onDelete, onUpdateStatus, onRetry }) => {
  const [showFullDesc, setShowFullDesc] = useState(false);
  const [isEditing, setIsEditing] = useState(['FAILED_SCRAPE', 'NO_DATA'].includes(job.status));
  const [editTitle, setEditTitle] = useState(job.job_title || '');
  const [editCompany, setEditCompany] = useState(job.company || '');
  const [editDesc, setEditDesc] = useState(job.full_description || '');
  const [isSaving, setIsSaving] = useState(false);
  const [isRescanLoading, setIsRescanLoading] = useState(false);
  
  const isFailed = ['FAILED_SCRAPE', 'NO_DATA'].includes(job.status);
  const isManual = job.url?.startsWith('manual-') || !job.url?.includes('http');

  const currentStatus = job.application_status || 'pending';
  const statusInfo = STATUS_CONFIG[currentStatus];

  const handleStatusChange = (e) => {
    onUpdateStatus(job.url, e.target.value);
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-emerald-600 bg-emerald-50 border-emerald-100";
    if (score >= 50) return "text-amber-600 bg-amber-50 border-amber-100";
    return "text-rose-600 bg-rose-50 border-rose-100";
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
    
    if (success) {
      setIsEditing(false);
    }
    setIsSaving(false);
  };

  return (
    <div 
      className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-[100] p-4 md:p-12 animate-in fade-in duration-300" 
      dir="rtl"
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-[2rem] w-full max-w-6xl max-h-[90vh] overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.2)] flex flex-col border border-slate-200 animate-in zoom-in-95"
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* --- Header --- */}
        <div className="px-10 py-8 border-b border-slate-100 bg-white flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex-1 space-y-4 text-center md:text-right w-full">
            <div className="flex flex-wrap justify-center md:justify-start items-center gap-3">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 text-slate-600 rounded-full text-xs font-bold uppercase tracking-wide">
                <Building2 size={14} />
                {isEditing ? 'עריכה ידנית' : job.company}
              </span>
              {job.location && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-100 text-slate-600 rounded-full text-xs font-bold uppercase tracking-wide">
                  <MapPin size={14} />
                  {job.location}
                </span>
              )}
              <span className="inline-flex items-center gap-1.5 text-slate-400 text-xs font-medium">
                <Clock size={14} />
                {new Date(job.analyzed_at || job.created_at).toLocaleDateString('he-IL')}
              </span>
            </div>
            
            {isEditing ? (
              <div className="space-y-4 w-full">
                <input 
                  className="text-2xl md:text-3xl font-black text-slate-900 border-b-2 border-blue-500 outline-none w-full bg-slate-50 px-2 py-1 rounded"
                  value={editTitle}
                  onChange={e => setEditTitle(e.target.value)}
                  placeholder="כותרת המשרה"
                />
                <input 
                  className="text-xl font-bold text-slate-600 border-b border-slate-300 outline-none w-full bg-slate-50 px-2 py-1 rounded"
                  value={editCompany}
                  onChange={e => setEditCompany(e.target.value)}
                  placeholder="שם החברה"
                />
              </div>
            ) : (
              <h2 className="text-3xl md:text-4xl font-black text-slate-900 leading-tight">
                {job.job_title || job.url}
              </h2>
            )}
          </div>

          <div className="flex items-center gap-6">
            {!isEditing && job.status === 'COMPLETED' && (
              <div className="flex gap-3">
                <div className={`flex flex-col items-center justify-center w-24 h-24 rounded-2xl border-2 ${getScoreColor(job.suitability_score)}`}>
                  <span className="text-[10px] font-black opacity-80 uppercase">התאמה</span>
                  <span className="text-3xl font-black">{job.suitability_score}%</span>
                </div>
                <div className={`flex flex-col items-center justify-center w-24 h-24 rounded-2xl border-2 ${getScoreColor(job.acceptance_probability)}`}>
                  <span className="text-[10px] font-black opacity-80 uppercase">סיכוי</span>
                  <span className="text-3xl font-black">{job.acceptance_probability}%</span>
                </div>
              </div>
            )}
            <button onClick={onClose} className="p-3 text-slate-300 hover:text-slate-900 hover:bg-slate-50 rounded-full transition-all">
              <X size={28} />
            </button>
          </div>
        </div>

        {/* --- Content Area --- */}
        <div className="flex-1 overflow-y-auto custom-scrollbar bg-white">
          <div className="max-w-5xl mx-auto px-10 py-12 space-y-20">
            {isEditing ? (
              <section className="space-y-8 animate-in fade-in duration-500">
                <div className="bg-blue-50/50 p-6 rounded-3xl border border-blue-100 flex flex-col md:flex-row justify-between items-center gap-6">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-blue-600 text-white rounded-xl shadow-lg shadow-blue-100">
                      <FileText size={22} />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-blue-600">הזנה ידנית</h3>
                      <p className="text-blue-600/60 text-sm">העתק והדבק את דרישות המשרה כאן</p>
                    </div>
                  </div>
                  {!isManual && (
                    <a href={job.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 px-6 py-3 bg-white text-blue-600 border-2 border-blue-200 rounded-2xl font-black hover:bg-blue-50 transition-all">
                      <ExternalLink size={18} />
                      פתח קישור מקורי
                    </a>
                  )}
                </div>

                <textarea 
                  className="w-full h-[400px] p-8 bg-slate-50 border-2 border-slate-200 rounded-[2rem] focus:border-blue-500 focus:bg-white outline-none text-slate-800 text-lg leading-relaxed shadow-inner"
                  value={editDesc}
                  onChange={e => setEditDesc(e.target.value)}
                  placeholder="הדבק כאן את תוכן המשרה..."
                />

                <button 
                  onClick={handleSave}
                  disabled={isSaving || !editTitle || !editCompany || !editDesc}
                  className="w-full py-6 bg-blue-600 text-white rounded-2xl font-black text-xl hover:bg-blue-700 transition-all shadow-xl disabled:opacity-50 flex items-center justify-center gap-3"
                >
                  {isSaving ? <Loader2 className="animate-spin" /> : <Sparkles />}
                  שמור ושלח לניתוח AI
                </button>
              </section>
            ) : (
              <>
                {job.job_summary_hebrew && (
                  <section className="relative">
                    <div className="flex items-center gap-2 mb-6 text-slate-400 font-bold uppercase text-xs tracking-widest">
                      <FileText size={18} />
                      <h3>תקציר המשרה</h3>
                    </div>
                    <div className="text-xl md:text-2xl text-slate-700 font-medium leading-relaxed max-w-4xl border-r-4 border-blue-500 pr-6">
                      {job.job_summary_hebrew}
                    </div>
                  </section>
                )}

                <section className="space-y-8">
                  <div className="flex items-center gap-3 text-blue-600 font-bold text-xl">
                    <Sparkles size={22} />
                    <h3>ניתוח התאמה</h3>
                  </div>
                  <div className="bg-slate-50/50 rounded-[2.5rem] p-10 border border-slate-100 whitespace-pre-line text-slate-800 text-lg leading-[2]">
                    {job.formatted_message}
                  </div>
                </section>

                <div className="grid md:grid-cols-2 gap-12">
                  <div className="space-y-6">
                    <div className="flex items-center gap-2 text-rose-600 font-bold"><AlertCircle size={20} /><h4>נקודות תורפה</h4></div>
                    {job.showstoppers?.map((item, i) => (
                      <div key={i} className="p-5 bg-rose-50/30 border border-rose-100 rounded-2xl text-slate-700 font-medium">{item}</div>
                    ))}
                  </div>
                  <div className="space-y-6">
                    <div className="flex items-center gap-2 text-indigo-600 font-bold"><TrendingUp size={20} /><h4>פערי ידע</h4></div>
                    {job.gap_analysis?.map((item, i) => (
                      <div key={i} className="p-5 bg-indigo-50/30 border border-indigo-100 rounded-2xl text-slate-700 font-medium">{item}</div>
                    ))}
                  </div>
                </div>

                <section className="bg-amber-50/50 border-2 border-amber-200 rounded-[2rem] p-10 flex flex-col md:flex-row gap-8 items-center">
                  <div className="w-16 h-16 bg-amber-400 text-white rounded-2xl flex items-center justify-center shrink-0 shadow-lg"><Lightbulb size={32} /></div>
                  <div>
                    <p className="text-amber-700/60 text-xs font-black uppercase tracking-widest">המלצה סופית</p>
                    <p className="text-2xl md:text-3xl font-black text-amber-900 leading-tight">{job.recommendation}</p>
                  </div>
                </section>
              </>
            )}

            {!isEditing && (
              <section className="pt-8 border-t border-slate-100 text-center">
                <button onClick={() => setShowFullDesc(!showFullDesc)} className="inline-flex items-center gap-2 text-slate-400 hover:text-slate-600 font-bold text-sm uppercase px-6 py-3 rounded-xl hover:bg-slate-50 transition-all">
                  {showFullDesc ? 'הסתר תיאור' : 'צפה בתיאור המקורי'}
                  <ChevronDown size={18} className={showFullDesc ? 'rotate-180' : ''} />
                </button>
                {showFullDesc && (
                  <div className="mt-8 text-right bg-slate-50 rounded-3xl p-10 border text-slate-600 whitespace-pre-wrap animate-in slide-in-from-top-4">
                    {job.full_description || 'אין טקסט זמין'}
                  </div>
                )}
              </section>
            )}
          </div>
        </div>

        {/* --- Footer --- */}
        <div className="px-10 py-8 bg-white border-t border-slate-100 flex flex-col md:flex-row gap-4 items-center">
          {!isEditing ? (
            <>
              {!isManual && (
                <div className="flex gap-2 w-full md:w-auto">
                  <a href={job.url} target="_blank" rel="noreferrer" className="flex-1 md:flex-none px-6 py-5 border-2 border-slate-200 text-slate-600 font-bold rounded-2xl hover:bg-slate-50 transition-all text-center">אתר מקורי</a>
                  <button 
                    onClick={async () => {
                      if (onRetry) {
                        setIsRescanLoading(true);
                        const success = await onRetry(job.url);
                        if (success) {
                          onClose();
                        }
                        setIsRescanLoading(false);
                      }
                    }} 
                    disabled={isRescanLoading}
                    className="flex-1 md:flex-none px-6 py-5 border-2 border-amber-200 text-amber-600 font-bold rounded-2xl hover:bg-amber-50 transition-all flex items-center justify-center gap-2"
                  >
                    {isRescanLoading ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <RefreshCw size={18} />
                    )}
                    <span>סרוק מחדש</span>
                  </button>
                </div>
              )}
              
              <div className="flex-1 flex flex-col md:flex-row gap-3 w-full">
                <button 
                  onClick={() => { onUpdateStatus(job.url, 'applied'); onClose(); }}
                  className="flex-1 flex items-center justify-center gap-2 px-8 py-5 bg-slate-900 text-white font-bold rounded-2xl hover:bg-black shadow-lg transition-all text-lg"
                >
                  <Send size={20} />
                  <span>שלחתי קורות חיים</span>
                </button>
                
                <button 
                  onClick={() => { onUpdateStatus(job.url, 'not_relevant'); onClose(); }}
                  className="flex-1 flex items-center justify-center gap-2 px-8 py-5 bg-white border-2 border-slate-200 text-slate-600 font-bold rounded-2xl hover:bg-slate-50 transition-all text-lg"
                >
                  <X size={20} />
                  <span>לא רלוונטי</span>
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button onClick={() => setIsEditing(true)} className="px-6 py-4 text-blue-600 font-bold hover:bg-blue-50 rounded-xl transition-colors">עריכה</button>
                <button onClick={() => { onDelete(job); onClose(); }} className="px-6 py-4 text-slate-400 font-bold hover:text-rose-600 transition-colors text-sm">מחיקה</button>
              </div>
            </>
          ) : (
            <div className="flex justify-between w-full">
              <button onClick={() => {onDelete(job); onClose();}} className="px-8 py-5 text-rose-600 font-bold hover:bg-rose-50 rounded-xl transition-colors flex items-center gap-2"><X size={20} /> מחק משרה</button>
              <button onClick={() => setIsEditing(false)} className="px-8 py-5 text-slate-400 font-bold hover:text-slate-600 transition-colors">ביטול</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default JobModal;