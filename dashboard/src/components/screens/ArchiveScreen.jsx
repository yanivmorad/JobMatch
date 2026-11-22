import React, { useState } from 'react';
import { Archive, ChevronDown, RotateCcw, SearchX, Trash2 } from 'lucide-react';
import Button from '../ui/Button';
import Dialog from '../ui/Dialog';
import { RowScore } from '../ui/Score';
import { EmptyState, Menu, MenuItem } from '../ui/Feedback';
import { useConfirm } from '../../hooks/useConfirm';
import JobDetail from '../job/JobDetail';
import { AUTO_ARCHIVE_STATUSES, STATUS_CONFIG } from '../../constants/statusConfig';
import { jobHeading, jobKey, reasonLine, shortDate } from '../../utils/jobView';

// שינוי סטטוס ההגשה מהארכיון (כמו ה-select הקודם), עם הסבר מה יקרה
const StatusMenu = ({ job, onUpdateStatus }) => {
  const current = job.application_status || 'pending';
  return (
    <Menu
      label={`סטטוס: ${STATUS_CONFIG[current]?.label || current}. שינוי`}
      triggerClassName={`h-8 px-2.5 inline-flex items-center gap-1 rounded-md text-[13px] hover:bg-hover ${current === 'rejected' ? 'text-danger font-semibold' : 'text-ink-2'}`}
      trigger={<>{STATUS_CONFIG[current]?.label || current}<ChevronDown size={13} aria-hidden /></>}
    >
      {(close) => Object.entries(STATUS_CONFIG).map(([k, cfg]) => (
        <MenuItem
          key={k}
          close={close}
          current={k === current}
          tone={k === 'rejected' ? 'danger' : undefined}
          hint={AUTO_ARCHIVE_STATUSES.includes(k) ? 'נשאר בארכיון' : 'יוצא מהארכיון'}
          onSelect={() => k !== current && onUpdateStatus(job.url, k)}
        >
          {cfg.label}
        </MenuItem>
      ))}
    </Menu>
  );
};

const FILTERS = [
  { id: 'all', label: 'הכל' },
  { id: 'not_relevant', label: 'לא רלוונטי' },
  { id: 'ghosted', label: 'ללא מענה' },
  { id: 'rejected', label: 'דחייה' },
  { id: 'other', label: 'אחר' },
];
const CLOSED = ['not_relevant', 'ghosted', 'rejected'];

const ArchiveScreen = ({ jobs, now, loading, onRestore, onDelete, onUpdateStatus, onRetry, onClearHistory, searching }) => {
  const [filter, setFilter] = useState('all');
  const [openKey, setOpenKey] = useState(null);
  const [confirm, confirmEl] = useConfirm();

  const matches = (j, f) => (f === 'all' ? true : f === 'other' ? !CLOSED.includes(j.application_status) : j.application_status === f);
  const counts = Object.fromEntries(FILTERS.map((f) => [f.id, jobs.filter((j) => matches(j, f.id)).length]));
  const visible = jobs.filter((j) => matches(j, filter));
  const openJob = jobs.find((j) => jobKey(j) === openKey);

  const clear = async () => {
    const ok = await confirm({
      title: `למחוק לצמיתות את כל ${jobs.length} המשרות בארכיון?`,
      body: 'הניקוי מוחק כל משרה בארכיון, כולל "ללא מענה" ו"דחייה", ולא רק "לא רלוונטי". אי אפשר לבטל. משרות שמחכות לבדיקה והגשות פתוחות לא נמחקות.',
      confirmLabel: 'מחיקת הארכיון',
      danger: true,
    });
    if (ok) onClearHistory();
  };

  if (!loading && jobs.length === 0) {
    return searching
      ? <EmptyState icon={SearchX} title="אין בארכיון משרות שמתאימות לחיפוש" className="flex-1" />
      : <EmptyState icon={Archive} title="הארכיון ריק" className="flex-1">משרות שסימנת "לא רלוונטי", או שנסגרו בדחייה או בלי מענה, יופיעו כאן. אפשר להחזיר כל אחת ללוח.</EmptyState>;
  }

  return (
    <div className="px-7 max-sm:px-4 py-5 max-sm:py-4 flex flex-col gap-3.5">
      {confirmEl}
      <div role="group" aria-label="סינון לפי סיבת סגירה" className="flex gap-1.5 overflow-x-auto -mx-1 px-1 pb-1">
        {FILTERS.filter((f) => f.id === 'all' || counts[f.id] > 0).map((f) => (
          <button
            key={f.id}
            type="button"
            aria-pressed={filter === f.id}
            onClick={() => setFilter(f.id)}
            className={`h-8 px-3.5 rounded-full text-[13px] whitespace-nowrap ${filter === f.id ? 'bg-ink text-ink-inverse font-semibold' : 'bg-surface border border-line-strong hover:bg-hover'}`}
          >
            {f.label} · <span className="num">{counts[f.id]}</span>
          </button>
        ))}
      </div>

      <div className="bg-surface rounded-lg shadow-[0_0_0_1px_var(--line)] overflow-hidden">
        <div className="max-md:hidden grid grid-cols-[56px_minmax(0,1fr)_150px_80px_128px] gap-4 px-5 py-2.5 text-xs font-semibold text-ink-2 border-b border-line">
          <span>ציון</span><span>משרה</span><span>סטטוס</span><span>נותחה</span><span className="sr-only">פעולות</span>
        </div>
        <ul>
          {loading && Array.from({ length: 8 }, (_, i) => <li key={i} className="h-[60px] px-5 flex items-center gap-4 border-b border-line" aria-hidden><span className="skeleton w-8 h-6" /><span className="skeleton h-3 w-1/2" /></li>)}
          {!loading && visible.map((j) => {
            const { title, sub, titleIsUrl } = jobHeading(j);
            const reason = reasonLine(j);
            return (
              <li key={jobKey(j)} className="border-b border-line last:border-b-0 grid grid-cols-[56px_minmax(0,1fr)_128px] md:grid-cols-[56px_minmax(0,1fr)_150px_80px_128px] gap-x-4 items-center px-5 max-sm:px-3 max-sm:gap-x-2.5 min-h-[60px] py-2 hover:bg-hover">
                <RowScore score={j.suitability_score} size="sm" />
                <button type="button" onClick={() => setOpenKey(jobKey(j))} className="text-start min-w-0 flex flex-col rounded-sm">
                  <span className={`truncate ${titleIsUrl ? 'font-mono text-[13px] text-ink-2' : 'font-semibold'}`} dir="auto">{title}</span>
                  <span className="truncate text-xs text-ink-3" dir="auto">{[sub, reason.kind === 'blocker' ? `⊘ ${reason.text}` : reason.text].filter(Boolean).join(' · ')}</span>
                </button>
                <span className="max-md:hidden"><StatusMenu job={j} onUpdateStatus={onUpdateStatus} /></span>
                <span className="max-md:hidden num text-[13px] text-ink-3">{shortDate(j.analyzed_at || j.created_at, now)}</span>
                <span className="flex justify-end">
                  <Button size="sm" variant="secondary" onClick={() => onRestore(j, 'none')} aria-label={`החזרה ללוח: ${title}`}>
                    <RotateCcw size={14} aria-hidden /><span className="max-sm:hidden">החזרה ללוח</span>
                  </Button>
                </span>
              </li>
            );
          })}
        </ul>
      </div>

      {jobs.length > 0 && !searching && (
        <div className="flex flex-wrap items-center gap-3 px-4 py-3 rounded-[10px] border border-dashed border-line-strong">
          <span className="flex-1 min-w-60 text-[13px] text-ink-2">
            <strong className="text-ink font-semibold">ניקוי הארכיון</strong> · מוחק לצמיתות את כל {jobs.length} המשרות בארכיון. אי אפשר לבטל.
          </span>
          <Button size="sm" variant="danger" onClick={clear}><Trash2 size={14} aria-hidden />ניקוי…</Button>
        </div>
      )}

      <Dialog open={Boolean(openJob)} onClose={() => setOpenKey(null)} title={openJob ? jobHeading(openJob).title : ''} hideTitle variant="sheet">
        {openJob && (
          <div className="flex flex-col">
            <div className="px-5 max-sm:px-4 pb-2 flex items-center gap-2 text-[13px] text-ink-2">
              סטטוס: <StatusMenu job={openJob} onUpdateStatus={onUpdateStatus} />
            </div>
            <JobDetail
              job={openJob}
              context="archive"
              layout="sheet"
              onAction={async (job, action, data) => { const ok = await onRestore(job, action, data); if (ok && action === 'none') setOpenKey(null); return ok; }}
              onDelete={async (job) => { const ok = await onDelete(job); if (ok) setOpenKey(null); return ok; }}
              onUpdateStatus={onUpdateStatus}
              onRetry={onRetry}
            />
          </div>
        )}
      </Dialog>
    </div>
  );
};

export default ArchiveScreen;
