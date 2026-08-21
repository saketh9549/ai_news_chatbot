import React, { useState, useRef, useEffect } from 'react'
import {
  Send,
  Sparkles,
  ArrowRight,
  Radio,
  SlidersHorizontal,
  Bot,
  RefreshCw,
  Search,
  ExternalLink,
  Layers,
  Square,
  Octagon,
} from 'lucide-react'
import { sendMessageStream, getChatHistory } from '../api/client'
import MessageBubble from './MessageBubble'

const CATEGORIES = [
  { id: 'all', label: 'All Intel' },
  { id: 'general', label: 'General' },
  { id: 'technology', label: 'Tech & AI' },
  { id: 'world', label: 'World' },
  { id: 'business', label: 'Markets' },
  { id: 'science', label: 'Science' },
]

const STARTER_PROMPTS = [
  {
    title: 'Top Global Briefing',
    desc: 'Summarize the most significant breaking news stories across all verified sources today.',
    query: 'What are the top breaking news stories and key global developments today?',
    category: 'all',
  },
  {
    title: 'AI & Tech Breakthroughs',
    desc: 'Analyze recent developments, corporate earnings, and open-weights releases.',
    query: 'What are the latest breakthroughs, model releases, and company moves in tech and AI?',
    category: 'technology',
  },
  {
    title: 'Financial & Market Pulse',
    desc: 'Get a breakdown on market movements, retail trends, and central bank signals.',
    query: 'What are the major financial, economic, and stock market updates reported today?',
    category: 'business',
  },
  {
    title: 'European & World Affairs',
    desc: 'Inspect international diplomatic negotiations, trade talks, and political crises.',
    query: 'What is happening in world news regarding international relations and political events?',
    category: 'world',
  },
]

export default function ChatWindow({
  activeSessionId,
  onSessionCreated,
  onRefreshSessions,
  activeCategory,
  onSelectCategory,
  onOpenSources,
  prefilledQuery,
  onClearPrefilledQuery,
}) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const abortControllerRef = useRef(null)
  const currentSessionIdRef = useRef(activeSessionId)

  // Sync external activeSessionId changes (e.g. user clicked another chat in sidebar or clicked "+ New Chat")
  useEffect(() => {
    if (activeSessionId !== currentSessionIdRef.current) {
      currentSessionIdRef.current = activeSessionId
      if (activeSessionId) {
        loadSessionHistory(activeSessionId)
      } else {
        setMessages([])
      }
    }
  }, [activeSessionId])

  // Handle prefilled query from HeadlineTicker
  useEffect(() => {
    if (prefilledQuery && prefilledQuery.trim()) {
      handleSend(prefilledQuery)
      if (onClearPrefilledQuery) onClearPrefilledQuery()
    }
  }, [prefilledQuery])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isGenerating])

  // Listen for Escape key to stop generation
  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      if (e.key === 'Escape' && isGenerating) {
        handleStop()
      }
    }
    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [isGenerating])

  const loadSessionHistory = async (sessionId) => {
    if (!sessionId) return
    try {
      setIsLoadingHistory(true)
      const history = await getChatHistory(sessionId)
      if (history && history.length > 0) {
        setMessages(
          history.map((m) => ({
            role: m.role,
            content: m.content,
            citations: m.citations,
          }))
        )
      } else {
        setMessages([])
      }
    } catch (err) {
      console.error('Failed to load chat history:', err)
      setMessages([])
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsGenerating(false)
  }

  const handleSend = async (queryText) => {
    const query = (queryText || input).trim()
    if (!query) return

    // If currently generating, stop previous
    if (isGenerating && abortControllerRef.current) {
      handleStop()
    }

    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    // Initialize new abort controller
    const controller = new AbortController()
    abortControllerRef.current = controller

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: query, citations: null }])
    setIsGenerating(true)

    // Add empty assistant placeholder for streaming
    setMessages((prev) => [...prev, { role: 'assistant', content: '', citations: null }])

    // Reuse active session ID so multiple queries stay in the SAME chat
    const sessionIdToSend = currentSessionIdRef.current || activeSessionId || null

    try {
      const catFilter = activeCategory === 'all' ? null : activeCategory

      await sendMessageStream({
        query,
        sessionId: sessionIdToSend,
        categoryFilter: catFilter,
        signal: controller.signal,
        onSession: (newSessionId) => {
          currentSessionIdRef.current = newSessionId
          if (onSessionCreated) onSessionCreated(newSessionId)
          if (onRefreshSessions) onRefreshSessions()
        },
        onSessionCreated: (newSessionId) => {
          currentSessionIdRef.current = newSessionId
          if (onSessionCreated) onSessionCreated(newSessionId)
          if (onRefreshSessions) onRefreshSessions()
        },
        onToken: (token) => {
          setMessages((prev) => {
            const next = [...prev]
            const lastIdx = next.length - 1
            if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
              next[lastIdx] = {
                ...next[lastIdx],
                content: next[lastIdx].content + token,
              }
            }
            return next
          })
        },
        onDone: ({ citations }) => {
          setMessages((prev) => {
            const next = [...prev]
            const lastIdx = next.length - 1
            if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
              next[lastIdx] = {
                ...next[lastIdx],
                citations,
              }
            }
            return next
          })
          setIsGenerating(false)
          abortControllerRef.current = null
          if (onRefreshSessions) onRefreshSessions()
        },
        onError: (err) => {
          if (err.name === 'AbortError') return
          setMessages((prev) => {
            const next = [...prev]
            const lastIdx = next.length - 1
            if (lastIdx >= 0 && next[lastIdx].role === 'assistant') {
              next[lastIdx] = {
                ...next[lastIdx],
                content:
                  next[lastIdx].content ||
                  'An error occurred while connecting to the news service. Please try again.',
              }
            }
            return next
          })
          setIsGenerating(false)
          abortControllerRef.current = null
          if (onRefreshSessions) onRefreshSessions()
        },
      })
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Chat error:', err)
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: 'Connection error. Please check your backend service.',
            citations: null,
          },
        ])
      }
      setIsGenerating(false)
      abortControllerRef.current = null
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleTextareaInput = (e) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`
  }

  return (
    <div className="flex-1 flex-col h-full bg-slate-50 relative overflow-hidden flex">
      {/* Scrollable Conversation Container */}
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
        <div className="max-w-3xl mx-auto w-full">
          {/* Loading History Indicator */}
          {isLoadingHistory && (
            <div className="flex items-center justify-center py-20 text-slate-400 gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />
              <span className="text-xs font-medium">Restoring conversation...</span>
            </div>
          )}

          {/* Welcome Screen when Empty and not loading */}
          {!isLoadingHistory && messages.length === 0 && (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-2 py-8 animate-in fade-in zoom-in-95 duration-200">
              <div className="relative mb-5">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center text-white text-2xl font-black shadow-xl shadow-blue-500/20">
                  <Bot className="w-8 h-8" />
                </div>
                <span className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 border-2 border-white flex items-center justify-center text-[10px] text-white">
                  ✓
                </span>
              </div>

              <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight mb-2">
                NewsPulse Intelligence
              </h2>
              <p className="text-sm text-slate-600 max-w-md mx-auto mb-8 leading-relaxed">
                Citation-grounded news assistant. Ask anything about recent events and receive verified summaries backed by real source links.
              </p>

              {/* Starter Investigation Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
                {STARTER_PROMPTS.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      onSelectCategory(item.category)
                      handleSend(item.query)
                    }}
                    className="p-4 bg-white hover:bg-gradient-to-br hover:from-white hover:to-blue-50/50 border border-slate-200/90 hover:border-blue-400/80 rounded-2xl shadow-2xs hover:shadow-md transition-all group flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                          {item.title}
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all" />
                      </div>
                      <p className="text-xs text-slate-500 leading-normal line-clamp-2">
                        {item.desc}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Conversation Thread */}
          {!isLoadingHistory &&
            messages.map((msg, i) => (
              <MessageBubble
                key={i}
                message={msg}
                isGenerating={isGenerating && i === messages.length - 1}
                onOpenSources={onOpenSources}
              />
            ))}

          {/* Typing / Searching Indicator only during active query generation */}
          {isGenerating && messages[messages.length - 1]?.role !== 'assistant' && (
            <div className="flex items-center gap-3 mb-6 animate-in fade-in">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-sm">
                <Sparkles className="w-4 h-4 animate-spin" />
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-xs px-4 py-3 shadow-2xs">
                <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
                  <div className="flex gap-1 items-center">
                    <span className="w-2 h-2 bg-cyan-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  <span>Searching Qdrant & synthesizing grounded citations...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Floating AI Command & Input Bar */}
      <div className="p-4 bg-gradient-to-t from-slate-100 via-slate-50 to-transparent">
        <div className="max-w-3xl mx-auto w-full">
          {/* Floating Stop Generating Action Pill */}
          {isGenerating && (
            <div className="flex justify-center mb-2 animate-in fade-in slide-in-from-bottom-2 duration-150">
              <button
                onClick={handleStop}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-900/90 hover:bg-slate-900 backdrop-blur-md text-white text-xs font-semibold rounded-full shadow-lg border border-slate-700/80 hover:border-red-500/50 hover:text-red-300 transition-all cursor-pointer group"
                title="Stop Generating (Esc)"
              >
                <Square className="w-3 h-3 text-red-400 fill-red-400 group-hover:scale-110 transition-transform" />
                <span>Stop Generating</span>
                <span className="text-[10px] text-slate-400 font-mono ml-1 px-1 py-0.2 bg-slate-800 rounded">Esc</span>
              </button>
            </div>
          )}

          {/* Category Channel Filter Pills */}
          <div className="flex items-center gap-1.5 mb-2.5 overflow-x-auto pb-1 scrollbar-none">
            {CATEGORIES.map((cat) => {
              const isSelected = activeCategory === cat.id
              return (
                <button
                  key={cat.id}
                  onClick={() => onSelectCategory(cat.id)}
                  className={`text-xs px-3 py-1 rounded-full font-medium transition-all ${
                    isSelected
                      ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/20 font-semibold'
                      : 'bg-white hover:bg-slate-200 text-slate-600 border border-slate-200/80 shadow-2xs'
                  }`}
                >
                  {cat.label}
                </button>
              )
            })}
          </div>

          {/* Input Box */}
          <div className="bg-white border border-slate-300 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20 rounded-2xl shadow-lg shadow-slate-200/60 p-2 transition-all flex items-end gap-2">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={handleTextareaInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about latest news... (Enter to send, Shift+Enter for newline)"
              className="flex-1 max-h-36 py-2 px-3 text-sm text-slate-900 placeholder-slate-400 bg-transparent resize-none focus:outline-none leading-relaxed"
            />

            {/* Morphing Send / Stop Button */}
            {isGenerating ? (
              <button
                onClick={handleStop}
                className="p-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-md shadow-rose-500/30 transition-all shrink-0 cursor-pointer animate-pulse flex items-center gap-1.5 px-3"
                title="Stop generation (Esc)"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span className="text-xs font-semibold">Stop</span>
              </button>
            ) : (
              <button
                onClick={() => handleSend()}
                disabled={!input.trim()}
                className="p-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl shadow-md shadow-blue-500/20 transition-all shrink-0 cursor-pointer"
                title="Send query"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Safe Information Footnote */}
          <div className="flex items-center justify-between text-[11px] text-slate-400 px-2 mt-1.5">
            <span>Grounding: Google Gemini 2.5 Flash • Vector Store: Qdrant Cloud</span>
            <button
              onClick={onOpenSources}
              className="hover:text-blue-600 transition-colors flex items-center gap-1 font-medium cursor-pointer"
            >
              <Layers className="w-3 h-3" />
              <span>Manage Feeds</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
