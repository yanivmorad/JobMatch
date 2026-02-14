// src/components/JobCard/JobModal.jsx
import React, { useState } from 'react';
import { Sparkles, ChevronDown, Loader2 } from 'lucide-react';

// תת-קומפוננטות
import JobModalHeader from './JobModalHeader';
import JobAnalysisSection from './JobAnalysisSection';
import JobInsightsGrid from './JobInsightsGrid';
import JobActionPanel from './JobActionPanel';

/**
 * קומפוננטת המודל הראשית - משמשת כקונטיינר ומנהלת סטייט
 */
const JobModal = ({ job, onClose, onAction, onDelete, onUpdateStatus, onRetry }) => {
  const [showFullDesc, setShowFullDesc] = useState(false);
  const [showFullSummary, setShowFullSummary] = useState(false);
  const [isEditing, setIsEditing] = useState(['FAILED_SCRAPE', 'NO_DATA'].includes(job.status));
  const [editTitle, setEditTitle] = useState(job.job_title || '');
  const [editCompany, setEditCompany] = useState(job.company || '');
  const [editDesc, setEditDesc] = useState(job.full_description || '');
  const [isSaving, setIsSaving] = useState(false);
  const [isRescanLoading, setIsRescanLoading] = useState(false);
  const [showFullAnalysis, setShowFullAnalysis] = useState(false);

  const isManual = job.url?.startsWith('manual-') || !job.url?.includes('http');

  const getScoreColor = (score) => {
    if (score >= 80) return { 
      text: "text-emerald-600", 
      bg: "bg-emerald-50", 
      border: "border-emerald-200", 
      fill: "bg-emerald-500",
      gradient: "from-emerald-500 to-emerald-600"
    };
    if (score >= 50) return { 
      text: "text-amber-600", 
      bg: "bg-amber-50", 
      border: "border-amber-200", 
      fill: "bg-amber-500",
      gradient: "from-amber-500 to-amber-600"
    };
    return { 
      text: "text-rose-600", 
      bg: "bg-rose-50", 
      border: "border-rose-200", 
      fill: "bg-rose-500",
      gradient: "from-rose-500 to-rose-600"
    };
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
    <div 
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[100] p-4 animate-in fade-in duration-200" 
      dir="rtl" 
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-3xl w-full max-w-5xl max-h-[96vh] overflow-hidden shadow-2xl flex flex-col animate-in zoom-in-95 duration-200" 
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* =============== HEADER =============== */}
        <JobModalHeader 
          job={job}
          isEditing={isEditing}
          editCompany={editCompany}
          setEditCompany={setEditCompany}
          editTitle={editTitle}
          setEditTitle={setEditTitle}
          onClose={onClose}
          getScoreColor={getScoreColor}
        />

        {/* =============== CONTENT AREA =============== */}
        <div className="flex-1 overflow-y-auto custom-scrollbar bg-slate-50/30">
          {isEditing ? (
            <section className="max-w-4xl mx-auto p-6 md:p-10 space-y-6">
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                <textarea 
                  className="w-full h-[50vh] p-6 md:p-8 bg-transparent outline-none text-slate-800 text-lg leading-relaxed resize-none"
                  value={editDesc} 
                  onChange={e => setEditDesc(e.target.value)} 
                  placeholder="הדבק כאן את תוכן המשרה..."
                />
              </div>
              <button 
                onClick={handleSave} 
                disabled={isSaving} 
                className="w-full py-4 bg-gradient-to-l from-blue-600 to-blue-500 text-white rounded-2xl font-black text-xl hover:from-blue-700 hover:to-blue-600 transition-all shadow-lg active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-3"
              >
                {isSaving ? <Loader2 className="animate-spin" size={24} /> : <Sparkles size={24} />} 
                שמור ונתח משרה
              </button>
            </section>
          ) : (
            <div className="max-w-4xl mx-auto p-6 md:p-10 space-y-8">
              <JobAnalysisSection 
                job={job}
                showFullSummary={showFullSummary}
                setShowFullSummary={setShowFullSummary}
                showFullAnalysis={showFullAnalysis}
                setShowFullAnalysis={setShowFullAnalysis}
              />

              <JobInsightsGrid job={job} />

              <JobActionPanel 
                job={job}
                isManual={isManual}
                onUpdateStatus={onUpdateStatus}
                onRetry={onRetry}
                onDelete={onDelete}
                onClose={onClose}
                isRescanLoading={isRescanLoading}
                setIsRescanLoading={setIsRescanLoading}
              />

              {/* ORIGINAL DESCRIPTION (COLLAPSED) */}
              <div className="border-t border-slate-200 pt-8 flex flex-col items-center">
                <button 
                  onClick={() => setShowFullDesc(!showFullDesc)} 
                  className="text-slate-400 hover:text-slate-600 font-bold text-[10px] uppercase tracking-widest flex items-center gap-2 transition-all px-5 py-2 rounded-full border border-slate-200 bg-white hover:bg-slate-50"
                >
                  {showFullDesc ? 'הסתר תיאור מלא' : 'הצג תיאור משרה מלא'}
                  <ChevronDown size={12} className={`transition-transform ${showFullDesc ? 'rotate-180' : ''}`} />
                </button>
                {showFullDesc && (
                  <div className="mt-6 w-full bg-white border border-slate-200 rounded-3xl p-8 text-slate-600 text-sm leading-relaxed whitespace-pre-wrap animate-in fade-in slide-in-from-top-4">
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