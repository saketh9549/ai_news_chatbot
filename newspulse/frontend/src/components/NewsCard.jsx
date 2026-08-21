import React, { useState } from 'react'
import { ExternalLink, Calendar, Newspaper, Sparkles, Image as ImageIcon } from 'lucide-react'

// Map sources/categories to curated accent gradients and badges
const CATEGORY_COLORS = {
  technology: 'from-blue-600 to-indigo-600 text-blue-100',
  business: 'from-emerald-600 to-teal-700 text-emerald-100',
  world: 'from-amber-600 to-orange-600 text-amber-100',
  science: 'from-purple-600 to-violet-700 text-purple-100',
  general: 'from-slate-700 to-slate-900 text-slate-100',
}

export default function NewsCard({ citation, category = 'technology' }) {
  const [imageError, setImageError] = useState(false)
  const hasImage = citation.image_url && !imageError

  // Format published date
  let formattedDate = null
  if (citation.published_at) {
    try {
      const dt = new Date(citation.published_at)
      if (!isNaN(dt.getTime())) {
        formattedDate = dt.toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })
      }
    } catch {
      formattedDate = null
    }
  }

  const categoryGradient = CATEGORY_COLORS[category] || CATEGORY_COLORS.general
  const title = citation.title || `${citation.source} Report`

  return (
    <div className="group flex flex-col bg-white rounded-2xl border border-slate-200/90 shadow-xs hover:shadow-md hover:border-blue-400/80 transition-all duration-200 overflow-hidden text-left">
      {/* Top Image / Visual Banner */}
      <div className="relative w-full aspect-video sm:aspect-[16/9] bg-slate-100 overflow-hidden flex items-center justify-center">
        {hasImage ? (
          <img
            src={citation.image_url}
            alt={title}
            onError={() => setImageError(true)}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 ease-out"
            loading="lazy"
          />
        ) : (
          <div className={`w-full h-full bg-gradient-to-br ${categoryGradient} flex flex-col items-center justify-center p-4 text-center select-none`}>
            <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-md flex items-center justify-center text-white mb-2 shadow-inner">
              <Newspaper className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-white/90 tracking-wide uppercase">
              {citation.source || 'News Intelligence'}
            </span>
          </div>
        )}

        {/* Index Citation Pill */}
        <div className="absolute top-2.5 left-2.5 px-2 py-0.5 rounded-md bg-slate-900/80 backdrop-blur-md text-white text-[11px] font-bold tracking-tight shadow-xs flex items-center gap-1">
          <span>[{citation.index}]</span>
        </div>

        {/* Publisher Badge */}
        <div className="absolute top-2.5 right-2.5 px-2.5 py-0.5 rounded-md bg-white/90 backdrop-blur-md text-slate-800 text-[11px] font-semibold tracking-wide shadow-xs">
          {citation.source}
        </div>
      </div>

      {/* Content Area */}
      <div className="p-3.5 flex flex-col flex-1 justify-between">
        <div>
          {/* Published Date */}
          {formattedDate && (
            <div className="flex items-center gap-1 text-[11px] font-medium text-slate-400 mb-1.5">
              <Calendar className="w-3 h-3 text-slate-400" />
              <span>{formattedDate}</span>
            </div>
          )}

          {/* Headline */}
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-slate-900 text-sm leading-snug group-hover:text-blue-600 transition-colors line-clamp-2 mb-2 block"
            title={title}
          >
            {title}
          </a>

          {/* Key Summary / Takeaway */}
          {citation.summary && (
            <p className="text-xs text-slate-600 leading-relaxed line-clamp-3 mb-3">
              {citation.summary}
            </p>
          )}
        </div>

        {/* Footer Action */}
        <div className="pt-2 border-t border-slate-100 flex items-center justify-between mt-auto">
          <span className="text-[11px] font-medium text-slate-400">Verified Citation [{citation.index}]</span>
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline"
          >
            <span>Read Story</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  )
}
