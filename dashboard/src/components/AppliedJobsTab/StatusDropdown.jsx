import React from 'react';
import { ChevronDown } from 'lucide-react';
import { STATUS_CONFIG } from '../../constants/statusConfig';

const StatusDropdown = ({ status, onUpdateStatus, jobUrl }) => {
  const currentStatus = status || 'pending';
  const config = STATUS_CONFIG[currentStatus] || STATUS_CONFIG.pending;

  return (
    <div 
      className="relative inline-block"
      onClick={(e) => e.stopPropagation()}
    >
      <div 
        className="inline-flex items-center gap-2 px-3 py-2 rounded-full text-xs font-black border transition-all"
        style={{ 
          backgroundColor: config.bg, 
          color: config.color,
          borderColor: config.border
        }}
      >
        <config.icon className="w-3 h-3" />
        {config.label}
        <ChevronDown size={14} />
      </div>
      <select
        value={currentStatus}
        onChange={(e) => onUpdateStatus(jobUrl, e.target.value)}
        className="absolute inset-0 opacity-0 cursor-pointer w-full"
      >
        {Object.entries(STATUS_CONFIG).map(([key, config]) => (
          <option key={key} value={key}>{config.label}</option>
        ))}
      </select>
    </div>
  );
};

export default React.memo(StatusDropdown);
