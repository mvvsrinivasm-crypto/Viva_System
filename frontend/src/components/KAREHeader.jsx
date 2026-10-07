import React from 'react';

export const KAREHeader = ({ compact = false }) => {
  return (
    <div className={`w-full bg-white border-b border-slate-200 transition-all ${compact ? 'py-2 px-4 shadow-xs' : 'py-3.5 px-6 shadow-sm'}`}>
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Official College Logo Banner */}
        <div className="flex items-center gap-4">
          <img
            src="/kare_logo.png"
            alt="Kalasalingam Academy of Research and Education"
            className={`${compact ? 'h-8 sm:h-9' : 'h-10 sm:h-12'} w-auto object-contain`}
          />
        </div>

        {/* Institution Accreditation & Subtitle */}
        <div className="text-center sm:text-right">
          <div className="text-xs font-semibold text-slate-800 tracking-wide">
            KARE VIVA EVALUATION SYSTEM
          </div>
          <div className="text-[11px] text-slate-500 font-medium">
            (Deemed to be University under sec. 3 of UGC Act 1956) • NAAC &quot;A++&quot; Accredited
          </div>
        </div>
      </div>
    </div>
  );
};

export default KAREHeader;
