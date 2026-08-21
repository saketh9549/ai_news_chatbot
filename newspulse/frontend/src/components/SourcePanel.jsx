import React, { useState, useEffect } from 'react'
import {
  Rss,
  Plus,
  RefreshCw,
  Trash2,
  X,
  ExternalLink,
  CheckCircle2,
  Radio,
  Search,
} from 'lucide-react'
import { getSources, addSource, deleteSource, triggerIngestion } from '../api/client'

export default function SourcePanel({ onClose }) {
  const [sources, setSources] = useState([])
  const [showAdd, setShowAdd] = useState(false)
  const [newSource, setNewSource] = useState({ name: '', feed_url: '', category: 'general' })
  const [ingesting, setIngesting] = useState(false)
  const [ingestResult, setIngestResult] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadSources()
  }, [])

  const loadSources = async () => {
    try {
      const data = await getSources()
      setSources(data || [])
    } catch (err) {
      console.error('Failed to load sources:', err)
    }
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    try {
      await addSource(newSource)
      setNewSource({ name: '', feed_url: '', category: 'general' })
      setShowAdd(false)
      loadSources()
    } catch (err) {
      alert(`Error adding source: ${err.message}`)
    }
  }

  const handleDeleteSource = async (id) => {
    if (!confirm('Are you sure you want to remove this RSS feed?')) return
    try {
      await deleteSource(id)
      loadSources()
    } catch (err) {
      alert(`Error deleting source: ${err.message}`)
    }
  }

  const handleIngest = async () => {
    setIngesting(true)
    setIngestResult(null)
    try {
      const result = await triggerIngestion()
      setIngestResult(result)
      loadSources()
    } catch (err) {
      alert(`Ingestion error: ${err.message}`)
    } finally {
      setIngesting(false)
    }
  }

  const filtered = sources.filter(
    (s) =>
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (s.category && s.category.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  return (
    <div className="h-full flex flex-col bg-slate-900 text-slate-200 border-l border-slate-800 select-none">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Rss className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-white tracking-tight">Intelligence Feeds</h2>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
            {sources.length}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Action Bar */}
      <div className="p-3 border-b border-slate-800/80 flex items-center gap-2">
        <button
          onClick={handleIngest}
          disabled={ingesting}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-md shadow-emerald-600/20 transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${ingesting ? 'animate-spin' : ''}`} />
          <span>{ingesting ? 'Ingesting Feeds...' : 'Sync All Feeds'}</span>
        </button>

        <button
          onClick={() => setShowAdd(!showAdd)}
          className={`flex items-center gap-1 px-3 py-2 text-xs font-semibold rounded-xl border transition-all ${
            showAdd
              ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
              : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'
          }`}
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add</span>
        </button>
      </div>

      {/* Ingestion notification */}
      {ingestResult && (
        <div className="m-3 p-3 bg-emerald-950/60 border border-emerald-500/40 rounded-xl text-xs text-emerald-300 animate-in fade-in">
          <div className="flex items-center gap-1.5 font-bold mb-0.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Feed Sync Complete</span>
          </div>
          <p className="text-[11px] text-emerald-200/80">
            Ingested {ingestResult.new_articles} new articles • {ingestResult.new_chunks} chunks indexed to Qdrant.
          </p>
        </div>
      )}

      {/* Add Source Form */}
      {showAdd && (
        <form onSubmit={handleAdd} className="m-3 p-3.5 bg-slate-800/80 border border-slate-700 rounded-xl space-y-2.5 animate-in fade-in">
          <h3 className="text-xs font-bold text-white">Subscribe to RSS Feed</h3>
          <div>
            <label className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Source Name</label>
            <input
              type="text"
              placeholder="e.g. Ars Technica"
              value={newSource.name}
              onChange={(e) => setNewSource({ ...newSource, name: e.target.value })}
              className="w-full px-2.5 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">RSS / Atom Feed URL</label>
            <input
              type="url"
              placeholder="https://feeds.arstechnica.com/arstechnica/index"
              value={newSource.feed_url}
              onChange={(e) => setNewSource({ ...newSource, feed_url: e.target.value })}
              className="w-full px-2.5 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase font-semibold text-slate-400 block mb-1">Category</label>
            <select
              value={newSource.category}
              onChange={(e) => setNewSource({ ...newSource, category: e.target.value })}
              className="w-full px-2.5 py-1.5 text-xs bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="general">General</option>
              <option value="technology">Technology</option>
              <option value="world">World</option>
              <option value="business">Business</option>
              <option value="science">Science</option>
            </select>
          </div>
          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              className="flex-1 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-sm"
            >
              Save Source
            </button>
            <button
              type="button"
              onClick={() => setShowAdd(false)}
              className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs rounded-lg"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Sources Search & List */}
      <div className="flex-1 flex flex-col min-h-0 px-3 py-2">
        <div className="relative mb-2">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search news feeds..."
            className="w-full pl-8 pr-2.5 py-1 text-xs bg-slate-800/80 border border-slate-700/60 rounded-lg text-slate-200 placeholder-slate-400 focus:outline-none focus:border-cyan-500 text-[11px]"
          />
        </div>

        <div className="flex-1 overflow-y-auto space-y-2 scrollbar-none pr-0.5">
          {filtered.map((s) => (
            <div
              key={s.id}
              className="p-3 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-slate-600 rounded-xl transition-all group"
            >
              <div className="flex items-center justify-between gap-1 mb-1">
                <span className="text-xs font-semibold text-white truncate">{s.name}</span>
                {s.category && (
                  <span className="text-[10px] px-2 py-0.2 rounded-full bg-slate-700/80 text-cyan-300 font-medium capitalize shrink-0">
                    {s.category}
                  </span>
                )}
              </div>
              <p className="text-[10px] font-mono text-slate-400 truncate mb-2">{s.feed_url}</p>
              <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-700/40">
                <span className="truncate">
                  {s.last_polled_at
                    ? `Polled: ${new Date(s.last_polled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                    : 'Awaiting first poll'}
                </span>
                <button
                  onClick={() => handleDeleteSource(s.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-400 transition-opacity"
                  title="Remove feed"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}

          {filtered.length === 0 && (
            <p className="text-center text-xs text-slate-400 py-8">No matching RSS sources found.</p>
          )}
        </div>
      </div>
    </div>
  )
}
