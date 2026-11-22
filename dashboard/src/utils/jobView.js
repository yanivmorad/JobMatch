// איך משרה מוצגת: כותרת נקייה, פסק דין, רצועת ציון, תאריכים.
// לוגיקה טהורה בלי React - כל הקומפוננטות משתמשות באותם כללים.
import { isPlaceholder, jobDisplayName } from './queueView.js';

// --- ציון: כלל אחד לכל הדשבורד (קודם: 85/80/70/50 במקומות שונים) ---
export const SCORE_BANDS = {
  strong: { min: 70, label: 'התאמה חזקה', fill: 'bg-go-fill', track: 'bg-go-soft', text: 'text-go' },
  partial: { min: 50, label: 'התאמה חלקית', fill: 'bg-warn-fill', track: 'bg-warn-soft', text: 'text-warn' },
  weak: { min: 0, label: 'התאמה חלשה', fill: 'bg-weak-fill', track: 'bg-weak-soft', text: 'text-weak' },
};

export const scoreBand = (score) => {
  const s = Number(score);
  if (!Number.isFinite(s)) return null;
  if (s >= SCORE_BANDS.strong.min) return 'strong';
  if (s >= SCORE_BANDS.partial.min) return 'partial';
  return 'weak';
};

export const hasScore = (job) => job?.suitability_score !== null && job?.suitability_score !== undefined;

// --- פסק הדין של ה-AI ("להגיש" / "לא להגיש") ---
export const verdictOf = (job) => {
  const r = String(job?.recommendation || '').trim();
  if (!r) return 'none';
  if (r.startsWith('לא')) return 'no';
  if (r.startsWith('להגיש')) return 'yes';
  return 'other';
};

// --- כותרת ---
// "🔥 דרוש/ה Junior QA" -> "Junior QA". פתיחים של הודעות גיוס שלא אומרים כלום על המשרה.
const OPENER_RE = /^(?:[\p{Extended_Pictographic}\p{Emoji_Presentation}️‍\s*•·\-–|:!]+)?(?:(?:דרוש(?:ים|ות|\/ה|\/ות|ה)?|מגייסים|מחפשים|hiring|we'?re hiring)\s*[:!\-–]?\s*)?/iu;
export const cleanTitle = (title) => {
  if (isPlaceholder(title)) return null;
  const cleaned = String(title).replace(OPENER_RE, '').trim();
  return cleaned || String(title).trim();
};

export const cleanCompany = (company) => (isPlaceholder(company) ? null : String(company).trim());

const hostOf = (url) => {
  try {
    const u = new URL(url);
    return /^https?:$/.test(u.protocol) ? u.hostname.replace(/^www\./, '') : '';
  } catch {
    return '';
  }
};

// כותרת ראשית + שורה משנית, עם נפילה חכמה כשהכותרת חסרה ("Unknown")
export const jobHeading = (job) => {
  const title = cleanTitle(job.job_title);
  const company = cleanCompany(job.company);
  const host = hostOf(job.source_url || job.url);
  if (title) return { title, sub: company || host || null, titleIsUrl: false };
  if (company) return { title: company, sub: host || null, titleIsUrl: false };
  if (host) {
    const path = (() => {
      try { return new URL(job.source_url || job.url).pathname.replace(/\/$/, ''); } catch { return ''; }
    })();
    return { title: `${host}${path}`, sub: 'כותרת לא זוהתה', titleIsUrl: true };
  }
  return { title: jobDisplayName(job), sub: null, titleIsUrl: false };
};

export const jobHost = (job) => hostOf(job.source_url || job.url);
export const isManualJob = (job) => !job?.url?.includes('http');

// --- חוסמים ---
const asList = (v) => (Array.isArray(v) ? v.filter((x) => x && String(x).trim()) : []);
export const blockersOf = (job) => asList(job?.showstoppers);
export const gapsOf = (job) => asList(job?.gap_analysis);

// שורת הסיבה בשורת רשימה: החוסם הראשון, או "אין חוסמים · סיכוי קבלה N%"
export const reasonLine = (job) => {
  const b = blockersOf(job);
  if (b.length) return { kind: 'blocker', text: b[0], more: b.length - 1 };
  const p = job?.acceptance_probability;
  return { kind: 'clear', text: p !== null && p !== undefined ? `אין חוסמים · סיכוי קבלה ${p}%` : 'אין חוסמים', more: 0 };
};

// --- מיון לבדיקה: מומלצות קודם, ואז ציון, ואז id (סדר יציב ברענון) ---
const VERDICT_RANK = { yes: 0, other: 1, none: 2, no: 3 };
export const sortForReview = (jobs) =>
  [...jobs].sort((a, b) =>
    (VERDICT_RANK[verdictOf(a)] - VERDICT_RANK[verdictOf(b)]) ||
    ((b.suitability_score ?? -1) - (a.suitability_score ?? -1)) ||
    ((Number(b.id) || 0) - (Number(a.id) || 0)));

// --- תאריכים ---
const dayFmt = new Intl.DateTimeFormat('he-IL', { day: 'numeric', month: 'numeric' });
const fullFmt = new Intl.DateTimeFormat('he-IL', { day: 'numeric', month: 'numeric', year: 'numeric' });
export const shortDate = (iso, now = Date.now()) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.getFullYear() === new Date(now).getFullYear() ? dayFmt.format(d) : fullFmt.format(d);
};

export const relativeTime = (iso, now = Date.now()) => {
  if (!iso) return '';
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '';
  const sec = Math.max(0, Math.round((now - t) / 1000));
  if (sec < 45) return 'עכשיו';
  const min = Math.round(sec / 60);
  if (min < 60) return `לפני ${min} דק׳`;
  const h = Math.round(min / 60);
  if (h < 24) return h === 1 ? 'לפני שעה' : `לפני ${h} שעות`;
  const days = Math.round(h / 24);
  if (days === 1) return 'אתמול';
  if (days < 30) return `לפני ${days} ימים`;
  return shortDate(iso, now);
};

export const daysSince = (iso, now = Date.now()) => {
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? null : Math.floor((now - t) / 86400000);
};

export const isSameDay = (iso, now = Date.now()) => {
  if (!iso) return false;
  const d = new Date(iso);
  const n = new Date(now);
  return d.getFullYear() === n.getFullYear() && d.getMonth() === n.getMonth() && d.getDate() === n.getDate();
};

export const jobKey = (job) => job.id ?? job.url;

// כמה הושלמו / נכשלו / בעיבוד, מתוך runSummary
export const runCounts = (summary) => ({
  done: summary.done,
  failed: summary.failed,
  processing: summary.resolve + summary.scrape + summary.ai,
});
