import React from 'react';
import {
  Clock, Search, Sparkles, Brain, Loader2,
  Link as LinkIcon, RefreshCw, ExternalLink,
  AlertCircle, CheckCircle, XCircle
} from 'lucide-react';
import { FAILED_STATUS_LABELS, isFailed } from '../constants/jobStatus';
import { jobDisplayName, runSummary } from '../utils/queueView';
import { getSuitabilityScoreStyle } from '../utils/jobHelpers';

// פונקציית עזר לקיצור טקסט חכם
const truncateText = (text, maxLength = 35) => {
  if (!text) return '';
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
};

const getStatusConfig = (job) => {
  const { status } = job;
  switch (status) {
    case 'NEW':
    case 'PENDING_RESOLVE':
      return {
        text: 'ממתין לפענוח קישור',
        color: 'bg-amber-500',
        lightColor: 'bg-amber-50',
        textColor: 'text-amber-600',
        icon: <Clock size={16} />,
        loading: true,
        percentage: 10
      };
    case 'RESOLVING':
      return {
        text: 'מפענח קישור',
        color: 'bg-amber-600',
        lightColor: 'bg-amber-50',
        textColor: 'text-amber-700',
        icon: <Search size={16} className="animate-pulse" />,
        loading: true,
        percentage: 20
      };
    case 'WAITING_FOR_SCRAPE':
      return {
        text: 'ממתין לסריקה',
        color: 'bg-blue-400',
        lightColor: 'bg-blue-50',
        textColor: 'text-blue-600',
        icon: <Clock size={16} />,
        loading: true,
        percentage: 40
      };
    case 'SCRAPING':
      return {
        text: 'סורק תוכן',
        color: 'bg-blue-500',
        lightColor: 'bg-blue-50',
        textColor: 'text-blue-600',
        icon: <Search size={16} className="animate-pulse" />,
        loading: true,
        percentage: 55
      };
    case 'WAITING_FOR_AI':
      return {
        text: 'ממתין ל-AI',
        color: 'bg-purple-500',
        lightColor: 'bg-purple-50',
        textColor: 'text-purple-600',
        icon: <Sparkles size={16} />,
        loading: true,
        percentage: 75
      };
    case 'ANALYZING':
      return {
        text: 'מנתח משרה',
        color: 'bg-indigo-600',
        lightColor: 'bg-indigo-50',
        textColor: 'text-indigo-600',
        icon: <Brain size={16} className="animate-pulse" />,
        loading: true,
        percentage: 90
      };
    case 'COMPLETED':
      return {
        text: 'הושלם',
        color: 'bg-emerald-500',
        lightColor: 'bg-emerald-50',
        textColor: 'text-emerald-600',
        icon: <CheckCircle size={16} />,
        loading: false,
        percentage: 100
      };
    case 'DUPLICATE':
      return {
        text: 'משרה כפולה (כבר קיימת במערכת)',
        color: 'bg-amber-400',
        lightColor: 'bg-amber-50',
        textColor: 'text-amber-600',
        icon: <AlertCircle size={16} />,
        loading: false,
        percentage: 100
      };
    default:
      // נכשל (פענוח / סריקה / ניתוח / אין מידע): קודם הוצג כאן "מעבד..." עם ספינר
      if (isFailed(status)) {
        return {
          text: FAILED_STATUS_LABELS[status] || 'נכשל',
          color: 'bg-rose-500',
          lightColor: 'bg-rose-50',
          textColor: 'text-rose-600',
          icon: <XCircle size={16} />,
          loading: false,
          percentage: 100
        };
      }
      return {
        text: 'מעבד...',
        color: 'bg-gray-400',
        lightColor: 'bg-gray-50',
        textColor: 'text-gray-500',
        icon: <Loader2 size={16} className="animate-spin" />,
        loading: true,
        percentage: 5
      };
  }
};

const QueueItem = ({ job, onRetry }) => {
  const config = getStatusConfig(job);
  // קודם: company, ואם הוא "Unknown" - job_title. למשרה חדשה company הוא ה-URL הזמני,
  // אז הוצג URL קטוע. עכשיו: שם המשרה · החברה, או האתר כשעוד לא ידוע כלום
  const displayName = jobDisplayName(job);
  const failed = isFailed(job.status) && job.status !== 'DUPLICATE';
  const score = job.status === 'COMPLETED' ? job.suitability_score : null;
  const canRetry = onRetry && job.status !== 'COMPLETED';

  return (
    <div
      className="group relative bg-white rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden"
      data-testid="queue-item"
      data-status={job.status}
    >

      {/* פס התקדמות דינמי בתחתית */}
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-slate-100/50">
        <div
          className={`h-full ${config.color} transition-all duration-1000 ease-in-out rounded-r-full`}
          style={{ width: `${config.percentage}%` }}
        ></div>
        {config.loading && (
          <div className="absolute inset-0 w-full h-full bg-white/20 animate-pulse"></div>
        )}
      </div>

      <div className="flex items-stretch h-full">
        {/* פס צבע צידי המעיד על סטטוס */}
        <div className={`w-1.5 shrink-0 ${config.color}`}></div>

        <div className="flex-1 p-3.5 flex items-center justify-between gap-3 min-w-0">

          {/* אזור המידע המרכזי */}
          <div className="flex flex-col min-w-0 gap-1">
            <div className="flex items-center gap-2">
              <span className={`${config.lightColor} ${config.textColor} p-1.5 rounded-lg shrink-0`}>
                {config.icon}
              </span>

              {/* כותרת עם טיפול בחריגה */}
              <h4
                className="font-bold text-slate-800 text-sm truncate leading-tight cursor-help"
                title={displayName} // Tooltip עם השם המלא
              >
                {truncateText(displayName, 40)}
              </h4>
            </div>

            <div className="flex items-center gap-3 pr-9">
              <span className={`text-[10px] font-bold tracking-wide ${config.textColor}`}>
                {config.text}
              </span>

              {score !== null && score !== undefined && (
                <span className={`text-[10px] font-black px-1.5 py-0.5 rounded border ${getSuitabilityScoreStyle(score)}`}>
                  ציון {score}
                </span>
              )}

              {job.url && (
                <a
                  href={job.source_url || job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[10px] text-slate-300 hover:text-blue-500 transition-colors truncate max-w-[150px]"
                  dir="ltr"
                  title={job.source_url || job.url}
                >
                  <LinkIcon size={10} />
                  <span className="truncate">link</span>
                  <ExternalLink size={8} />
                </a>
              )}
            </div>

            {failed && job.error_log && (
              <p className="pr-9 text-[11px] text-rose-700 leading-snug break-words" title={job.error_log}>
                {truncateText(job.error_log, 90)}
              </p>
            )}
          </div>

          {/* כפתור פעולה */}
          {canRetry && (
            <button
              onClick={() => onRetry(job.url)}
              className="p-2 rounded-lg text-slate-300 hover:bg-slate-50 hover:text-blue-500 transition-all opacity-0 group-hover:opacity-100 focus:opacity-100 shrink-0"
              title="אתחל משרה זו"
            >
              <RefreshCw size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// "8 קישורים: 5 הושלמו · 1 נכשל · 2 בסריקה" - איפה הריצה עומדת במבט אחד
const STAGE_CHIPS = [
  { key: 'done', label: 'הושלמו', one: 'הושלם', className: 'bg-emerald-50 text-emerald-700' },
  { key: 'failed', label: 'נכשלו', one: 'נכשל', className: 'bg-rose-50 text-rose-700' },
  { key: 'resolve', label: 'בפענוח', className: 'bg-amber-50 text-amber-700' },
  { key: 'scrape', label: 'בסריקה', className: 'bg-blue-50 text-blue-700' },
  { key: 'ai', label: 'ב-AI', className: 'bg-purple-50 text-purple-700' },
];

const RunSummary = ({ jobs }) => {
  const summary = runSummary(jobs);
  return (
    <div className="flex flex-col gap-2" data-testid="run-summary">
      <p className="text-xs font-bold text-slate-600">
        {summary.total} קישורים בריצה האחרונה
      </p>
      <div className="flex flex-wrap gap-1.5">
        {STAGE_CHIPS.filter(c => summary[c.key] > 0).map(c => (
          <span key={c.key} className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${c.className}`}>
            {summary[c.key]} {summary[c.key] === 1 && c.one ? c.one : c.label}
          </span>
        ))}
      </div>
    </div>
  );
};

export const ActiveQueueList = ({ activeQueue, onRetry, showSummary = false }) => {
  if (activeQueue.length === 0) {
    return (
      <div className="text-center py-8 border-2 border-dashed border-slate-100 rounded-xl bg-slate-50/50">
        <Loader2 className="mx-auto text-slate-300 mb-2 animate-spin-slow" size={24} />
        <p className="text-slate-400 text-sm italic">אין משימות בתור כרגע</p>
      </div>
    );
  }
  // לפי סדר ההכנסה: כל קישור נשאר במקומו ורק המצב שלו מתחלף
  const ordered = [...activeQueue].sort((a, b) => (a.id ?? 0) - (b.id ?? 0));

  return (
    <div className="flex flex-col gap-3 animate-in fade-in slide-in-from-bottom-2 duration-500">
      {showSummary && <RunSummary jobs={ordered} />}

      <div className="flex flex-col gap-2.5 max-h-[32rem] overflow-y-auto pl-1">
        {ordered.map(job => (
          <QueueItem key={job.id ?? job.url} job={job} onRetry={onRetry} />
        ))}
      </div>

      {!showSummary && activeQueue.length > 3 && (
        <div className="text-center mt-2">
          <p className="text-[10px] text-slate-400 font-medium">
            סה"כ {activeQueue.length} משרות בעיבוד
          </p>
        </div>
      )}
    </div>
  );
};
