// ערכת נושא שנבחרה ידנית. 'system' = לפי הגדרת המערכת (בלי data-theme).
// index.html קורא את אותו מפתח לפני הציור הראשון, כדי שלא יהיה הבהוב.
const THEME_KEY = 'jobmatch_theme';

export const readTheme = () => {
  try { return localStorage.getItem(THEME_KEY) || 'system'; } catch { return 'system'; }
};

export const applyTheme = (theme) => {
  try {
    if (theme === 'system') localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, theme);
  } catch { /* אחסון חסום - הבחירה תחזיק עד רענון */ }
  const root = document.documentElement;
  if (theme === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', theme);
};
