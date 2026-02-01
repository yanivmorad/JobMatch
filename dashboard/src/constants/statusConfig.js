import { 
  Clock, 
  Send, 
  Phone, 
  Users, 
  XCircle, 
  AlertCircle, 
  Ghost
} from 'lucide-react';

export const STATUS_CONFIG = {
  pending: { label: "ממתין לבדיקה", color: "#6c757d", bg: "#f8f9fa", border: "#dee2e6", description: "חדש", icon: Clock },
  applied: { label: "הוגשה מועמדות", color: "#007bff", bg: "#e7f1ff", border: "#b6d4fe", description: "שלחתי קורות חיים", icon: Send },
  phone_screen: { label: "ראיון טלפוני", color: "#6f42c1", bg: "#f3eafa", border: "#d9bbef", description: "שיחה ראשונית", icon: Phone },
  interview: { label: "ראיון", color: "#fd7e14", bg: "#fff5eb", border: "#fed7b1", description: "בתהליך ראיונות", icon: Users },
  not_relevant: { label: "לא רלוונטי", color: "#495057", bg: "#e9ecef", border: "#ced4da", description: "לא מתאים לי", icon: XCircle },
  rejected: { label: "דחייה", color: "#dc3545", bg: "#f8d7da", border: "#f5c2c7", description: "קיבלתי לא", icon: AlertCircle },
  ghosted: { label: "ללא מענה", color: "#856404", bg: "#fff3cd", border: "#ffeeba", description: "לא חזרו אלי מעל חודש", icon: Ghost }
};

export const getStatusLabel = (status) => STATUS_CONFIG[status]?.label || status;
export const getStatusColor = (status) => STATUS_CONFIG[status]?.color || "#6c757d";
