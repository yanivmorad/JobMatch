import React from 'react';
import { FileText, Loader2, Sparkles, PenTool } from 'lucide-react';

const ManualInputCard = ({ 
  textTitle, 
  setTextTitle, 
  textInput, 
  setTextInput, 
  submitStatus, 
  onSubmit 
}) => {
  const isDark = textInput.length > 0;

  return (
    <div className="group relative bg-white/70 backdrop-blur-xl rounded-[2.5rem] border border-white shadow-[0_20px_50px_rgba(0,0,0,0.05)] overflow-hidden transition-all hover:shadow-[0_20px_60px_rgba(0,0,0,0.08)]">
      {/* אלמנט עיצובי סגול ברקע */}
      <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-purple-500/5 rounded-full blur-3xl group-hover:bg-purple-500/10 transition-all duration-700"></div>
      
      <div className="relative p-8 md:p-10">
        {/* Header Section */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-5">
            <div className="relative">
              <div className="absolute inset-0 bg-purple-400 blur-lg opacity-20"></div>
              <div className="relative bg-gradient-to-br from-purple-500 to-indigo-600 p-4 rounded-2xl text-white shadow-lg">
                <FileText size={26} strokeWidth={2.5} />
              </div>
            </div>
            <div>
              <h3 className="text-2xl font-black text-slate-800 tracking-tight">ניתוח טקסט חופשי</h3>
              <p className="text-slate-500 font-medium italic">הזנה ידנית לדיוק מקסימלי</p>
            </div>
          </div>
          
          {/* אינדיקטור כתיבה */}
          {isDark && (
            <div className="hidden md:flex items-center gap-2 text-purple-600 animate-pulse">
              <PenTool size={16} />
              <span className="text-[10px] font-black uppercase tracking-widest">מזהה תוכן...</span>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-5">
          {/* שדה כותרת */}
          <div className="relative">
            <input 
              type="text" 
              value={textTitle} 
              onChange={e => setTextTitle(e.target.value)}
              placeholder="שם החברה / כותרת המשרה (אופציונלי)"
              className="w-full bg-slate-50/50 border-2 border-slate-100 rounded-2xl px-6 py-4 text-base font-bold text-slate-700 outline-none focus:border-purple-400 focus:bg-white focus:ring-4 focus:ring-purple-500/5 transition-all placeholder:font-normal placeholder:text-slate-400"
            />
          </div>

          {/* שדה תוכן המשרה */}
          <div className="relative">
            <textarea 
              value={textInput} 
              onChange={e => setTextInput(e.target.value)}
              className="w-full h-48 bg-slate-50/50 border-2 border-slate-100 rounded-[2rem] p-6 text-base leading-relaxed text-slate-600 transition-all resize-none outline-none focus:border-purple-400 focus:bg-white focus:ring-4 focus:ring-purple-500/5 custom-scrollbar"
              placeholder="הדבק כאן את תיאור המשרה המלא... המערכת תנתח דרישות, טכנולוגיות ושכר באופן אוטומטי."
            />
            
            {/* Counter עדין */}
            <div className="absolute bottom-5 left-6 text-[10px] font-bold text-slate-400 bg-white/80 px-2 py-1 rounded-md shadow-sm border border-slate-100">
              {textInput.length} תווים
            </div>
          </div>
        </div>

        {/* Footer / Action */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6 mt-8 pt-6 border-t border-slate-50">
          <div className="flex items-center gap-2 text-slate-400 text-sm">
            <Sparkles size={16} className="text-purple-400" />
            <span>עיבוד AI מבוסס מודל Deep Analysis</span>
          </div>

          <button 
            onClick={() => onSubmit(textInput, textTitle)}
            disabled={!textInput.trim() || submitStatus === 'sending'}
            className={`group relative flex items-center gap-3 py-4 px-10 rounded-2xl font-black transition-all overflow-hidden
              ${textInput.trim() 
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:scale-105 active:scale-95 shadow-xl shadow-purple-500/20' 
                : 'bg-slate-100 text-slate-400 cursor-not-allowed'
              }`}
          >
            {submitStatus === 'sending' ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <>
                <Sparkles size={18} />
                <span>נתח טקסט עכשיו</span>
              </>
            )}
            
            {/* אפקט הברק (Shimmer) */}
            {textInput.trim() && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]"></div>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ManualInputCard;