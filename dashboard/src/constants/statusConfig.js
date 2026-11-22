// סטטוס ההגשה (application_status). הערכים זהים ל-ApplicationStatus בשרת.
// tone הוא תפקיד צבע מהטוקנים (לא hex), stage הוא המיקום ב-pipeline של ההגשות.
export const STATUS_CONFIG = {
  pending: { label: 'ממתין לבדיקה', description: 'עוד לא החלטת', tone: 'neutral' },
  applied: { label: 'הוגש', description: 'שלחתי קורות חיים', tone: 'accent', stage: 0 },
  phone_screen: { label: 'שיחה טלפונית', description: 'שיחה ראשונית', tone: 'accent', stage: 1 },
  interview: { label: 'ראיון', description: 'בתהליך ראיונות', tone: 'accent', stage: 2 },
  rejected: { label: 'דחייה', description: 'קיבלתי תשובה שלילית', tone: 'danger', closed: true },
  ghosted: { label: 'ללא מענה', description: 'לא חזרו אליי', tone: 'muted', closed: true },
  not_relevant: { label: 'לא רלוונטי', description: 'לא מתאים לי', tone: 'muted', closed: true },
};

// שלבי ה-pipeline לפי הסדר
export const PIPELINE_STAGES = Object.keys(STATUS_CONFIG)
  .filter((k) => STATUS_CONFIG[k].stage !== undefined)
  .sort((a, b) => STATUS_CONFIG[a].stage - STATUS_CONFIG[b].stage);

// סטטוסים שהשרת מעביר בגללם לארכיון אוטומטית (update_application_status)
export const AUTO_ARCHIVE_STATUSES = Object.keys(STATUS_CONFIG).filter((k) => STATUS_CONFIG[k].closed);

export const getStatusLabel = (status) => STATUS_CONFIG[status]?.label || status;
