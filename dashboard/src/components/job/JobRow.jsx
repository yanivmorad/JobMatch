import React from 'react';
import { Ban } from 'lucide-react';
import { RowScore, VerdictBadge } from '../ui/Score';
import { jobHeading, reasonLine, shortDate, verdictOf } from '../../utils/jobView';

// שורת משרה שנותחה: ציון | כותרת, חברה · תאריך | שורת סיבה (החוסם הראשון)
// גובה קבוע, כך שרענון אוטומטי לא מזיז את הרשימה
const JobRow = React.forwardRef(function JobRow({ job, selected, onSelect, showVerdict = true, now, ...rest }, ref) {
  const { title, sub, titleIsUrl } = jobHeading(job);
  const reason = reasonLine(job);
  const date = shortDate(job.analyzed_at || job.created_at, now);
  return (
    <button
      ref={ref}
      type="button"
      onClick={() => onSelect(job)}
      aria-current={selected ? 'true' : undefined}
      className={`w-full h-[78px] flex gap-3.5 items-start text-start ps-5 pe-5 max-sm:px-4 py-3 border-s-[3px] transition-colors ${selected ? 'bg-surface border-accent' : 'border-transparent hover:bg-hover'} focus-visible:-outline-offset-2`}
      {...rest}
    >
      <RowScore score={job.suitability_score} />
      <span className="flex-1 min-w-0 flex flex-col gap-px">
        <span className={`truncate font-semibold ${titleIsUrl ? 'font-mono font-normal text-[13px] text-ink-2' : ''}`} dir="auto">{title}</span>
        <span className="truncate text-[13px] text-ink-2">
          <span dir="auto">{sub || 'חברה לא ידועה'}</span>{date && <> · <span className="num">{date}</span></>}
        </span>
        <span className="truncate text-xs text-ink-3">
          {reason.kind === 'blocker' && <Ban size={12} className="inline-block align-[-2px] me-1 text-danger" aria-label="חוסם:" />}
          <span dir="auto">{reason.text}</span>
          {reason.more > 0 && <span className="text-ink-3"> · עוד {reason.more}</span>}
        </span>
      </span>
      {showVerdict && verdictOf(job) === 'yes' && <span className="pt-0.5"><VerdictBadge job={job} /></span>}
    </button>
  );
});

export const JobRowSkeleton = () => (
  <div className="h-[78px] flex gap-3.5 px-5 py-3.5 border-s-[3px] border-transparent" aria-hidden>
    <span className="skeleton w-10 h-7" />
    <span className="flex-1 flex flex-col gap-2 pt-0.5">
      <span className="skeleton h-3 w-[64%]" />
      <span className="skeleton h-2.5 w-[38%] opacity-70" />
      <span className="skeleton h-2.5 w-[52%] opacity-50" />
    </span>
  </div>
);

export default JobRow;
