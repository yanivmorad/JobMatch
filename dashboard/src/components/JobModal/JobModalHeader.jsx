import React from 'react';
import { X, ExternalLink, Building2, MapPin, Sparkles, TrendingUp } from 'lucide-react';

const JobModalHeader = ({ 
  job, isEditing, editCompany, setEditCompany, editTitle, setEditTitle, 
  onClose, getScoreColor 
}) => {
  return (
    <div className="relative bg-gradient-to-br from-slate-50 to-white border-b border-slate-200">
      <div className="px-6 md:px-10 py-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="space-y-3">
              <input 
                className="text-sm font-bold text-slate-500 bg-slate-100 border-b-2 border-blue-500 outline-none w-full px-3 py-2 rounded-lg" 
                value={editCompany} 
                onChange={e => setEditCompany(e.target.value)} 
                placeholder="שם החברה" 
              />
              <input 
                className="text-2xl md:text-3xl font-black text-slate-900 border-b-2 border-blue-500 outline-none w-full px-3 py-2 rounded-lg bg-blue-50/30" 
                value={editTitle} 
                onChange={e => setEditTitle(e.target.value)} 
                placeholder="כותרת המשרה" 
              />
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-2">
                <Building2 size={16} className="text-slate-400 shrink-0" />
                <span className="text-sm font-bold text-slate-500 uppercase tracking-wide">
                  {job.company || 'חברה לא ידועה'}
                </span>
                {job.location && (
                  <>
                    <span className="w-1 h-1 rounded-full bg-slate-300 mx-1"></span>
                    <MapPin size={14} className="text-slate-400 shrink-0" />
                    <span className="text-xs text-slate-400">{job.location}</span>
                  </>
                )}
              </div>
              <h1 className="text-2xl md:text-4xl font-black text-slate-900 leading-tight">
                {job.job_title || job.url}
              </h1>
            </>
          )}
        </div>

        {!isEditing && (
          <div className="flex gap-3 shrink-0">
            {[
              { label: "התאמה", value: job.suitability_score, icon: Sparkles },
              { label: "סיכוי", value: job.acceptance_probability, icon: TrendingUp }
            ].map((metric, idx) => {
              const style = getScoreColor(metric.value);
              const Icon = metric.icon;
              return (
                <div 
                  key={idx} 
                  className={`bg-white rounded-2xl px-5 py-3 border-2 ${style.border} shadow-sm flex flex-col items-center min-w-[100px] group hover:shadow-md transition-all`}
                >
                  <Icon size={14} className={`${style.text} mb-1`} />
                  <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1">
                    {metric.label}
                  </span>
                  <span className={`text-2xl font-black ${style.text} leading-none`}>
                    {metric.value}%
                  </span>
                </div>
              );
            })}
          </div>
        )}

        <button 
          onClick={onClose} 
          className="absolute top-4 left-4 p-2 text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-all"
        >
          <X size={22} />
        </button>
      </div>

      {!isEditing && job.url && (
        <div className="px-6 md:px-10 pb-6">
          <a 
            href={job.url} 
            target="_blank" 
            rel="noopener noreferrer" 
            className="group w-full bg-gradient-to-l from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white py-3.5 px-6 rounded-2xl font-black text-lg flex items-center justify-center gap-3 transition-all shadow-lg hover:shadow-xl active:scale-[0.98]"
          >
            <span>עבור לדף המשרה והגש מועמדות</span>
            <ExternalLink size={20} className="group-hover:translate-x-1 transition-transform" />
          </a>
        </div>
      )}
    </div>
  );
};

export default JobModalHeader;
