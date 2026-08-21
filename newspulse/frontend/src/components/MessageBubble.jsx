import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  Copy,
  Check,
  Sparkles,
  User,
  Layers,
  LayoutGrid,
  List,
  ExternalLink,
  Radio,
  Clock,
  Compass,
} from 'lucide-react'
import CitationChip from './CitationChip'
import NewsCard from './NewsCard'

function LoadingAnimation() {
  const [step, setStep] = useState(0)

  const STEPS = [
    { text: 'Scanning 20+ global feeds & Qdrant vector database...', icon: '📡' },
    { text: 'Matching semantic context & verifying factual citations...', icon: '⚡' },
    { text: 'Synthesizing verified executive news briefing...', icon: '✍️' },
  ]

  useEffect(() => {
    const timer1 = setTimeout(() => setStep(1), 1800)
    const timer2 = setTimeout(() => setStep(2), 3600)
    return () => {
      clearTimeout(timer1)
      clearTimeout(timer2)
    }
  }, [])

  return (
    <div className="py-2 space-y-4 animate-in fade-in duration-300">
      {/* Dynamic Status Pill */}
      <div className="flex items-center gap-2.5 bg-gradient-to-r from-blue-50 via-indigo-50/60 to-cyan-50 border border-blue-100/90 rounded-2xl px-4 py-2.5 shadow-2xs">
        <span className="text-base animate-bounce select-none">{STEPS[step].icon}</span>
        <div className="flex-1">
          <p className="text-xs font-semibold text-slate-800 tracking-tight">
            {STEPS[step].text}
          </p>
        </div>
        <div className="flex gap-1.5 items-center">
          <span className="w-2 h-2 bg-cyan-500 rounded-full animate-ping" />
          <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" />
        </div>
      </div>

      {/* Shimmering Skeleton Text Lines */}
      <div className="space-y-2.5 px-1.5">
        <div className="h-4 bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 rounded-full w-3/4 animate-pulse" />
        <div className="h-3.5 bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 rounded-full w-full animate-pulse" />
        <div className="h-3.5 bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 rounded-full w-5/6 animate-pulse" />
      </div>

      {/* Shimmering Skeleton Story Cards Preview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
        <div className="h-28 bg-slate-100/80 border border-slate-200/70 rounded-2xl animate-pulse p-3.5 flex flex-col justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-slate-200" />
            <div className="h-3 bg-slate-200 rounded w-24" />
          </div>
          <div className="space-y-1.5">
            <div className="h-2.5 bg-slate-200 rounded w-full" />
            <div className="h-2.5 bg-slate-200 rounded w-3/4" />
          </div>
        </div>
        <div className="h-28 bg-slate-100/80 border border-slate-200/70 rounded-2xl animate-pulse p-3.5 flex flex-col justify-between hidden sm:flex">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-slate-200" />
            <div className="h-3 bg-slate-200 rounded w-24" />
          </div>
          <div className="space-y-1.5">
            <div className="h-2.5 bg-slate-200 rounded w-full" />
            <div className="h-2.5 bg-slate-200 rounded w-3/4" />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function MessageBubble({
  message,
  isGenerating = false,
  onOpenSources,
}) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const [viewMode, setViewMode] = useState('cards') // 'cards' | 'compact'

  const handleCopy = () => {
    if (!message.content) return
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const citations = message.citations || []
  const citationMap = new Map()
  citations.forEach((c) => citationMap.set(c.index, c))

  const renderFormattedContent = (content) => {
    if (!content) return null

    if (isUser) {
      return <p className="whitespace-pre-wrap text-sm leading-relaxed">{content}</p>
    }

    // Auto-link any bracketed [1] citations if they aren't already markdown links
    let processedContent = content
    if (citations.length > 0) {
      // Replace unlinked [1], [2], etc. with direct markdown links [[1]](url)
      processedContent = processedContent.replace(/(?<!!)\[(\d+)\](?!\()/g, (match, num) => {
        const c = citationMap.get(parseInt(num, 10))
        if (c && c.url) {
          return `[**[${num}]**](${c.url})`
        }
        return match
      })
    }

    return (
      <div className="prose prose-sm prose-slate max-w-none text-slate-800 leading-relaxed">
        <ReactMarkdown
          components={{
            p: ({ children }) => <p className="mb-2.5 last:mb-0 text-sm leading-relaxed">{children}</p>,
            ul: ({ children }) => <ul className="my-2.5 ml-4 list-disc space-y-1.5 text-sm">{children}</ul>,
            ol: ({ children }) => <ol className="my-2.5 ml-4 list-decimal space-y-1.5 text-sm">{children}</ol>,
            li: ({ children }) => <li className="text-sm leading-relaxed">{children}</li>,
            strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
            h1: ({ children }) => <h1 className="text-base font-bold text-slate-900 mt-3 mb-1.5">{children}</h1>,
            h2: ({ children }) => <h2 className="text-sm font-bold text-slate-900 mt-2.5 mb-1">{children}</h2>,
            h3: ({ children }) => <h3 className="text-sm font-semibold text-slate-900 mt-2 mb-1">{children}</h3>,
            blockquote: ({ children }) => (
              <blockquote className="border-l-3 border-blue-500 pl-3 py-1 my-2 bg-blue-50/50 rounded-r text-slate-700 text-xs italic">
                {children}
              </blockquote>
            ),
            a: ({ href, children }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-blue-600 hover:text-blue-800 underline decoration-blue-300 hover:decoration-blue-600 transition-colors inline-flex items-center gap-0.5 px-1 py-0.5 rounded hover:bg-blue-50/80 cursor-pointer"
                title={`Open verified source: ${href}`}
              >
                <span>{children}</span>
                <ExternalLink className="w-3 h-3 text-blue-500 opacity-80 inline shrink-0 ml-0.5 self-center" />
              </a>
            ),
          }}
        >
          {processedContent}
        </ReactMarkdown>
      </div>
    )
  }

  const isThinking = !isUser && !message.content && isGenerating

  return (
    <div className={`flex gap-3 mb-6 ${isUser ? 'justify-end' : 'justify-start'} group animate-in fade-in duration-200`}>
      {/* Assistant Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-sm mt-0.5">
          <Sparkles className="w-4 h-4" />
        </div>
      )}

      {/* Message Bubble Container */}
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[95%] sm:max-w-[90%] md:max-w-[85%]`}>
        <div
          className={`w-full rounded-2xl px-4 py-3.5 shadow-2xs ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-xs shadow-blue-500/10'
              : 'bg-white text-slate-800 border border-slate-200/90 rounded-tl-xs shadow-slate-200/50'
          }`}
        >
          {/* Loading Animation while Waiting for Output */}
          {isThinking ? (
            <LoadingAnimation />
          ) : (
            renderFormattedContent(message.content)
          )}

          {/* Visual News Cards & Corresponding Pictures (Revealed upon receiving citations) */}
          {!isUser && citations.length > 0 && (
            <div className="mt-4 pt-3.5 border-t border-slate-100 animate-in fade-in duration-300">
              {/* Header & View Mode Switcher */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  <Layers className="w-3.5 h-3.5 text-blue-500" />
                  <span>Verified News Sources & Intel ({citations.length})</span>
                </div>
                <div className="flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200/60">
                  <button
                    onClick={() => setViewMode('cards')}
                    className={`px-2 py-0.5 rounded-md text-[11px] font-medium flex items-center gap-1 transition-all cursor-pointer ${
                      viewMode === 'cards'
                        ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                    title="Visual Story Cards with Pictures & Links"
                  >
                    <LayoutGrid className="w-3 h-3" />
                    <span className="hidden sm:inline">Visual Cards</span>
                  </button>
                  <button
                    onClick={() => setViewMode('compact')}
                    className={`px-2 py-0.5 rounded-md text-[11px] font-medium flex items-center gap-1 transition-all cursor-pointer ${
                      viewMode === 'compact'
                        ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                    title="Compact Chips"
                  >
                    <List className="w-3 h-3" />
                    <span className="hidden sm:inline">Compact</span>
                  </button>
                </div>
              </div>

              {/* Cards Grid */}
              {viewMode === 'cards' ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-1">
                  {citations.map((c) => (
                    <NewsCard key={c.index} citation={c} />
                  ))}
                </div>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {citations.map((c) => (
                    <CitationChip key={c.index} citation={c} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Message Actions Bar */}
        {!isUser && message.content && (
          <div className="flex items-center gap-2 mt-1.5 ml-1 text-slate-400 text-xs opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-2 py-0.5 rounded-md hover:bg-slate-200 hover:text-slate-700 transition-colors cursor-pointer"
              title="Copy answer"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-[11px] text-emerald-600 font-medium">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span className="text-[11px]">Copy</span>
                </>
              )}
            </button>
            {onOpenSources && citations.length > 0 && (
              <button
                onClick={onOpenSources}
                className="flex items-center gap-1 px-2 py-0.5 rounded-md hover:bg-slate-200 hover:text-slate-700 transition-colors cursor-pointer"
                title="Inspect sources"
              >
                <Layers className="w-3.5 h-3.5" />
                <span className="text-[11px]">Inspect Sources</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-slate-700 text-white flex items-center justify-center shrink-0 shadow-sm mt-0.5">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  )
}
