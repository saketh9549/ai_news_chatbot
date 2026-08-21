import React, { useState } from 'react'
import {
  Menu,
  Rss,
  Plus,
  RefreshCw,
  SlidersHorizontal,
  ChevronRight,
  Radio,
  Layers,
  Sparkles,
} from 'lucide-react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import SourcePanel from './components/SourcePanel'
import HeadlineTicker from './components/HeadlineTicker'

export default function App() {
  const [showSidebar, setShowSidebar] = useState(true)
  const [showSources, setShowSources] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState(() => {
    try {
      return localStorage.getItem('newspulse_active_session') || null
    } catch {
      return null
    }
  })
  const [sessionRefreshKey, setSessionRefreshKey] = useState(0)
  const [activeCategory, setActiveCategory] = useState('all')
  const [prefilledQuery, setPrefilledQuery] = useState('')

  const handleRefreshSessions = () => {
    setSessionRefreshKey((k) => k + 1)
  }

  const handleSelectSession = (sessionId) => {
    setActiveSessionId(sessionId)
    if (sessionId) {
      localStorage.setItem('newspulse_active_session', sessionId)
    } else {
      localStorage.removeItem('newspulse_active_session')
    }
  }

  const handleNewChat = () => {
    setActiveSessionId(null)
    localStorage.removeItem('newspulse_active_session')
  }

  const handleSelectCategory = (categoryId) => {
    setActiveCategory(categoryId)
  }

  const handleSelectHeadline = (title) => {
    setPrefilledQuery(`Tell me about this recent news: ${title}`)
  }

  return (
    <div className="h-screen flex flex-col bg-slate-950 font-sans text-slate-100 overflow-hidden antialiased">
      {/* Top Breaking Headlines Ticker */}
      <HeadlineTicker onSelectHeadline={handleSelectHeadline} />

      {/* Main Glassmorphic Application Bar */}
      <header className="bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-4 py-2.5 flex items-center justify-between shrink-0 select-none z-20">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowSidebar(!showSidebar)}
            className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title={showSidebar ? 'Hide Sidebar' : 'Show Sidebar'}
          >
            <Menu className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold text-xs shadow-md shadow-blue-500/20">
              NP
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold text-white tracking-tight leading-tight">
                NewsPulse
              </span>
              <span className="text-[10px] text-cyan-400 font-medium leading-none">
                Grounded Hybrid RAG
              </span>
            </div>
          </div>
        </div>

        {/* Right Action Tools */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleNewChat}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition-all cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5 text-cyan-400" />
            <span>New Chat</span>
          </button>

          <button
            onClick={() => setShowSources(!showSources)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl border transition-all cursor-pointer ${
              showSources
                ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Sources & Feeds</span>
            <span className="sm:hidden">Feeds</span>
          </button>
        </div>
      </header>

      {/* 3-Zone Workspace Body */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Zone 1: Left Navigation & History Sidebar */}
        <Sidebar
          isOpen={showSidebar}
          onToggle={() => setShowSidebar(!showSidebar)}
          activeSessionId={activeSessionId}
          sessionRefreshKey={sessionRefreshKey}
          onSelectSession={handleSelectSession}
          onNewChat={handleNewChat}
          activeCategory={activeCategory}
          onSelectCategory={handleSelectCategory}
        />

        {/* Zone 2: Central AI Conversation & Command Stream */}
        <main className="flex-1 flex flex-col overflow-hidden relative">
          <ChatWindow
            activeSessionId={activeSessionId}
            onSessionCreated={handleSelectSession}
            onRefreshSessions={handleRefreshSessions}
            activeCategory={activeCategory}
            onSelectCategory={handleSelectCategory}
            onOpenSources={() => setShowSources(true)}
            prefilledQuery={prefilledQuery}
            onClearPrefilledQuery={() => setPrefilledQuery('')}
          />
        </main>

        {/* Zone 3: Right Slide-Out Intelligence Inspector */}
        {showSources && (
          <aside className="w-84 max-w-full h-full shrink-0 shadow-2xl z-20 animate-in slide-in-from-right-10 duration-200">
            <SourcePanel onClose={() => setShowSources(false)} />
          </aside>
        )}
      </div>
    </div>
  )
}
