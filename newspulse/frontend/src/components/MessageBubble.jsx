import React, { useState, useEffect, useRef } from 'react'
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
  ChevronDown,
  ChevronUp,
  ArrowRight,
  HelpCircle,
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

function HoverTooltip({ citation, position }) {
  if (!citation || !position) return null
  return (
    <div
      style={{ top: `${position.top}px`, left: `${position.left}px` }}
      className="fixed z-50 w-80 max-w-[90vw] p-3.5 bg-slate-900/95 backdrop-blur-md text-white border border-slate-700/80 rounded-2xl shadow-2xl animate-in fade-in zoom-in-95 duration-150 pointer-events-none -translate-x-1/2 -translate-y-full -mt-2"
    >
      <div className="flex items-center justify-between gap-2 mb-1.5 pb-1.5 border-b border-slate-800 text-[11px]">
        <div className="flex items-center gap-1.5 font-semibold text-cyan-400">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          <span className="truncate">{citation.source || 'News Source'}</span>
        </div>
        {citation.published_at && (
          <span className="text-slate-400 text-[10px] shrink-0">
            {new Date(citation.published_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
          </span>
        )}
      </div>
      <h4 className="text-xs font-bold text-white leading-snug line-clamp-2 mb-1.5">
        {citation.title || 'Verified News Report'}
      </h4>
      {citation.summary && (
        <p className="text-[11px] text-slate-300 line-clamp-2 leading-relaxed mb-2 font-normal">
          {citation.summary}
        </p>
      )}
      <div className="flex items-center justify-between text-[10px] text-cyan-300 font-medium pt-1 border-t border-slate-800/80">
        <span>Source #{citation.index}</span>
        <span className="flex items-center gap-0.5">
          Click to read original report ↗
        </span>
      </div>
    </div>
  )
}

export default function MessageBubble({
  message,
  isLatest = false,
  isGenerating = false,
  onOpenSources,
  onSendPrompt,
}) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const [viewMode, setViewMode] = useState('cards') // 'cards' | 'compact'
  const [isSourcesExpanded, setIsSourcesExpanded] = useState(true)

  // Floating hover card state
  const [hoveredCitation, setHoveredCitation] = useState(null)
  const [tooltipPos, setTooltipPos] = useState(null)
  const hoverTimeoutRef = useRef(null)

  const handleCopy = () => {
    if (!message.content) return
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const citations = message.citations || []
  const citationMap = new Map()
  citations.forEach((c) => citationMap.set(c.index, c))

  const handleCitationHover = (citation, e) => {
    if (!citation) return
    const rect = e.currentTarget.getBoundingClientRect()
    hoverTimeoutRef.current = setTimeout(() => {
      setHoveredCitation(citation)
      setTooltipPos({
        top: rect.top,
        left: rect.left + rect.width / 2,
      })
    }, 80)
  }

  const handleCitationLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current)
    setHoveredCitation(null)
    setTooltipPos(null)
  }

  const renderFormattedContent = (content) => {
    if (!content) return null

    if (isUser) {
      return <p className="whitespace-pre-wrap text-sm leading-relaxed">{content}</p>
    }

    // Uniform citation parsing: Handles [1], [1, 5], [1, 2, 4], [1-3], [1][2]
    let processed = content
    if (citations.length > 0) {
      // 1. Expand ranges e.g. [1-3] -> [__CITE_1__][__CITE_2__][__CITE_3__]
      processed = processed.replace(/(?<!!)\[(\d+)\s*[-–]\s*(\d+)\](?!\()/g, (match, start, end) => {
        const s = parseInt(start, 10)
        const e = parseInt(end, 10)
        if (s < e && e - s <= 6) {
          let res = ''
          for (let i = s; i <= e; i++) res += `[__CITE_${i}__]`
          return res
        }
        return match
      })

      // 2. Expand comma-separated e.g. [1, 5] -> [__CITE_1__][__CITE_5__]
      processed = processed.replace(/(?<!!)\[(\d+(?:\s*,\s*\d+)+)\](?!\()/g, (match, nums) => {
        return nums
          .split(',')
          .map((n) => `[__CITE_${n.trim()}__]`)
          .join('')
      })

      // 3. Single bracket citations e.g. [1] -> [__CITE_1__]
      processed = processed.replace(/(?<!!)\[(\d+)\](?!\()/g, (match, num) => `[__CITE_${num}__]`)

      // 4. Map [__CITE_X__] into structured markdown links with clean anchor metadata
      processed = processed.replace(/\[__CITE_(\d+)__\]/g, (match, num) => {
        const c = citationMap.get(parseInt(num, 10))
        if (c && c.url) {
          return `[**[${num}]**](${c.url} "citation-${num}")`
        }
        return `[${num}]`
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
            h1: ({ children }) => <h1 className="text-base font-bold text-slate-900 mt-3.5 mb-1.5">{children}</h1>,
            h2: ({ children }) => <h2 className="text-sm font-bold text-slate-900 mt-3 mb-1">{children}</h2>,
            h3: ({ children }) => <h3 className="text-sm font-semibold text-slate-900 mt-2 mb-1">{children}</h3>,
            blockquote: ({ children }) => (
              <blockquote className="border-l-3 border-blue-500 pl-3 py-1 my-2 bg-blue-50/50 rounded-r text-slate-700 text-xs italic">
                {children}
              </blockquote>
            ),
            a: ({ href, title, children }) => {
              const isCitation = title && title.startsWith('citation-')
              if (isCitation) {
                const num = title.replace('citation-', '')
                const c = citationMap.get(parseInt(num, 10))
                return (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    onMouseEnter={(e) => handleCitationHover(c, e)}
                    onMouseLeave={handleCitationLeave}
                    className="inline-flex items-center gap-0.5 px-1.5 py-0.5 mx-0.5 rounded-md bg-blue-50/90 hover:bg-blue-100 text-blue-700 font-bold text-[11px] border border-blue-200/90 hover:border-blue-400 transition-all shadow-2xs hover:shadow-xs select-none no-underline cursor-pointer group align-baseline leading-none"
                  >
                    <span>[{num}]</span>
                    <ExternalLink className="w-2.5 h-2.5 opacity-60 group-hover:opacity-100 transition-opacity" />
                  </a>
                )
              }

              // Standard hyperlink
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-blue-600 hover:text-blue-800 underline decoration-blue-300 hover:decoration-blue-600 transition-colors inline-flex items-center gap-0.5 px-0.5 rounded hover:bg-blue-50/80 cursor-pointer"
                  title={`Open source: ${href}`}
                >
                  <span>{children}</span>
                  <ExternalLink className="w-3 h-3 text-blue-500 opacity-80 inline shrink-0 ml-0.5 self-center" />
                </a>
              )
            },
          }}
        >
          {processed}
        </ReactMarkdown>
      </div>
    )
  }

  // Generate dynamic contextual follow-up prompt suggestions
  const getFollowUpPrompts = () => {
    if (isUser || !message.content || citations.length === 0 || isGenerating) return []
    const suggestions = []

    if (citations[0]?.title) {
      const cleanTitle = citations[0].title.replace(/ - .*$/, '').replace(/ \| .*$/, '').trim()
      if (cleanTitle.length > 8 && cleanTitle.length < 50) {
        suggestions.push(`Tell me more about ${cleanTitle}`)
      }
    }

    if (citations[1]?.source) {
      suggestions.push(`What are the key reactions reported by ${citations[1].source}?`)
    }

    suggestions.push('What are the main industry and market implications?')
    return suggestions.slice(0, 3)
  }

  const followUpPrompts = getFollowUpPrompts()
  const isThinking = !isUser && !message.content && isGenerating

  return (
    <div className={`flex gap-3 mb-6 ${isUser ? 'justify-end' : 'justify-start'} group animate-in fade-in duration-200`}>
      {/* Hover Tooltip Overlay */}
      <HoverTooltip citation={hoveredCitation} position={tooltipPos} />

      {/* Assistant Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-md shadow-blue-500/20 mt-0.5">
          <Sparkles className="w-4 h-4" />
        </div>
      )}

      {/* Message Bubble Container with Enhanced Contrast & Padding */}
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[96%] sm:max-w-[92%] md:max-w-[88%]`}>
        <div
          className={`w-full rounded-2xl px-5 py-4.5 transition-all ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-xs shadow-md shadow-blue-600/15'
              : 'bg-white text-slate-800 border border-slate-200/90 rounded-tl-xs shadow-[0_2px_8px_-2px_rgba(0,0,0,0.06),0_1px_4px_-1px_rgba(0,0,0,0.04)]'
          }`}
        >
          {/* Loading Animation while Waiting for Output */}
          {isThinking ? (
            <LoadingAnimation />
          ) : (
            renderFormattedContent(message.content)
          )}

          {/* Collapsible Verified News Sources & Intel Section */}
          {!isUser && citations.length > 0 && !isThinking && (
            <div className="mt-4 pt-3.5 border-t border-slate-100 animate-in fade-in duration-300">
              {/* Header & Controls */}
              <div className="flex items-center justify-between gap-2 mb-2.5">
                <button
                  onClick={() => setIsSourcesExpanded(!isSourcesExpanded)}
                  className="flex items-center gap-1.5 text-[11px] font-bold text-slate-600 hover:text-slate-900 uppercase tracking-wider transition-colors cursor-pointer group"
                >
                  <Layers className="w-3.5 h-3.5 text-blue-500" />
                  <span>Verified News Sources & Intel ({citations.length})</span>
                  {isSourcesExpanded ? (
                    <ChevronUp className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-700 transition-colors" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-700 transition-colors" />
                  )}
                </button>

                {isSourcesExpanded && (
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
                )}
              </div>

              {/* Accordion Body */}
              {isSourcesExpanded && (
                <div className="animate-in fade-in slide-in-from-top-1 duration-150">
                  {viewMode === 'cards' ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-1">
                      {citations.map((c) => (
                        <NewsCard key={c.index} citation={c} />
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {citations.map((c) => (
                        <CitationChip key={c.index} citation={c} />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Suggested Follow-up Prompts */}
        {!isUser && isLatest && followUpPrompts.length > 0 && onSendPrompt && (
          <div className="mt-2.5 w-full animate-in fade-in duration-200">
            <div className="flex items-center gap-1 text-[11px] font-semibold text-slate-500 mb-1.5 px-1">
              <Sparkles className="w-3 h-3 text-blue-500" />
              <span>Suggested Follow-ups:</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {followUpPrompts.map((promptText, idx) => (
                <button
                  key={idx}
                  onClick={() => onSendPrompt(promptText)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-blue-50/80 text-slate-700 hover:text-blue-700 text-xs font-medium rounded-xl border border-slate-200/90 hover:border-blue-300 shadow-2xs hover:shadow-xs transition-all cursor-pointer text-left group"
                >
                  <span>{promptText}</span>
                  <ArrowRight className="w-3 h-3 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-0.5 transition-all shrink-0" />
                </button>
              ))}
            </div>
          </div>
        )}

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
