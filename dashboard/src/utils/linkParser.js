// מחלץ לינקים של משרות מטקסט חופשי (למשל הודעות מוואטסאפ/טלגרם),
// יחד עם הכותרת שמופיעה לפני כל לינק - אם יש.

const URL_REGEX = /https?:\/\/[^\s<>"']+/g;

// תווי כיווניות שוואטסאפ מוסיף סביב שמות ומספרי טלפון
const BIDI_CHARS = /[‎‏‪-‮⁦-⁩]/g;

// "[22.11, 7:43] שם השולח: " בתחילת שורה (ייצוא/העתקה מוואטסאפ)
const CHAT_PREFIX = /^\[[^\]]{1,40}\]\s*[^:]{0,60}:\s*/;

/** מנקה תווים שנדבקו לסוף הלינק (סימני פיסוק, ? או & ריקים) */
export const cleanUrl = (url) => url.replace(/[.,;:!)\]}>'"?&#]+$/, '');

const extractTitle = (textBefore) => {
  const lines = textBefore
    .replace(BIDI_CHARS, '')
    .split('\n')
    .map(l => l.replace(CHAT_PREFIX, '').trim())
    .filter(Boolean);
  if (lines.length === 0) return null;

  const title = lines[lines.length - 1].replace(/[\s\-–—:|]+$/, '').trim();
  if (title.length < 2 || title.length > 120) return null;
  return title;
};

/**
 * @returns {{url: string, title: string|null}[]} רשימה ללא כפילויות, לפי סדר הופעה
 */
export const parseJobLinks = (rawText) => {
  if (!rawText) return [];
  const results = [];
  const seen = new Set();
  let prevEnd = 0;

  for (const match of rawText.matchAll(URL_REGEX)) {
    const url = cleanUrl(match[0]);
    const title = extractTitle(rawText.slice(prevEnd, match.index));
    prevEnd = match.index + match[0].length;

    if (!seen.has(url)) {
      seen.add(url);
      results.push({ url, title });
    }
  }
  return results;
};
