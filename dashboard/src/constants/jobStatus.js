// סטטוסי הצינור (resolve -> scrape -> AI), מקור אחד לכל הדשבורד.
// חייב להתאים ל-JOB_STATUSES ב-src/db/postgres.py: כל סטטוס בדיוק בקבוצה אחת.
// tests/test_dashboard_statuses.py בודק את זה - סטטוס חדש בשרת שלא נוסף כאן יכשיל את הבדיקה
// (כך FAILED_RESOLVE "נעלם" מהממשק: הוא לא הופיע באף רשימת סינון).

// בעיבוד: ה-workers עוד עובדים על המשרה (הדשבורד מרענן כל עוד יש כאלה)
export const PROCESSING_STATUSES = ['NEW', 'PENDING_RESOLVE', 'RESOLVING', 'WAITING_FOR_SCRAPE', 'SCRAPING', 'WAITING_FOR_AI', 'ANALYZING'];

// נכשל / דורש פעולה מהמשתמש
export const FAILED_STATUSES = ['FAILED_RESOLVE', 'FAILED_SCRAPE', 'FAILED_ANALYSIS', 'NO_DATA', 'DUPLICATE'];

// הסתיים בהצלחה
export const DONE_STATUSES = ['COMPLETED'];

// כישלונות שבהם אין תיאור משרה - המודאל נפתח ישר במצב הדבקת טקסט ידנית
export const NEEDS_MANUAL_CONTENT_STATUSES = ['FAILED_RESOLVE', 'FAILED_SCRAPE', 'NO_DATA'];

export const FAILED_STATUS_LABELS = {
  FAILED_RESOLVE: 'נכשל בפענוח הקישור',
  FAILED_SCRAPE: 'נכשל בסריקה',
  FAILED_ANALYSIS: 'נכשל בניתוח AI',
  NO_DATA: 'אין מידע',
  DUPLICATE: 'משרה כפולה (כבר קיימת במערכת)',
};

// השלב בצינור של כל סטטוס - לסיכום "איפה כל קישור עומד" בניטור החי
export const STATUS_STAGE = {
  NEW: 'resolve',
  PENDING_RESOLVE: 'resolve',
  RESOLVING: 'resolve',
  WAITING_FOR_SCRAPE: 'scrape',
  SCRAPING: 'scrape',
  WAITING_FOR_AI: 'ai',
  ANALYZING: 'ai',
  COMPLETED: 'done',
  FAILED_RESOLVE: 'failed',
  FAILED_SCRAPE: 'failed',
  FAILED_ANALYSIS: 'failed',
  NO_DATA: 'failed',
  DUPLICATE: 'failed',
};
export const jobStage = (status) => STATUS_STAGE[status] || 'resolve';

export const isProcessing = (status) => PROCESSING_STATUSES.includes(status);
export const isFailed = (status) => FAILED_STATUSES.includes(status);
// משרות שמוצגות בלשונית ההזנה: בעיבוד או נכשלו
export const isInPipeline = (status) => isProcessing(status) || isFailed(status);
export const needsManualContent = (status) => NEEDS_MANUAL_CONTENT_STATUSES.includes(status);

// סטטוסים שבהם worker עובד על המשרה ממש עכשיו (לעומת ממתינה בתור) - לחיווי "עובד" מול "ממתין"
export const WORKING_STATUSES = ['RESOLVING', 'SCRAPING', 'ANALYZING'];
export const isWorking = (status) => WORKING_STATUSES.includes(status);

// באיזה שלב בצינור משרה נכשלה - כדי לסמן את הצעד הנכון ב-ProcessingTrack
export const FAILED_AT_STAGE = {
  FAILED_RESOLVE: 'resolve',
  DUPLICATE: 'resolve',
  FAILED_SCRAPE: 'scrape',
  NO_DATA: 'scrape',
  FAILED_ANALYSIS: 'ai',
};

// תוויות קצרות לכל סטטוס בצינור (שורת הניטור)
export const PIPELINE_STATUS_LABELS = {
  NEW: 'בתור',
  PENDING_RESOLVE: 'ממתין לפענוח',
  RESOLVING: 'מפענח קישור',
  WAITING_FOR_SCRAPE: 'ממתין לסריקה',
  SCRAPING: 'סורק',
  WAITING_FOR_AI: 'ממתין לניתוח',
  ANALYZING: 'מנתח',
  COMPLETED: 'הושלם',
  FAILED_RESOLVE: 'הפענוח נכשל',
  FAILED_SCRAPE: 'הסריקה נכשלה',
  FAILED_ANALYSIS: 'הניתוח נכשל',
  NO_DATA: 'אין מידע',
  DUPLICATE: 'כבר קיימת',
};
