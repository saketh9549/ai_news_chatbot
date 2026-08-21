import React, { useState } from 'react'
import { ExternalLink, Clock, Newspaper } from 'lucide-react'

export default function CitationChip({ citation, inline = false }) {
  const [showPopover, setShowPopover] = useState(false)

  const formatTime = (ts) => {
    if (!ts) return null
    try {
      return new Date(ts).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return ts
    }
  }

  return (
    <div
      className="relative inline-block align-baseline"
      onMouseEnter={() => setShowPopover(true)}
      onMouseLeave={() => setShowPopover(false)}
    >
      <a
        href={citation.url}
        target="_blank"
        rel="noopener noreferrer"
        className={`inline-flex items-center gap-1 transition-all ${
          inline
            ? 'mx-0.5 px-1.5 py-0.2 text-[11px] font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md shadow-2xs hover:shadow-xs'
            : 'px-2.5 py-1 text-xs font-medium text-slate-700 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-300 rounded-lg shadow-2xs hover:shadow-sm'
        }`}
      >
        <span className="text-blue-600 font-bold">[{citation.index}]</span>
        <span className="truncate max-w-[130px] font-medium">{citation.source}</span>
        <ExternalLink className="w-2.5 h-2.5 opacity-60 ml-0.5" />
      </a>

      {/* Interactive Hovercard Popover */}
      {showPopover && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3 bg-slate-900 text-white rounded-xl shadow-xl z-50 text-left text-xs border border-slate-700 pointer-events-none animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between gap-2 mb-1.5 pb-1.5 border-b border-slate-800">
            <div className="flex items-center gap-1.5 font-semibold text-cyan-400 truncate">
              <Newspaper className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">{citation.source}</span>
            </div>
            <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-mono text-[10px]">
              Source [{citation.index}]
            </span>
          </div>

          {citation.published_at && (
            <div className="flex items-center gap-1 text-[11px] text-slate-400 mb-2">
              <Clock className="w-3 h-3" />
              <span>{formatTime(citation.published_at)}</span>
            </div>
          )}

          <p className="text-[11px] text-slate-300 line-clamp-2 leading-relaxed mb-2 font-mono text-[10px] opacity-80 truncate">
            {citation.url}
          </p>

          <div className="flex items-center justify-end text-[10px] text-cyan-400 font-medium pt-1">
            <span>Click badge to open article →</span>
          </div>
        </div>
      )}
    </div>
  )
}
