// "איפה כל קישור עומד": אילו משרות מוצגות בניטור החי, איך קוראים להן, ומתי לרענן את הרשימה.
// לוגיקה טהורה בלי React - נבדקת ב-tests/js/queue_view.test.mjs (מורץ מ-pytest).
//
// באג (ריצה אמיתית, 22.11): 8 קישורים נכנסו לתור בלי שהדשבורד ראה אותם. הרענון האוטומטי
// רץ רק כשברשימה שכבר נטענה הייתה משרה בעיבוד, כך שמשרות שנוספו מחוץ לדשבורד
// (תוסף, API, טאב / טלפון אחר, ובהמשך הבוט) לא הופיעו עד רענון ידני של הדף.
// וגם כשהן כן הופיעו: רק 4 ראשונות, בלי שם (company היה ה-URL הזמני), ומשרה שסיימה
// נעלמה מהניטור בלי לומר אם הצליחה או נכשלה.
import { isFailed, isProcessing, jobStage } from '../constants/jobStatus.js';

export const QUEUE_POLL_MS = 5000; // יש משרות בעיבוד
export const IDLE_POLL_MS = 15000; // אין - רק כדי לגלות משרות שנוספו מבחוץ
export const RECENT_RUN_MINUTES = 60; // משרה שסיימה נשארת בניטור שעה

// כמו PLACEHOLDER_VALUES / _MASKED_MARKERS ב-src/services/job_fields.py (בדיקה מוודאת שהן זהות)
export const PLACEHOLDER_VALUES = [
  '', 'unknown', 'identifying...', 'pending...', 'לא צוין', 'לא זוהה', 'משרה ידנית', 'n/a', 'none', 'null',
  'company', 'company | hireme', 'hireme', 'hiremetech', 'hiremetech.com', 'hire me tech',
];
export const MASKED_MARKERS = ['מוסתר', 'hidden by hiremetech'];

export const isPlaceholder = (value) => {
  if (value === null || value === undefined) return true;
  const v = String(value).trim().toLowerCase();
  return (
    PLACEHOLDER_VALUES.includes(v) ||
    /^(https?:\/\/|manual)/.test(v) ||
    MASKED_MARKERS.some(m => v.includes(m))
  );
};

// רק http(s): למשרה ידנית ה-url הוא manual://<uuid>, וה-hostname שלו הוא ה-uuid
const hostOf = (url) => {
  try {
    const parsed = new URL(url);
    return /^https?:$/.test(parsed.protocol) ? parsed.hostname.replace(/^www\./, '') : '';
  } catch {
    return '';
  }
};

// "Junior QA · Supercom" / רק אחד מהם / האתר (comeet.com) כשעוד לא ידוע כלום
export const jobDisplayName = (job) => {
  const title = isPlaceholder(job.job_title) ? null : String(job.job_title).trim();
  const company = isPlaceholder(job.company) ? null : String(job.company).trim();
  if (title && company) return `${title} · ${company}`;
  return title || company || hostOf(job.source_url || job.url) || 'משרה בתהליך';
};

const minutesSince = (iso, now) => {
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? Infinity : (now - t) / 60000;
};

// בניטור: כל משרה בעיבוד, ומשרה שסיימה (הצליחה / נכשלה) בשעה האחרונה.
// הושלמה -> לפי analyzed_at (לא updated_at: שינוי סטטוס הגשה / תחזוקה מעדכנים אותו גם למשרות ישנות).
export const isInCurrentRun = (job, now, windowMinutes = RECENT_RUN_MINUTES) => {
  if (isProcessing(job.status)) return true;
  let finishedAt = null;
  if (job.status === 'COMPLETED') finishedAt = job.analyzed_at;
  else if (isFailed(job.status)) finishedAt = job.updated_at || job.created_at;
  if (!finishedAt) return false;
  return minutesSince(finishedAt, now) <= windowMinutes;
};

// לפי סדר ההכנסה (id), כך שכל שורה נשארת במקומה ורק המצב שלה מתחלף
export const currentRun = (jobs, now, windowMinutes = RECENT_RUN_MINUTES) =>
  jobs.filter(j => isInCurrentRun(j, now, windowMinutes)).sort((a, b) => (a.id ?? 0) - (b.id ?? 0));

export const runSummary = (runJobs) => {
  const summary = { total: runJobs.length, resolve: 0, scrape: 0, ai: 0, done: 0, failed: 0 };
  for (const j of runJobs) summary[jobStage(j.status)] += 1;
  return summary;
};

export const pollDelay = (hasProcessing) => (hasProcessing ? QUEUE_POLL_MS : IDLE_POLL_MS);

// snapshot = GET /api/jobs/queue -> {counts: {STATUS: n}, version}
// בדיקה ראשונה (אין גרסה קודמת): משווים לרשימה שנטענה - משרות שנוספו בינתיים לא יפוספסו.
export const shouldRefetch = (prevVersion, snapshot, jobs) => {
  if (!snapshot || snapshot.version === undefined || snapshot.version === null) return false;
  if (prevVersion === null || prevVersion === undefined) {
    const counts = snapshot.counts || {};
    const total = Object.values(counts).reduce((a, n) => a + n, 0);
    const processing = Object.entries(counts)
      .filter(([status]) => isProcessing(status))
      .reduce((a, [, n]) => a + n, 0);
    const localProcessing = jobs.filter(j => isProcessing(j.status)).length;
    return total !== jobs.length || processing !== localProcessing;
  }
  return snapshot.version !== prevVersion;
};
