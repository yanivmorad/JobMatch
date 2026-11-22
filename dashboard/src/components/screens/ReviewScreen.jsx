import React, { useRef, useState } from 'react';
import { Check, Inbox, Plus, SearchX, X } from 'lucide-react';
import JobRow, { JobRowSkeleton } from '../job/JobRow';
import JobDetail from '../job/JobDetail';
import Dialog from '../ui/Dialog';
import Button from '../ui/Button';
import { EmptyState } from '../ui/Feedback';
import { useIsDesktop } from '../../hooks/useMediaQuery';
import { jobHeading, jobKey, sortForReview, verdictOf } from '../../utils/jobView';

const GROUPS = [
  { id: 'yes', label: 'מומלץ להגיש', icon: Check, cls: 'text-go', match: (v) => v === 'yes' || v === 'other' },
  { id: 'none', label: 'ללא המלצה', icon: null, cls: 'text-ink-2', match: (v) => v === 'none' },
  { id: 'no', label: 'לא מומלץ', icon: X, cls: 'text-ink-2', match: (v) => v === 'no' },
];

const FilterPill = ({ active, onClick, children }) => (
  <button
    type="button"
    aria-pressed={active}
    onClick={onClick}
    className={`h-8 px-3.5 rounded-full text-[13px] whitespace-nowrap transition-colors ${active ? 'bg-ink text-ink-inverse font-semibold' : 'bg-surface border border-line-strong text-ink hover:bg-hover'}`}
  >
    {children}
  </button>
);

// לבדיקה: רשימה ממוינת (מומלצות, ואז ציון) + פרט. בדסקטופ זה לצד זה, בנייד הפרט נפתח כגיליון.
const ReviewScreen = ({ jobs, loading, now, selection, onSelect, onAction, onDelete, onUpdateStatus, onRetry, onNavigate, searching }) => {
  const isDesktop = useIsDesktop();
  const [filter, setFilter] = useState('all');
  const [sheetOpen, setSheetOpen] = useState(false);
  const rowRefs = useRef(new Map());

  const sorted = sortForReview(jobs);
  const recommended = sorted.filter((j) => verdictOf(j) === 'yes');
  const visible = filter === 'yes' ? recommended : sorted;

  const selectedJob = visible.find((j) => jobKey(j) === selection) || (isDesktop ? visible[0] : null);
  const selectedKey = selectedJob ? jobKey(selectedJob) : null;

  const select = (job) => {
    onSelect(jobKey(job));
    if (!isDesktop) setSheetOpen(true);
  };

  const onListKey = (e) => {
    if (!['ArrowDown', 'ArrowUp'].includes(e.key) || !visible.length) return;
    e.preventDefault();
    const i = visible.findIndex((j) => jobKey(j) === selectedKey);
    const next = visible[e.key === 'ArrowDown' ? Math.min(visible.length - 1, i + 1) : Math.max(0, i - 1)];
    onSelect(jobKey(next));
    rowRefs.current.get(jobKey(next))?.focus();
  };

  // אחרי החלטה (הגשתי / לא רלוונטי / מחיקה): עוברים למשרה הבאה ברשימה
  const onDecided = (job) => {
    const i = visible.findIndex((j) => jobKey(j) === jobKey(job));
    const next = visible[i + 1] || visible[i - 1];
    if (next && jobKey(next) !== jobKey(job)) onSelect(jobKey(next));
    else {
      onSelect(null);
      setSheetOpen(false);
    }
  };

  const detail = selectedJob && (
    <JobDetail
      key={selectedKey}
      job={selectedJob}
      context="review"
      layout={isDesktop ? 'pane' : 'sheet'}
      onAction={onAction}
      onDelete={onDelete}
      onUpdateStatus={onUpdateStatus}
      onRetry={onRetry}
      onDecided={onDecided}
    />
  );

  if (!loading && jobs.length === 0) {
    return searching ? (
      <EmptyState icon={SearchX} title="לא נמצאו משרות לבדיקה" className="flex-1">נסה מילה אחרת, או נקה את החיפוש.</EmptyState>
    ) : (
      <EmptyState
        icon={Check}
        tone="go"
        title="אין משרות שמחכות להחלטה"
        className="flex-1"
        action={<Button variant="primary" onClick={() => onNavigate('add')}><Plus size={16} aria-hidden />הוספת משרות</Button>}
      >
        כל מה שנותח כבר הוגש או נסגר. משרות חדשות יופיעו כאן מיד אחרי הניתוח.
      </EmptyState>
    );
  }

  return (
    <div className="flex-1 min-h-0 flex lg:h-full">
      <section aria-label="רשימת משרות לבדיקה" className="w-full lg:w-[440px] xl:w-[500px] shrink-0 lg:border-e border-line flex flex-col min-h-0">
        <div className="flex items-center gap-1.5 px-5 max-sm:px-4 py-3 border-b border-line" role="group" aria-label="סינון">
          <FilterPill active={filter === 'all'} onClick={() => setFilter('all')}>הכל · <span className="num">{sorted.length}</span></FilterPill>
          <FilterPill active={filter === 'yes'} onClick={() => setFilter('yes')}>מומלצות · <span className="num">{recommended.length}</span></FilterPill>
          <span className="flex-1" />
          <span className="text-xs text-ink-3 max-sm:hidden">ממוין לפי המלצה וציון</span>
        </div>
        <div className="flex-1 min-h-0 lg:scroll-area pb-4" onKeyDown={onListKey}>
          {loading && Array.from({ length: 7 }, (_, i) => <JobRowSkeleton key={i} />)}
          {!loading && visible.length === 0 && (
            <EmptyState icon={Inbox} title="אין משרות מומלצות כרגע">
              ה-AI לא המליץ על אף אחת מ-{sorted.length} המשרות. אפשר לעבור עליהן ב"הכל".
            </EmptyState>
          )}
          {!loading && GROUPS.map((g) => {
            const items = visible.filter((j) => g.match(verdictOf(j)));
            if (!items.length) return null;
            return (
              <div key={g.id} role="group" aria-label={`${g.label}, ${items.length}`}>
                <h2 className={`px-5 max-sm:px-4 pt-3.5 pb-1.5 text-xs font-semibold flex items-center gap-1.5 ${g.cls}`}>
                  {g.icon && <g.icon size={14} strokeWidth={2.6} aria-hidden />}
                  {g.label} · <span className="num">{items.length}</span>
                </h2>
                {items.map((j) => (
                  <JobRow
                    key={jobKey(j)}
                    ref={(el) => { if (el) rowRefs.current.set(jobKey(j), el); else rowRefs.current.delete(jobKey(j)); }}
                    job={j}
                    now={now}
                    selected={isDesktop && jobKey(j) === selectedKey}
                    onSelect={select}
                    showVerdict={g.id !== 'yes'}
                  />
                ))}
              </div>
            );
          })}
        </div>
      </section>

      {isDesktop ? (
        <article aria-label="פרטי המשרה" className="flex-1 min-w-0 bg-surface flex flex-col min-h-0">
          {loading ? (
            <div className="p-9 flex flex-col gap-4" aria-hidden>
              <span className="skeleton h-3 w-48" /><span className="skeleton h-7 w-96" /><span className="skeleton h-36 w-full rounded-lg" />
            </div>
          ) : detail}
        </article>
      ) : (
        <Dialog
          open={sheetOpen && Boolean(selectedJob)}
          onClose={() => setSheetOpen(false)}
          title={selectedJob ? jobHeading(selectedJob).title : ''}
          hideTitle
          variant="sheet"
        >
          {detail}
        </Dialog>
      )}
    </div>
  );
};

export default ReviewScreen;
