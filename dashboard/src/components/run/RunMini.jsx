import React from 'react';
import { runSummary } from '../../utils/queueView';
import { runCounts } from '../../utils/jobView';

// פס הריצה: כמה הושלמו / נכשלו / בעיבוד, כחלוקה של שלם אחד (segmented bar דק)
export const RunBar = ({ summary, height = 'h-1.5' }) => {
  const processing = summary.resolve + summary.scrape + summary.ai;
  const parts = [
    { key: 'done', n: summary.done, cls: 'bg-go-fill' },
    { key: 'failed', n: summary.failed, cls: 'bg-danger-fill' },
    { key: 'processing', n: processing, cls: 'bg-accent-soft' },
  ].filter((p) => p.n > 0);
  return (
    <div
      className={`flex gap-0.5 ${height}`}
      role="img"
      aria-label={`${summary.done} הושלמו, ${summary.failed} נכשלו, ${processing} בעיבוד`}
    >
      {parts.map((p) => (
        <span key={p.key} className={`${p.cls} first:rounded-s-full last:rounded-e-full transition-[flex-grow] duration-500`} style={{ flexGrow: p.n, flexBasis: 0 }} />
      ))}
      {parts.length === 0 && <span className="flex-1 rounded-full bg-line" />}
    </div>
  );
};

// בסרגל הצד: מצב הריצה במבט אחד, ולחיצה פותחת את הקליטה
const RunMini = ({ runJobs, onOpen }) => {
  const summary = runSummary(runJobs);
  const c = runCounts(summary);
  return (
    <button
      type="button"
      onClick={onOpen}
      className="text-start bg-surface rounded-xl shadow-[0_0_0_1px_var(--line)] p-3.5 flex flex-col gap-2.5 hover:shadow-[0_0_0_1px_var(--line-strong)] transition-shadow"
    >
      <span className="flex items-center justify-between">
        <span className="text-[13px] font-semibold">הריצה האחרונה</span>
        <span className="text-xs text-ink-3 num">{summary.total ? `${summary.total} קישורים` : 'אין'}</span>
      </span>
      {summary.total > 0 ? (
        <>
          <RunBar summary={summary} />
          <span className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-ink-2" aria-live="polite">
            {c.processing > 0 && <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-accent pulse-dot" aria-hidden />{c.processing} בעיבוד</span>}
            {c.done > 0 && <span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-go-fill" aria-hidden />{c.done} הושלמו</span>}
            {c.failed > 0 && <span className="flex items-center gap-1.5 text-danger font-semibold"><span className="size-2 rounded-full bg-danger-fill" aria-hidden />{c.failed} נכשל{c.failed > 1 ? 'ו' : ''}</span>}
          </span>
        </>
      ) : (
        <span className="text-xs text-ink-3">שום קישור לא נכנס בשעה האחרונה</span>
      )}
    </button>
  );
};

export default RunMini;
