import React, { useMemo } from 'react';
import { Link as LinkIcon, Send, Loader2, AlertCircle, List, Globe, Hash } from 'lucide-react';

const SmartImportCard = ({ 
  rawInput, 
  setRawInput, 
  duplicateJobs, 
  setDuplicateJobs, 
  submitStatus, 
  onSubmit 
}) => {
  const parsedLinks = useMemo(() => {
    if (!rawInput) return [];
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const matches = rawInput.match(urlRegex) || [];
    return [...new Set(matches.map(link => link.replace(/[.,;]$/, "")))];
  }, [rawInput]);

  return (
    <div className="group relative bg-white/70 backdrop-blur-xl rounded-[2.5rem] border border-white shadow-[0_20px_50px_rgba(0,0,0,0.05)] overflow-hidden transition-all hover:shadow-[0_20px_60px_rgba(0,0,0,0.08)]">
      {/* עיטור דקורטיבי עדין בפינה */}
      <div className="absolute -top-24 -right-24 w-48 h-48 bg-blue-500/5 rounded-full blur-3xl group-hover:bg-blue-500/10 transition-all duration-700"></div>
      
      <div className="relative p-8 md:p-10">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10">
          <div className="flex items-center gap-5">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-400 blur-lg opacity-20 animate-pulse"></div>
              <div className="relative bg-gradient-to-br from-blue-500 to-blue-700 p-4 rounded-2xl text-white shadow-lg">
                <LinkIcon size={26} strokeWidth={2.5} />
              </div>
            </div>
            <div>
              <h3 className="text-2xl font-black text-slate-800 tracking-tight">ייבוא לינקים חכם</h3>
              <p className="text-slate-500 font-medium">הדבק טקסט חופשי וה-AI יחלץ את הקישורים</p>
            </div>
          </div>

          {/* מונה לינקים מעוצב */}
          <div className="flex items-center gap-2 bg-slate-100/50 border border-slate-200/60 px-4 py-2 rounded-full">
            <div className={`w-2 h-2 rounded-full ${parsedLinks.length > 0 ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'}`}></div>
            <span className="text-sm font-bold text-slate-600">{parsedLinks.length} לינקים מזוהים</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-8">
          {/* אזור הזנה (Input) */}
          <div className="lg:col-span-7 flex flex-col gap-3">
            <div className="relative group/textarea">
              <textarea 
                value={rawInput}
                onChange={(e) => {
                  setRawInput(e.target.value);
                  if (duplicateJobs.length > 0) setDuplicateJobs([]);
                }}
                className={`w-full h-72 bg-slate-50/50 border-2 rounded-[2rem] p-6 text-base leading-relaxed transition-all resize-none outline-none
                  ${duplicateJobs.length > 0 
                    ? 'border-amber-200 focus:border-amber-400 ring-4 ring-amber-500/5' 
                    : 'border-slate-100 focus:border-blue-500 focus:bg-white ring-4 ring-blue-500/0 focus:ring-blue-500/5'
                  }`}
                placeholder="הדבק כאן הודעות וואטסאפ, פוסטים מלינקדאין או רשימת לינקים..."
              />
              <div className="absolute bottom-6 right-6 opacity-0 group-focus-within/textarea:opacity-100 transition-opacity">
                 <div className="bg-blue-600 text-[10px] text-white px-2 py-1 rounded font-bold uppercase tracking-tighter">AI Scanning...</div>
              </div>
            </div>
          </div>

          {/* תצוגת תוצאות (Live Preview) */}
          <div className="lg:col-span-5 flex flex-col gap-3">
            <div className="h-72 bg-slate-50/30 border-2 border-dashed border-slate-200/60 rounded-[2rem] p-6 overflow-y-auto custom-scrollbar">
              {parsedLinks.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {parsedLinks.map((link, i) => (
                    <div key={i} className="flex items-center gap-2 bg-white border border-slate-100 px-3 py-2 rounded-xl shadow-sm hover:border-blue-200 transition-colors max-w-full">
                      <div className="bg-blue-50 p-1 rounded-md text-blue-500 shrink-0">
                        <Globe size={12} />
                      </div>
                      <span className="text-[11px] text-slate-600 font-mono truncate">{link}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-4 opacity-60">
                  <div className="bg-white p-4 rounded-full shadow-inner">
                    <List size={32} strokeWidth={1.5} className="text-slate-300" />
                  </div>
                  <p className="text-sm font-medium">ממתין להזנת נתונים...</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* הודעות שגיאה */}
        {submitStatus === 'error' && (
          <div className="mb-8 p-5 bg-rose-50/80 border border-rose-100 rounded-[1.5rem] flex items-center gap-4 animate-in fade-in zoom-in duration-300">
            <div className="bg-rose-500 p-2 rounded-lg text-white">
              <AlertCircle size={20} />
            </div>
            <p className="text-rose-900 font-bold text-sm italic">משהו לא עבד. נסה לבדוק את הלינקים שוב.</p>
          </div>
        )}

        {/* כפתור שליחה - מרכזי ומרשים */}
        <div className="flex justify-center md:justify-end pt-6">
<button 
  onClick={() => {
    // 1. קודם כל שומרים את הלינקים שזיהינו במשתנה זמני
    const linksToSend = [...parsedLinks];
    
    // 2. מנקים את הלוח מיד (המשתמש רואה שהכל נעלם)
    setRawInput('');
    setDuplicateJobs([]);
    
    // 3. שולחים את הלינקים ששמרנו לשרת
    onSubmit(linksToSend);
  }}
  disabled={parsedLinks.length === 0 || submitStatus === 'sending'}
  className={`group relative flex items-center gap-4 py-4 px-12 rounded-2xl font-black transition-all overflow-hidden
    ${parsedLinks.length > 0 
      ? 'bg-slate-900 text-white hover:scale-105 active:scale-95 shadow-2xl' 
      : 'bg-slate-100 text-slate-400 cursor-not-allowed'
    }`}
>
  {submitStatus === 'sending' ? (
    <div className="flex items-center gap-2">
      <Loader2 className="animate-spin" size={20} />
      <span>שולח...</span>
    </div>
  ) : (
    <>
      <span>שגר {parsedLinks.length} משרות לעיבוד</span>
      <Send size={18} className="transition-transform group-hover:translate-x-1 group-hover:-translate-y-1" />
    </>
  )}
</button>
        </div>
      </div>
    </div>
  );
};

export default SmartImportCard;