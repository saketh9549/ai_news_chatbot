import React, { useState, useEffect } from 'react'
import {
  Plus,
  MessageSquare,
  Trash2,
  TrendingUp,
  Cpu,
  Globe,
  Briefcase,
  FlaskConical,
  Radio,
  SlidersHorizontal,
  ChevronLeft,
  Search,
} from 'lucide-react'
import { getSessions, deleteSession } from '../api/client'

const TOPIC_CHANNELS = [
  { id: 'all', label: 'All Intel', icon: Radio },
  { id: 'technology', label: 'Tech & AI', icon: Cpu },
  { id: 'world', label: 'Global News', icon: Globe },
  { id: 'business', label: 'Markets & Finance', icon: Briefcase },
  { id: 'science', label: 'Science & Health', icon: FlaskConical },
]

export default function Sidebar({
  activeSessionId,
  sessionRefreshKey,
  onSelectSession,
  onNewChat,
  activeCategory,
  onSelectCategory,
  isOpen,
  onToggle,
}) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(false)
  const [filterQuery, setFilterQuery] = useState('')

  useEffect(() => {
    loadSessions()
  }, [activeSessionId, sessionRefreshKey])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const data = await getSessions()
      setSessions(data || [])
    } catch (err) {
      console.debug('Failed to load sessions:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (e, sessionId) => {
    e.stopPropagation()
    try {
      await deleteSession(sessionId)
      setSessions((prev) => prev.filter((s) => s.id !== sessionId))
      if (activeSessionId === sessionId) {
        onNewChat()
      }
    } catch (err) {
      alert(`Error deleting session: ${err.message}`)
    }
  }

  const filteredSessions = sessions.filter((s) =>
    s.first_query.toLowerCase().includes(filterQuery.toLowerCase())
  )

  if (!isOpen) {
    return null
  }

  return (
    <aside className="w-64 min-w-[16rem] max-w-[16rem] bg-slate-900 text-slate-200 h-full flex flex-col border-r border-slate-800 shrink-0 select-none z-30 overflow-hidden">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white font-black text-sm shadow-md shadow-cyan-500/20 shrink-0">
            NP
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-bold text-white tracking-tight leading-none truncate">NewsPulse</h1>
            <span className="text-[10px] text-cyan-400 font-medium truncate block">Grounded Intelligence</span>
          </div>
        </div>
        <button
          onClick={onToggle}
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors md:hidden shrink-0 cursor-pointer"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="p-3 shrink-0">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-xl shadow-md shadow-blue-600/20 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4 shrink-0" />
          <span className="truncate">New Investigation</span>
        </button>
      </div>

      {/* Topic Channels */}
      <div className="px-3 py-2 border-b border-slate-800/80 shrink-0">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 mb-1.5 block">
          Channels
        </span>
        <div className="space-y-0.5">
          {TOPIC_CHANNELS.map((item) => {
            const Icon = item.icon
            const isSelected = activeCategory === item.id
            return (
              <button
                key={item.id}
                onClick={() => onSelectCategory(item.id)}
                className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-slate-800 text-cyan-400 font-semibold shadow-2xs border border-slate-700/50'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span className="truncate">{item.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* History Search & Session List */}
      <div className="flex-1 flex flex-col min-h-0 px-3 py-3 overflow-hidden">
        <div className="flex items-center justify-between mb-2 px-1 shrink-0">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Recent Threads ({sessions.length})
          </span>
        </div>

        {sessions.length > 5 && (
          <div className="relative mb-2 shrink-0">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              placeholder="Search chats..."
              className="w-full pl-8 pr-2.5 py-1 text-xs bg-slate-800/80 border border-slate-700/60 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500 text-[11px]"
            />
          </div>
        )}

        <div className="flex-1 overflow-y-auto space-y-1 scrollbar-none pr-0.5">
          {filteredSessions.map((s) => {
            const isActive = activeSessionId === s.id
            return (
              <div
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                className={`group flex items-center justify-between gap-1.5 px-2.5 py-2 rounded-xl text-xs cursor-pointer transition-all w-full min-w-0 overflow-hidden ${
                  isActive
                    ? 'bg-blue-600/20 text-white border border-blue-500/30'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
                title={s.first_query}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
                  <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                  <span className="truncate text-xs font-normal block max-w-full">{s.first_query}</span>
                </div>
                <button
                  onClick={(e) => handleDelete(e, s.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-opacity shrink-0 cursor-pointer"
                  title="Delete chat"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            )
          })}

          {!loading && sessions.length === 0 && (
            <div className="text-center py-6 text-slate-400 text-xs">
              No conversations yet. Ask a question to start.
            </div>
          )}
        </div>
      </div>

      {/* System Status Footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/40 text-[11px] text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>Gemini & Qdrant Online</span>
        </div>
        <span className="font-mono text-[10px] text-slate-400">v0.1.0</span>
      </div>
    </aside>
  )
}
