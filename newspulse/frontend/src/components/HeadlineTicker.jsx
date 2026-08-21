import React, { useState, useEffect } from 'react'
import { Radio, ChevronRight, ExternalLink, Sparkles } from 'lucide-react'
import { getRecentArticles } from '../api/client'

export default function HeadlineTicker({ onSelectHeadline }) {
  const [headlines, setHeadlines] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadHeadlines()
    const timer = setInterval(loadHeadlines, 60000) // refresh every 60s
    return () => clearInterval(timer)
  }, [])

  const loadHeadlines = async () => {
    try {
      const data = await getRecentArticles('all', 12)
      setHeadlines(data || [])
    } catch (err) {
      console.debug('Failed to load ticker headlines:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading || headlines.length === 0) {
    return null
  }

  return (
    <div className="bg-slate-900 text-white border-b border-slate-800 px-4 py-1.5 flex items-center gap-3 overflow-hidden text-xs shrink-0 select-none">
      {/* Live Badge */}
      <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[10px] text-cyan-400 shrink-0 pr-2 border-r border-slate-700">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
        </span>
        <span>Live Wire</span>
      </div>

      {/* Horizontal Scrolling Items */}
      <div className="flex-1 flex items-center gap-6 overflow-x-auto scrollbar-none py-0.5">
        {headlines.map((item) => (
          <div
            key={item.id}
            onClick={() => onSelectHeadline && onSelectHeadline(item.title)}
            className="flex items-center gap-2 shrink-0 cursor-pointer group hover:text-cyan-300 transition-colors"
          >
            <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-medium border border-slate-700 uppercase group-hover:border-cyan-500/50">
              {item.source_name}
            </span>
            <span className="text-slate-300 font-normal max-w-sm truncate group-hover:text-white transition-colors">
              {item.title}
            </span>
            <Sparkles className="w-2.5 h-2.5 text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        ))}
      </div>
    </div>
  )
}
