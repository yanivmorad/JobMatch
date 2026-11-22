import { Archive, Columns3, Inbox, LayoutGrid, Plus, UserRound } from 'lucide-react';

// המסכים של הדשבורד. ה-id הם השמות הפנימיים הקיימים (dashboard / active / ...).
export const TABS = [
  { id: 'dashboard', label: 'סקירה', icon: LayoutGrid },
  { id: 'active', label: 'לבדיקה', icon: Inbox },
  { id: 'applied', label: 'הגשות', icon: Columns3 },
  { id: 'add', label: 'קליטה', icon: Plus },
  { id: 'history', label: 'ארכיון', icon: Archive },
  { id: 'profile', label: 'פרופיל', icon: UserRound },
];
