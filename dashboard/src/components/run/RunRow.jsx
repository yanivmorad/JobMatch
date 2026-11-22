import React from 'react';
import { AlertCircle, Edit3, ExternalLink, Loader2, RefreshCw, Trash2 } from 'lucide-react';
import ProcessingTrack from '../ui/ProcessingTrack';
import Button from '../ui/Button';
import { FAILED_STATUS_LABELS, PIPELINE_STATUS_LABELS, isWorking, needsManualContent } from '../../constants/jobStatus';
import { cleanTitle, cleanCompany, jobHost, scoreBand, SCORE_BANDS } from '../../utils/jobView';
import { jobDisplayName } from '../../utils/queueView';

const runName = (job) => {
  const title = cleanTitle(job.job_title);
  const company = cleanCompany(job.company);
  if (title && company) return `${title} · ${company}`;
  return title || company || jobHost(job) || jobDisplayName(job);
};

// שורה בניטור החי: נקודות הצינור, שם, ומצב. גובה קבוע; שינוי מצב מתחלף ברכות במקום.
export const RunRow = ({ job, onOpen }) => {
  const done = job.status === 'COMPLETED';
  const band = done ? scoreBand(job.suitability_score) : null;
  const label = done && band ? `ציון ${job.suitability_score}` : PIPELINE_STATUS_LABELS[job.status] || 'מעבד';
  const content = (
    <>
      <ProcessingTrack status={job.status} />
      <span className="flex-1 min-w-0 truncate font-medium" dir="auto">{runName(job)}</span>
      <span
        key={job.status}
        className={`state-fade text-xs whitespace-nowrap ${done ? 'font-semibold text-ink' : isWorking(job.status) ? 'font-semibold text-accent' : 'text-ink-2'}`}
      >
        {done && band && <span className={`inline-block size-2 rounded-full me-1.5 ${SCORE_BANDS[band].fill}`} aria-hidden />}
        {label}
      </span>
    </>
  );
  const cls = 'w-full h-11 flex items-center gap-3 px-3.5 rounded-md text-start';
  return done && onOpen ? (
    <button type="button" onClick={() => onOpen(job)} className={`${cls} hover:bg-hover`} data-testid="queue-item" data-status={job.status}>{content}</button>
  ) : (
    <div className={cls} data-testid="queue-item" data-status={job.status}>{content}</div>
  );
};

// משרה שנכשלה: מוצמדת לראש הניטור, עם הסבר ופעולות גלויות תמיד
export const FailedRunItem = ({ job, onFix, onRetry, onRescan, onDelete, busy }) => {
  const duplicate = job.status === 'DUPLICATE';
  const manual = needsManualContent(job.status);
  return (
    <div className={`rounded-[10px] px-3.5 py-3 flex flex-col gap-2.5 ${duplicate ? 'bg-warn-soft' : 'bg-danger-soft'}`} data-testid="queue-item" data-status={job.status}>
      <div className="flex items-center gap-3">
        <ProcessingTrack status={job.status} />
        <span className="flex-1 min-w-0 truncate font-semibold" dir="auto">{runName(job)}</span>
        <span className={`text-xs font-semibold whitespace-nowrap ${duplicate ? 'text-warn' : 'text-danger'}`}>{PIPELINE_STATUS_LABELS[job.status]}</span>
      </div>
      <p className="text-[13px] text-ink leading-relaxed break-words">
        {duplicate
          ? (job.error_log || 'המשרה כבר קיימת במערכת (קישור זהה או חלופי).')
          : <>{job.error_log || FAILED_STATUS_LABELS[job.status]}{manual && ' אם יש לך את טקסט המשרה, אפשר להדביק אותו ולנתח ידנית.'}</>}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {duplicate ? (
          <Button size="sm" variant="primary" onClick={() => onRescan(job.url)} disabled={busy}><RefreshCw size={14} aria-hidden />סריקה מחדש</Button>
        ) : (
          <>
            <Button size="sm" variant="primary" onClick={() => onFix(job)}><Edit3 size={14} aria-hidden />הדבקת טקסט ידנית</Button>
            <Button size="sm" variant="secondary" onClick={() => onRetry(job.url)} disabled={busy}>
              {busy ? <Loader2 size={14} className="animate-spin" aria-hidden /> : <RefreshCw size={14} aria-hidden />}נסה שוב
            </Button>
          </>
        )}
        {job.url?.startsWith('http') && (
          <a href={job.url} target="_blank" rel="noopener noreferrer" className="text-[13px] text-accent hover:underline inline-flex items-center gap-1 px-1">
            לקישור<ExternalLink size={12} aria-hidden />
          </a>
        )}
        <span className="flex-1" />
        <Button size="iconSm" variant="ghost" onClick={() => onDelete(job)} aria-label="מחיקת המשרה" title="מחיקה">
          <Trash2 size={15} aria-hidden />
        </Button>
      </div>
    </div>
  );
};

// קישור שנדחה כי כבר נסרק בעבר (מתשובת השרת על השליחה)
export const DuplicateLinkItem = ({ dup, onRescan, onDismiss }) => (
  <div className="rounded-[10px] px-3.5 py-3 flex flex-col gap-2 bg-warn-soft">
    <div className="flex items-center gap-2">
      <AlertCircle size={15} className="text-warn shrink-0" aria-hidden />
      <span className="text-xs font-semibold text-warn">נסרק בעבר</span>
      <span className="flex-1 min-w-0 truncate font-mono text-xs text-ink-2" dir="ltr" title={dup.url}>{dup.url}</span>
    </div>
    {dup.date && <p className="text-[13px] text-ink">נסרק לאחרונה: <span className="num">{dup.date}</span></p>}
    <div className="flex gap-2">
      <Button size="sm" variant="primary" onClick={() => { onRescan(dup.url); onDismiss(dup.url); }}><RefreshCw size={14} aria-hidden />סריקה מחדש</Button>
      <Button size="sm" variant="ghost" onClick={() => onDismiss(dup.url)}>התעלמות</Button>
    </div>
  </div>
);
