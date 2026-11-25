# הקמת בוט הוואטסאפ

הבוט: מעבירים אליו הודעת משרות (או קישור), והוא עונה כמה משרות קיבל, ואחר כך שולח ציון לכל
משרה כשהניתוח מסתיים. הקוד מוכן (`src/services/whatsapp.py`, `src/routes/whatsapp_routes.py`,
`src/services/notifier.py`). בלי חמשת משתני `WHATSAPP_*` הבוט כבוי, וה-webhook מחזיר 404.

עובדים מול **WhatsApp Cloud API** הרשמי של Meta. העובדות כאן נבדקו בתיעוד ב-2026-11-26 (ראו
"Limits" ב-README). שמות הכפתורים ב-Meta משתנים מדי פעם: אם משהו לא נמצא בדיוק בשם הזה, מחפשים
שם דומה באותו מסך.

בכל מקום כאן `<service>` הוא שם השירות שלך ב-Render (ה-URL מופיע בראש עמוד השירות).

## מה צריך לפני שמתחילים
- הענף של הבוט ממוזג ל-`main` ופרוס ב-Render (`/webhooks/whatsapp` מחזיר 404 ולא את הדשבורד).
- חשבון פייסבוק, ומספר וואטסאפ אישי שממנו תשלח לבוט.

## 1. אפליקציה ב-Meta
1. https://developers.facebook.com ← **My Apps** ← **Create App**.
2. סוג השימוש: חיבור ללקוחות דרך WhatsApp (Business). בסוף נוצר גם חשבון WhatsApp Business לבדיקות.
3. בתפריט האפליקציה: **WhatsApp** ← **API Setup**. Meta יוצרת **מספר בדיקה** של הבוט אוטומטית.
4. בשדה **To**: מוסיפים את המספר האישי שלך ומאמתים בקוד שמגיע בוואטסאפ. התיעוד לא מציין כמה
   מספרים מותר להוסיף.

## 2. חמשת הערכים

| משתנה ב-Render | מאיפה |
|---|---|
| `WHATSAPP_PHONE_NUMBER_ID` | **API Setup** ← **Phone number ID** (מספר ארוך, לא מספר הטלפון) |
| `WHATSAPP_APP_SECRET` | **App settings** ← **Basic** ← **App secret** ← Show |
| `WHATSAPP_ACCESS_TOKEN` | טוקן קבוע של System User (סעיף 3). הטוקן הזמני ב-API Setup פג תוך שעות |
| `WHATSAPP_ALLOWED_NUMBERS` | המספר האישי שלך עם קידומת, בלי + ובלי 0: `972501234567`. כמה מספרים: עם פסיקים |
| `WHATSAPP_VERIFY_TOKEN` | Render יצר אותו כשה-Blueprint התעדכן. אם אין: מחרוזת אקראית ארוכה שתבחר |

## 3. טוקן קבוע (System User)
1. https://business.facebook.com ← **Settings** (Business settings) ← **Users** ← **System users** ← **Add**
   (תפקיד Admin).
2. **Assign assets**: האפליקציה (Manage app), וחשבון ה-WhatsApp (Full control).
3. **Generate token** ← בוחרים את האפליקציה ← תוקף: Never (אם מוצע) ← ההרשאות
   `whatsapp_business_messaging`, `whatsapp_business_management`, `business_management`.
4. מעתיקים את הטוקן **ישר ל-Render**. הוא מוצג פעם אחת. לא מדביקים אותו בצ'אט.

## 4. Render
1. השירות `jobmatch` ← **Environment** ← **Edit** ← מוסיפים את הערכים מסעיף 2. אם
   `WHATSAPP_VERIFY_TOKEN` כבר קיים, משאירים אותו.
2. **Save, rebuild, and deploy**.
3. בדיקה: `https://<service>.onrender.com/health` מציג `notifier_worker` תחת `workers`.

## 5. חיבור ה-webhook ב-Meta
1. קודם מעירים את השירות: פותחים `https://<service>.onrender.com/ping` ומחכים לתשובה. שירות
   ישן לא יענה בזמן לבדיקה של Meta.
2. **WhatsApp** ← **Configuration** ← **Webhook** ← **Edit**:
   - **Callback URL**: `https://<service>.onrender.com/webhooks/whatsapp`
   - **Verify token**: הערך של `WHATSAPP_VERIFY_TOKEN` מ-Render.
   - **Verify and save**.
3. באותו מסך, **Webhook fields** ← **messages** ← **Subscribe**.
4. לפי התיעוד, חלק מה-webhooks לא נשלחים כשהאפליקציה ב-**Dev mode**. אם הודעות לא מגיעות, מעבירים
   ל-**Live** (Meta עשויה לבקש קישור למדיניות פרטיות).

## 6. בדיקה
שולחים מהמספר האישי למספר הבוט הודעה עם קישור למשרה. צריכה לחזור תשובה "קיבלתי 1 משרות חדשות",
ואחרי כדקה-שתיים הציון. המשרה מופיעה גם בדשבורד.

## תקלות
ב-Render ← **Logs**:

| מה רואים | הסיבה |
|---|---|
| Meta: "The callback URL or verify token couldn't be validated" | הטוקן שונה מ-Render, השירות ישן (סעיף 5.1), או שהענף עוד לא פרוס (404) |
| `401` על `POST /webhooks/whatsapp` | `WHATSAPP_APP_SECRET` לא נכון |
| `not in WHATSAPP_ALLOWED_NUMBERS` | המספר ב-`WHATSAPP_ALLOWED_NUMBERS` לא תואם (רק ספרות, עם 972) |
| `WhatsApp: send failed (401)` | הטוקן פג או לא קבוע (סעיף 3) |
| `WhatsApp: send failed (400)` | ההודעה של Meta בלוג אומרת למה. בדרך כלל: המספר האישי לא אושר ב-**To** (סעיף 1.4) |
| הבוט ענה "קיבלתי" ואין ציון | לבדוק בדשבורד באיזה שלב המשרה. ציון נשלח גם על כישלון |

## עלות ומגבלות (מהתיעוד, 2026-11-26: https://developers.facebook.com/docs/whatsapp/pricing)
- הודעות ממך לבוט: חינם. תשובות הבוט בתוך 24 שעות מההודעה שלך: 1,000 בחודש בחינם למספר, ואחר כך
  בתשלום (ואז צריך אמצעי תשלום ב-Meta). בשימוש אישי זה רחוק מהמגבלה.
- הבוט עונה רק בתוך חלון 24 השעות, ולכן הוא לא שולח הודעות יזומות.
- Render החינמי ישן אחרי 15 דקות. הודעה שמגיעה בזמן השינה מעירה אותו, ו-Meta שולחת שוב עד שמקבלת
  תשובה. לא הולך לאיבוד, אבל התשובה הראשונה יכולה לקחת דקה ויותר.
