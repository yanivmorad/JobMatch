export const getSuitabilityScoreStyle = (score) => {
  if (score >= 85) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (score >= 50) return 'bg-amber-50 text-amber-700 border-amber-200';
  return 'bg-rose-50 text-rose-700 border-rose-200';
};

export const getStatusConfig = (status, STATUS_CONFIG) => {
  return STATUS_CONFIG[status] || STATUS_CONFIG.pending;
};
