// SchedulerCard — pre-market scheduler status + control panel

import { useState, useEffect, useRef, useCallback } from 'react'
import { PlayCircle, Pause, Clock, RefreshCw, Zap, Settings2, CheckCircle2, AlertCircle } from 'lucide-react'

const API = 'http://localhost:8000'

const RATING_CLASS: Record<string, string> = {
  BUY: 'badge-buy',
  OVERWEIGHT: 'badge-buy',
  HOLD: 'badge-hold',
  UNDERWEIGHT: 'badge-sell',
  SELL: 'badge-sell',
}

function fmtIst(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit', month: 'short',
      hour: '2-digit', minute: '2-digit',
      hour12: true,
    })
  } catch { return iso }
}

interface SchedulerStatus {
  enabled: boolean
  running: boolean
  scheduler_active: boolean
  scan_time_ist: string
  next_run: string | null
  last_run: string | null
  last_finished: string | null
  last_analysed_count: number
  last_results: { ticker: string; rating: string; decision: string }[]
  last_errors: string[]
  config: Record<string, unknown>
}

export default function SchedulerCard() {
  const [status, setStatus] = useState<SchedulerStatus | null>(null)
  const [_loading, setLoading] = useState(false)
  const [triggering, setTriggering] = useState(false)
  const [showConfig, setShowConfig] = useState(false)
  const [configTime, setConfigTime] = useState('08:30')
  const [configSource, setConfigSource] = useState<'custom' | 'index'>('custom')
  const [configEnabled, setConfigEnabled] = useState(true)
  const [savingConfig, setSavingConfig] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Fetch status ───────────────────────────────────────────────
  const fetchStatus = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true)
    try {
      const r = await fetch(`${API}/api/scheduler/status`)
      const d: SchedulerStatus = await r.json()
      setStatus(d)
      setConfigTime(d.scan_time_ist || '08:30')
      setConfigSource((d.config?.watchlist_source as 'custom' | 'index') || 'custom')
      setConfigEnabled(d.enabled)
    } catch { /* backend not ready */ }
    if (!quiet) setLoading(false)
  }, [])

  // Poll while running, slow-poll otherwise
  useEffect(() => {
    fetchStatus()
    const interval = setInterval(() => fetchStatus(true), status?.running ? 3000 : 15000)
    pollRef.current = interval
    return () => clearInterval(interval)
  }, [fetchStatus, status?.running])

  // ── Toggle enable/disable ──────────────────────────────────────
  const handleToggle = async () => {
    if (!status) return
    const newEnabled = !status.enabled
    await fetch(`${API}/api/scheduler/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: newEnabled }),
    })
    fetchStatus()
  }

  // ── Run now ────────────────────────────────────────────────────
  const handleRunNow = async () => {
    setTriggering(true)
    try {
      await fetch(`${API}/api/scheduler/run-now`, { method: 'POST' })
      // Start fast-polling
      setTimeout(() => fetchStatus(true), 1000)
    } catch { /* ignore */ }
    setTriggering(false)
  }

  // ── Save config ────────────────────────────────────────────────
  const handleSaveConfig = async () => {
    setSavingConfig(true)
    await fetch(`${API}/api/scheduler/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scan_time_ist: configTime,
        watchlist_source: configSource,
        enabled: configEnabled,
      }),
    })
    await fetchStatus()
    setSavingConfig(false)
    setShowConfig(false)
  }

  if (!status) {
    return (
      <div className="scheduler-card scheduler-card-loading">
        <RefreshCw size={13} className="spin" style={{ color: 'var(--text-dim)' }} />
        <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>Connecting to scheduler…</span>
      </div>
    )
  }

  const isRunning = status.running

  return (
    <div className={`scheduler-card ${isRunning ? 'scheduler-card-running' : ''}`}>
      {/* ── Header row ──────────────────────────────────────────── */}
      <div className="scheduler-header">
        <div className="scheduler-title-row">
          <span className={`scheduler-dot ${isRunning ? 'dot-running' : status.enabled ? 'dot-active' : 'dot-off'}`} />
          <span className="scheduler-label">
            {isRunning ? 'Scan in progress…' : status.enabled ? 'Auto-Scan Enabled' : 'Auto-Scan Disabled'}
          </span>
        </div>

        <div className="scheduler-actions">
          <button
            id="btn-scheduler-runnow"
            className="btn-ghost"
            style={{ height: 30, fontSize: '0.75rem', gap: '0.3rem' }}
            onClick={handleRunNow}
            disabled={isRunning || triggering}
            title="Run pre-market scan now"
          >
            {triggering
              ? <><RefreshCw size={12} className="spin" /> Starting…</>
              : <><Zap size={12} /> Run Now</>
            }
          </button>

          <button
            id="btn-scheduler-toggle"
            className={`btn-ghost ${status.enabled ? '' : 'active'}`}
            style={{ height: 30, fontSize: '0.75rem', gap: '0.3rem' }}
            onClick={handleToggle}
            title={status.enabled ? 'Disable auto-scan' : 'Enable auto-scan'}
          >
            {status.enabled ? <><Pause size={12} /> Disable</> : <><PlayCircle size={12} /> Enable</>}
          </button>

          <button
            id="btn-scheduler-config"
            className={`btn-icon ${showConfig ? 'active' : ''}`}
            style={{ width: 30, height: 30 }}
            onClick={() => setShowConfig(v => !v)}
            title="Configure scheduler"
          >
            <Settings2 size={13} />
          </button>
        </div>
      </div>

      {/* ── Meta info row ────────────────────────────────────────── */}
      <div className="scheduler-meta">
        <span className="sched-meta-item">
          <Clock size={11} />
          Daily at <strong>{status.scan_time_ist} IST</strong>
        </span>
        {status.next_run && (
          <span className="sched-meta-item sched-meta-sep">
            Next: <strong>{fmtIst(status.next_run)}</strong>
          </span>
        )}
        {status.last_run && (
          <span className="sched-meta-item sched-meta-sep">
            Last: {fmtIst(status.last_run)}
          </span>
        )}
        <span className="sched-meta-item sched-meta-sep sched-source-badge">
          Source: <strong>{(status.config?.watchlist_source as string) === 'custom' ? 'Custom Watchlist' : status.config?.index_name as string || 'NIFTY 50'}</strong>
        </span>
      </div>

      {/* ── Running progress ─────────────────────────────────────── */}
      {isRunning && (
        <div className="scheduler-running-bar">
          <div className="scheduler-running-shimmer" />
        </div>
      )}

      {/* ── Last results summary ─────────────────────────────────── */}
      {!isRunning && status.last_results.length > 0 && (
        <div className="scheduler-results">
          <span className="sched-results-label">
            <CheckCircle2 size={11} />
            Last scan: {status.last_analysed_count} analysed
          </span>
          <div className="sched-pills-row">
            {status.last_results.map(r => (
              <span key={r.ticker} className="sched-result-chip">
                <span className="sched-chip-ticker">{r.ticker.replace('.NS', '')}</span>
                <span className={`decision-pill ${RATING_CLASS[r.rating] ?? 'badge-hold'}`} style={{ fontSize: '0.55rem', padding: '0.1rem 0.35rem' }}>
                  {r.rating}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Errors ──────────────────────────────────────────────── */}
      {!isRunning && status.last_errors.length > 0 && (
        <div className="scheduler-errors">
          <AlertCircle size={11} />
          {status.last_errors.length} error{status.last_errors.length > 1 ? 's' : ''} in last scan
        </div>
      )}

      {/* ── Config panel ─────────────────────────────────────────── */}
      {showConfig && (
        <div className="scheduler-config-panel">
          <div className="sched-config-row">
            <label className="field-label" htmlFor="sched-time">Scan Time (IST)</label>
            <input
              id="sched-time"
              type="time"
              className="wl-input"
              style={{ width: 120, height: 32, fontSize: '0.8rem' }}
              value={configTime}
              onChange={e => setConfigTime(e.target.value)}
            />
          </div>

          <div className="sched-config-row">
            <label className="field-label" htmlFor="sched-source">Watchlist Source</label>
            <select
              id="sched-source"
              className="select-input"
              style={{ width: 180, height: 32, fontSize: '0.8rem', padding: '0 1.5rem 0 0.6rem' }}
              value={configSource}
              onChange={e => setConfigSource(e.target.value as 'custom' | 'index')}
            >
              <option value="custom">Custom Watchlist</option>
              <option value="index">NSE Index</option>
            </select>
          </div>

          <div className="sched-config-row">
            <label className="field-label">
              <input
                type="checkbox"
                checked={configEnabled}
                onChange={e => setConfigEnabled(e.target.checked)}
                style={{ marginRight: '0.4rem' }}
              />
              Enabled
            </label>
          </div>

          <div className="sched-config-actions">
            <button className="btn-ghost" style={{ height: 30 }} onClick={() => setShowConfig(false)}>
              Cancel
            </button>
            <button
              id="btn-scheduler-save"
              className="btn-primary"
              style={{ height: 30, fontSize: '0.8rem', padding: '0 1rem' }}
              onClick={handleSaveConfig}
              disabled={savingConfig}
            >
              {savingConfig ? <><RefreshCw size={12} className="spin" /> Saving…</> : 'Save'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
