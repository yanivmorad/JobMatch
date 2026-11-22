import { createContext, useContext } from 'react';

// הודעה קצרה ושקטה אחרי פעולה (במקום alert). ToastProvider נמצא ב-components/ui/Feedback.jsx
export const ToastContext = createContext(() => {});
export const useToast = () => useContext(ToastContext);
