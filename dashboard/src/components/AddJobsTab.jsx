import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Link as LinkIcon, X, Send, Loader2, FileText, CheckCircle, Sparkles, Zap, ArrowLeft, Clock } from 'lucide-react';
import StatusBadge from './StatusBadge';

const AddJobsTab = ({ pendingJobs, onJobAdded }) => {
  const [rawInput, setRawInput] = useState('');
  const [parsedLinks, setParsedLinks] = useState([]);
  const [submitStatus, setSubmitStatus] = useState(null); 
  const [localJobs, setLocalJobs] = useState([]);
  const [textInput, setTextInput] = useState('');
  const [textTitle, setTextTitle] = useState('');

  // --- לוגיקה (ללא שינוי) ---
  useEffect(() => {
    if (!rawInput) {
      setParsedLinks([]);
      return;
    }
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const matches = rawInput.match(urlRegex) || [];
    const uniqueLinks = [...new Set(matches.map(link => link.replace(/[.,;]$/, "")) )];
    setParsedLinks(uniqueLinks);
  }, [rawInput]);

  useEffect(() => {
    if (pendingJobs.length > 0) {
      const serverUrls = new Set(pendingJobs.map(j => j.url));
      setLocalJobs(prev => prev.filter(local => !serverUrls.has(local.url)));
    }
  }, [pendingJobs]);

  const handleUrlSubmit = async () => {
    if (parsedLinks.length === 0) return;
    
    const newOptimisticJobs = parsedLinks.map(url => ({
      url,
      company: 'ממתין לשרת...',
      status: 'pending',
      isLocal: true
    }));
    setLocalJobs(prev => [...prev, ...newOptimisticJobs]);

    setSubmitStatus('sending');
    try {
      await axios.post('http://localhost:8000/api/jobs/url', { urls: parsedLinks });
      setRawInput('');
      setParsedLinks([]); 
      setSubmitStatus('success');
      setTimeout(() => setSubmitStatus(null), 3000);
      onJobAdded(); 
      setTimeout(() => onJobAdded(), 2000); 
    } catch (e) {
      setSubmitStatus('error');
      setTimeout(() => setSubmitStatus(null), 3000);
    }
  };

  const handleTextSubmit = async () => {
    if (!textInput.trim()) return;
    setSubmitStatus('sending');
    try {
      await axios.post('http://localhost:8000/api/jobs/text', {
        text: textInput,
        title: textTitle || 'משרה ידנית'
      });
      setTextInput('');
      setTextTitle('');
      setSubmitStatus('success');
      setTimeout(() => setSubmitStatus(null), 3000);
      onJobAdded();
    } catch (e) {
      setSubmitStatus('error');
    }
  };

  const removeLink = (linkToRemove) => {
    setParsedLinks(parsedLinks.filter(l => l !== linkToRemove));
  };

  const displayQueue = useMemo(() => {
    const serverUrlSet = new Set(pendingJobs.map(j => j.url));
    const uniqueLocalJobs = localJobs.filter(j => !serverUrlSet.has(j.url));
    return [...pendingJobs, ...uniqueLocalJobs];
  }, [pendingJobs, localJobs]);

  // --- UI מתוקן ובהיר ---
  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 min-h-[700px] text-slate-800 pb-10">
      
      {/* צד ימין: אזור ההזנה (רחב יותר) */}
      <div className="xl:col-span-8 flex flex-col gap-8">
        
        {/* כרטיס סריקת קישורים */}
        <div className="bg-white rounded-[2rem] shadow-sm border border-slate-200 overflow-hidden relative group hover:shadow-md transition-all duration-300">
          <div className="absolute top-0 right-0 w-1.5 h-full bg-blue-500"></div>
          
          <div className="p-8">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center text-blue-600">
                <LinkIcon className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-2xl text-slate-900">סריקה מהירה</h3>
                <p className="text-slate-500 text-sm">הדבק תוכן חופשי לחילוץ קישורים</p>
              </div>
            </div>

            <div className="flex flex-col lg:flex-row gap-6">
              <textarea
                value={rawInput}
                onChange={(e) => setRawInput(e.target.value)}
                className="flex-1 h-[200px] lg:h-auto p-5 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 focus:bg-white transition-all text-sm outline-none resize-none"
                placeholder="הדבק כאן הודעות וואטסאפ, מיילים או רשימת קישורים..."
              />

              <div className="lg:w-72 flex flex-col gap-3">
                <div className="flex-1 bg-slate-50 rounded-2xl border border-slate-100 p-3 overflow-y-auto max-h-[180px] custom-scrollbar">
                    {parsedLinks.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2 opacity-60">
                            <Sparkles className="w-6 h-6" />
                            <span className="text-[10px] font-bold uppercase">אין קישורים</span>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {parsedLinks.map((link, i) => (
                                <div key={i} className="flex items-center justify-between bg-white p-2 rounded-xl border border-slate-100 shadow-sm text-xs">
                                    <span className="truncate w-40 font-medium text-slate-600">{link}</span>
                                    <button onClick={() => removeLink(link)} className="text-slate-300 hover:text-rose-500"><X className="w-3 h-3"/></button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
                <button
                  onClick={handleUrlSubmit}
                  disabled={parsedLinks.length === 0 || submitStatus === 'sending'}
                  className={`py-3 rounded-xl font-bold text-sm shadow-sm active:scale-95 transition-all flex justify-center items-center gap-2
                    ${parsedLinks.length > 0 
                        ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-200' 
                        : 'bg-slate-100 text-slate-400 cursor-not-allowed'}
                  `}
                >
                  {submitStatus === 'sending' ? <Loader2 className="animate-spin w-4 h-4" /> : <Send className="w-4 h-4" />}
                  <span>סרוק {parsedLinks.length} משרות</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* כרטיס ניתוח טקסט ידני - מוגדל ומרווח */}
        <div className="bg-white rounded-[2rem] shadow-sm border border-slate-200 p-8 hover:shadow-md transition-all duration-300">
            <div className="flex items-center gap-4 mb-6 border-b border-slate-50 pb-4">
                <div className="w-12 h-12 bg-purple-50 rounded-2xl flex items-center justify-center text-purple-600">
                    <FileText className="w-6 h-6" />
                </div>
                <div>
                    <h3 className="font-bold text-2xl text-slate-900">הזנת משרה ידנית</h3>
                    <p className="text-slate-500 text-sm">הדבק כאן את תיאור המשרה המלא לניתוח</p>
                </div>
            </div>
            
            <div className="space-y-6">
                <div className="flex flex-col md:flex-row gap-4">
                    <div className="flex-1">
                        <label className="text-xs font-bold text-slate-400 mb-1.5 block pr-1">שם חברה / כותרת</label>
                        <input
                            type="text"
                            className="w-full h-12 px-4 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 focus:bg-white outline-none transition-all"
                            placeholder="למשל: Google - Full Stack Developer"
                            value={textTitle}
                            onChange={e => setTextTitle(e.target.value)}
                        />
                    </div>
                    <div className="flex items-end">
                         <button
                            onClick={handleTextSubmit}
                            disabled={!textInput.trim() || submitStatus === 'sending'}
                            className={`h-12 px-8 rounded-xl font-bold text-sm transition-all flex items-center gap-2 shadow-sm whitespace-nowrap
                                ${textInput.trim() 
                                    ? 'bg-purple-600 hover:bg-purple-700 text-white shadow-purple-200 active:scale-95' 
                                    : 'bg-slate-100 text-slate-400 cursor-not-allowed'}
                            `}
                        >
                            {submitStatus === 'sending' ? <Loader2 className="animate-spin w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
                            <span>נתח טקסט</span>
                        </button>
                    </div>
                </div>

                <div className="relative">
                     <label className="text-xs font-bold text-slate-400 mb-1.5 block pr-1">תיאור משרה מלא (הדבק כאן פסקה)</label>
                     <textarea
                        value={textInput}
                        onChange={(e) => setTextInput(e.target.value)}
                        className="w-full h-[300px] p-6 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 focus:bg-white transition-all text-sm leading-relaxed outline-none resize-none font-medium text-slate-700"
                        placeholder="הדבק כאן את כל הטקסט של המשרה...
דרישות, תחומי אחריות, וכל פרט אחר.
המערכת תדע לסנן ולנתח את זה."
                    />
                    <div className="absolute bottom-4 left-4">
                        <span className="text-[10px] font-bold text-slate-400 bg-white/80 px-2 py-1 rounded-md border border-slate-100">
                           {textInput.length} תווים
                        </span>
                    </div>
                </div>
            </div>
        </div>
      </div>

      {/* צד שמאל: Live Queue - מתוקן לבהיר */}
      <div className="xl:col-span-4">
        <div className="bg-white rounded-[2rem] h-full shadow-lg shadow-slate-200/50 border border-slate-100 flex flex-col overflow-hidden">
            
            {/* כותרת בהירה */}
            <div className="p-6 pb-4 border-b border-slate-50 bg-slate-50/50">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="font-black text-lg text-slate-800 flex items-center gap-2">
                            <Clock className="w-5 h-5 text-blue-500" />
                            תור עבודה
                        </h3>
                        <p className="text-slate-400 text-xs font-medium mt-0.5">סטטוס משימות בזמן אמת</p>
                    </div>
                    <span className="bg-white px-3 py-1 rounded-full text-xs font-bold border border-slate-200 text-slate-600 shadow-sm">
                        {displayQueue.length}
                    </span>
                </div>
            </div>

            {/* רשימה בהירה */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/30 custom-scrollbar">
                {displayQueue.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-slate-400 gap-3">
                        <div className="w-16 h-16 bg-slate-50 rounded-full border border-slate-200 flex items-center justify-center">
                            <CheckCircle className="w-8 h-8 opacity-20 text-slate-400" />
                        </div>
                        <p className="text-xs font-bold uppercase tracking-widest opacity-50">הכל נקי</p>
                    </div>
                ) : (
                    displayQueue.map((job, idx) => (
                        <div key={job.url + idx} className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-all group relative overflow-hidden">
                            {/* פס סטטוס צדדי */}
                            <div className={`absolute right-0 top-0 bottom-0 w-1 ${
                                job.status === 'completed' ? 'bg-emerald-500' : 
                                job.status === 'error' ? 'bg-rose-500' : 'bg-blue-500'
                            }`}></div>

                            <div className="flex justify-between items-start mb-3 pr-2">
                                <div className="w-[70%]">
                                    <h4 className="font-bold text-slate-800 truncate text-sm">
                                        {job.company && job.company !== "Unknown" ? job.company : (job.isLocal ? "מעבד..." : "מזהה חברה...")}
                                    </h4>
                                    <p className="text-[10px] text-slate-400 truncate mt-0.5">{job.url.replace(/^https?:\/\//, '')}</p>
                                </div>
                                <div className="scale-90 origin-top-left">
                                    <StatusBadge status={job.status} />
                                </div>
                            </div>
                            
                            {/* Progress Bar בהיר */}
                            <div className="pr-2">
                                <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <div className={`h-full rounded-full transition-all duration-1000 ease-out ${
                                        job.status === 'completed' ? 'bg-emerald-500 w-full' :
                                        job.status === 'analyzing' ? 'bg-purple-500 w-3/4' :
                                        job.status === 'scraped' ? 'bg-blue-500 w-1/2' : 
                                        'bg-blue-400 w-1/4 animate-pulse'
                                    }`}></div>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
      </div>
    </div>
  );
};

export default AddJobsTab;