// WatchlistPanel — custom watchlist management + batch analysis launcher

import { useState, useEffect, useRef } from 'react'
import {
  Plus, Trash2, PlayCircle, Loader2, CheckCircle2,
  XCircle, Clock, ChevronRight, RefreshCw,
} from 'lucide-react'
import type { BatchState, BatchTickerState } from '../types'

const API = 'http://localhost:8000'

const RATING_CLASS: Record<string, string> = {
  BUY: 'badge-buy',
  OVERWEIGHT: 'badge-buy',
  HOLD: 'badge-hold',
  UNDERWEIGHT: 'badge-sell',
  SELL: 'badge-sell',
}

function StatusIcon({ status }: { status: BatchTickerState['status'] }) {
  if (status === 'done')    return <CheckCircle2 size={15} className="batch-icon-done" />
  if (status === 'error')   return <XCircle      size={15} className="batch-icon-error" />
  if (status === 'running') return <Loader2      size={15} className="spin batch-icon-running" />
  return <Clock size={15} className="batch-icon-queued" />
}

export default function WatchlistPanel() {
  const [tickers, setTickers] = useState<string[]>([])
  const [inputVal, setInputVal] = useState('')
  const [inputError, setInputError] = useState('')
  const [loading, setLoading] = useState(false)

  const [batch, setBatch] = useState<BatchState | null>(null)
  const esRef = useRef<EventSource | null>(null)

  // ── Load watchlist from backend ─────────────────────────────────
  const loadWatchlist = async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/watchlist/custom`)
      const d = await r.json()
      setTickers(d.tickers || [])
    } catch { /* ignore */ }
    setLoading(false)
  }

  useEffect(() => { loadWatchlist() }, [])

  // ── Add ticker ─────────────────────────────────────────────────
  const handleAdd = async () => {
    const val = inputVal.trim().toUpperCase()
    if (!val) { setInputError('Enter a ticker symbol'); return }
    setInputError('')
    try {
      const r = await fetch(`${API}/api/watchlist/custom`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: val }),
      })
      const d = await r.json()
      if (d.tickers) { setTickers(d.tickers); setInputVal('') }
    } catch { setInputError('Failed to add ticker') }
  }

  // ── Remove ticker ──────────────────────────────────────────────
  const handleRemove = async (ticker: string) => {
    try {
      const r = await fetch(`${API}/api/watchlist/custom/${encodeURIComponent(ticker)}`, {
        method: 'DELETE',
      })
      const d = await r.json()
      if (d.tickers) setTickers(d.tickers)
    } catch { /* ignore */ }
  }

  // ── Run batch analysis via SSE ─────────────────────────────────
  const handleRunBatch = async () => {
    if (!tickers.length) return
    esRef.current?.close()

    // Initialise state
    const initialItems: BatchTickerState[] = tickers.map(t => ({
      ticker: t, status: 'queued',
    }))
    setBatch({ running: true, done: false, total: tickers.length, items: initialItems })

    try {
      const resp = await fetch(`${API}/api/analyze/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers }),
      })

      const reader = resp.body!.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      const process = async () => {
        while (true) {
          const { done, value } = await reader.read()
          if (done) {
            setBatch(prev => prev ? { ...prev, running: false, done: true } : prev)
            break
          }
          buf += decoder.decode(value, { stream: true })
          const lines = buf.split('\n')
          buf = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data:')) continue
            try {
              const evt = JSON.parse(line.slice(5).trim())
              handleBatchEvent(evt)
            } catch { /* skip malformed */ }
          }
        }
      }
      process()
    } catch (e) {
      setBatch(prev => prev ? { ...prev, running: false, done: true } : prev)
    }
  }

  const handleBatchEvent = (evt: Record<string, unknown>) => {
    setBatch(prev => {
      if (!prev) return prev
      const items = [...prev.items]

      if (evt.type === 'ticker_start') {
        const idx = items.findIndex(i => i.ticker === evt.ticker)
        if (idx !== -1) items[idx] = { ...items[idx], status: 'running' }
      } else if (evt.type === 'progress') {
        const idx = items.findIndex(i => i.ticker === evt.ticker)
        if (idx !== -1) items[idx] = { ...items[idx], currentAgent: evt.agent as string }
      } else if (evt.type === 'ticker_result') {
        const idx = items.findIndex(i => i.ticker === evt.ticker)
        if (idx !== -1) items[idx] = {
          ...items[idx], status: 'done',
          rating: evt.rating as string,
          decision: evt.decision as string,
          currentAgent: undefined,
        }
      } else if (evt.type === 'ticker_error') {
        const idx = items.findIndex(i => i.ticker === evt.ticker)
        if (idx !== -1) items[idx] = {
          ...items[idx], status: 'error',
          error: evt.error as string,
          currentAgent: undefined,
        }
      } else if (evt.type === 'batch_done') {
        return { ...prev, items, running: false, done: true }
      }

      return { ...prev, items }
    })
  }

  const donePct = batch
    ? Math.round((batch.items.filter(i => i.status === 'done' || i.status === 'error').length / batch.total) * 100)
    : 0

  return (
    <>
      {/* Header */}
      <div className="page-header">
        <h1>Custom <em>Watchlist</em></h1>
        <p>Add any NSE/global ticker, then run batch AI analysis on all of them at once.</p>
      </div>

      <div className="watchlist-layout">
        {/* ── Left panel: ticker management ─────────────────────────── */}
        <div className="watchlist-left">
          <div className="wl-card">
            <div className="wl-card-header">
              <span className="wl-card-title">Tickers</span>
              <span className="wl-count">{tickers.length}</span>
              <button
                id="btn-refresh-watchlist"
                className="btn-icon"
                onClick={loadWatchlist}
                disabled={loading}
                title="Refresh"
                style={{ marginLeft: 'auto', width: 28, height: 28 }}
              >
                <RefreshCw size={13} className={loading ? 'spin' : ''} />
              </button>
            </div>

            {/* Add input */}
            <div className="wl-add-row">
              <input
                id="wl-ticker-input"
                className={`wl-input ${inputError ? 'wl-input-error' : ''}`}
                placeholder="e.g. INFY.NS, TCS.NS, NVDA"
                value={inputVal}
                onChange={e => { setInputVal(e.target.value); setInputError('') }}
                onKeyDown={e => e.key === 'Enter' && handleAdd()}
              />
              <button
                id="btn-wl-add"
                className="btn-primary"
                onClick={handleAdd}
                style={{ height: 38, padding: '0 1rem', flexShrink: 0 }}
              >
                <Plus size={15} />
              </button>
            </div>
            {inputError && <p className="wl-input-hint">{inputError}</p>}

            {/* Ticker list */}
            {tickers.length === 0 ? (
              <div className="wl-empty">
                <div style={{ fontSize: '2rem', opacity: 0.3, marginBottom: '0.5rem' }}>📋</div>
                <p>No tickers yet. Add one above.</p>
              </div>
            ) : (
              <ul className="wl-ticker-list">
                {tickers.map(t => (
                  <li key={t} className="wl-ticker-item">
                    <ChevronRight size={12} style={{ color: 'var(--blue)', flexShrink: 0 }} />
                    <span className="wl-ticker-sym">{t}</span>
                    <button
                      className="btn-wl-remove"
                      onClick={() => handleRemove(t)}
                      title={`Remove ${t}`}
                    >
                      <Trash2 size={13} />
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {/* Run batch button */}
            <button
              id="btn-run-batch"
              className="btn-primary btn-batch-run"
              disabled={tickers.length === 0 || (batch?.running ?? false)}
              onClick={handleRunBatch}
            >
              {batch?.running
                ? <><Loader2 size={15} className="spin" /> Running…</>
                : <><PlayCircle size={15} /> Analyse All ({tickers.length})</>
              }
            </button>
          </div>
        </div>

        {/* ── Right panel: batch progress ──────────────────────────── */}
        <div className="watchlist-right">
          {!batch ? (
            <div className="wl-batch-empty">
              <div style={{ fontSize: '3rem', opacity: 0.18, marginBottom: '1rem' }}>⚡</div>
              <p>Batch results will appear here once you click <strong>Analyse All</strong>.</p>
            </div>
          ) : (
            <>
              {/* Progress bar */}
              <div className="batch-progress-wrap">
                <div className="batch-progress-header">
                  <span className="batch-progress-label">
                    {batch.done ? 'Batch complete' : `Running analysis…`}
                  </span>
                  <span className="batch-progress-pct">{donePct}%</span>
                </div>
                <div className="batch-progress-bar">
                  <div className="batch-progress-fill" style={{ width: `${donePct}%` }} />
                </div>
              </div>

              {/* Per-ticker status rows */}
              <div className="batch-items">
                {batch.items.map(item => (
                  <div
                    key={item.ticker}
                    className={`batch-item batch-item-${item.status}`}
                  >
                    <StatusIcon status={item.status} />
                    <span className="batch-item-ticker">{item.ticker}</span>

                    {item.status === 'running' && item.currentAgent && (
                      <span className="batch-item-agent">{item.currentAgent}…</span>
                    )}
                    {item.status === 'queued' && (
                      <span className="batch-item-queued">Queued</span>
                    )}
                    {item.status === 'done' && item.rating && (
                      <span className={`decision-pill ${RATING_CLASS[item.rating] ?? 'badge-hold'} batch-rating`}>
                        {item.rating}
                      </span>
                    )}
                    {item.status === 'error' && (
                      <span className="batch-item-error-msg" title={item.error}>Error</span>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  )
}
