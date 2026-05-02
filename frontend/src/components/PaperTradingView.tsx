// PaperTradingView.tsx — Live prices, signals, paper portfolio dashboard

import { useState, useEffect, useCallback, useRef } from 'react'
import type { PaperPosition, PaperPortfolio, SignalData } from '../types'

const API = 'http://localhost:8000'

const NIFTY50 = [
  'RELIANCE','TCS','HDFCBANK','INFY','ICICIBANK','HINDUNILVR','ITC','SBIN',
  'BHARTIARTL','KOTAKBANK','LT','AXISBANK','WIPRO','ASIANPAINT','MARUTI',
  'TITAN','SUNPHARMA','BAJFINANCE','HCLTECH','TATAMOTORS','NTPC','POWERGRID',
  'ULTRACEMCO','ONGC','TATASTEEL','JSWSTEEL','ADANIENT','ADANIPORTS','COALINDIA',
  'BPCL','TECHM','INDUSINDBK','HINDALCO','DRREDDY','CIPLA','DIVISLAB',
  'BRITANNIA','EICHERMOT','APOLLOHOSP','NESTLEIND','SBILIFE','HDFCLIFE',
  'TATACONSUM','HEROMOTOCO','BAJAJFINSV','SHRIRAMFIN','BEL',
]

const NIFTY_BANK = [
  'HDFCBANK','ICICIBANK','SBIN','KOTAKBANK','AXISBANK','INDUSINDBK',
  'BANKBARODA','AUBANK','BANDHANBNK','FEDERALBNK','IDFCFIRSTB','PNB',
]

function scoreColor(score: number): string {
  if (score >= 0.65) return 'signal-buy'
  if (score <= 0.35) return 'signal-sell'
  return 'signal-hold'
}

function scoreLabel(score: number): string {
  if (score >= 0.65) return 'BUY'
  if (score <= 0.35) return 'SELL'
  return 'HOLD'
}

function pnlClass(val: number): string {
  return val > 0 ? 'pnl-positive' : val < 0 ? 'pnl-negative' : 'pnl-zero'
}

function fmt(n: number, dec = 2): string {
  return n.toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec })
}

// ── Scanner types ──────────────────────────────────────────────────────────

interface ScannerStatus {
  enabled: boolean
  is_running: boolean
  last_scan_time: string | null
  scans_today: number
  auto_trades_today: number
  auto_exits_today: number
  errors: string[]
  config: ScannerConfig
  last_scan_results: {
    movers_found?: number
    signals_computed?: number
    auto_buys?: Array<{ symbol: string; price: number; score: number }>
    auto_sells?: Array<{ symbol: string; exit_price: number; pnl: number }>
    position_exits?: Array<{ symbol: string; exit_price: number; pnl: number; reason: string }>
    status?: string
  }
}

interface ScannerConfig {
  enabled: boolean
  interval_minutes: number
  buy_score_threshold: number
  sell_score_threshold: number
  max_auto_positions: number
  force_close_time: string
  position_size_pct: number
  mover_threshold_pct: number
}

// ── Scanner Control Panel ─────────────────────────────────────────────────

function ScannerControlPanel() {
  const [status, setStatus] = useState<ScannerStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [showConfig, setShowConfig] = useState(false)
  const [configDraft, setConfigDraft] = useState<Partial<ScannerConfig>>({})
  const [scanningNow, setScanningNow] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/scanner/status`)
      if (r.ok) setStatus(await r.json())
    } catch { /* silent */ }
  }, [])

  // Poll status every 10s
  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, 10_000)
    return () => clearInterval(id)
  }, [fetchStatus])

  const handleToggle = async () => {
    if (!status) return
    setLoading(true)
    try {
      const endpoint = status.is_running ? '/api/scanner/stop' : '/api/scanner/start'
      const r = await fetch(`${API}${endpoint}`, { method: 'POST' })
      if (r.ok) {
        setTimeout(fetchStatus, 500)
      }
    } catch { /* silent */ }
    setLoading(false)
  }

  const handleScanNow = async () => {
    setScanningNow(true)
    try {
      await fetch(`${API}/api/scanner/scan-now`, { method: 'POST' })
      setTimeout(fetchStatus, 1000)
    } catch { /* silent */ }
    setScanningNow(false)
  }

  const handleSaveConfig = async () => {
    try {
      await fetch(`${API}/api/scanner/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configDraft),
      })
      setShowConfig(false)
      fetchStatus()
    } catch { /* silent */ }
  }

  const openConfigPanel = () => {
    if (status?.config) setConfigDraft({ ...status.config })
    setShowConfig(!showConfig)
  }

  const isRunning = status?.is_running ?? false
  const lastScan = status?.last_scan_results ?? {}
  const timeSinceLastScan = status?.last_scan_time
    ? Math.round((Date.now() - new Date(status.last_scan_time).getTime()) / 60000)
    : null

  return (
    <div className={`scanner-panel ${isRunning ? 'scanner-active' : ''}`}>
      {/* Header row */}
      <div className="scanner-header">
        <div className="scanner-title-group">
          <span className={`scanner-dot ${isRunning ? 'dot-running' : 'dot-stopped'}`} />
          <h3 className="scanner-title">Auto Trading Bot</h3>
          <span className={`scanner-status-badge ${isRunning ? 'badge-running' : 'badge-stopped'}`}>
            {isRunning ? '● ACTIVE' : '○ STOPPED'}
          </span>
        </div>

        <div className="scanner-actions">
          <button
            className="scanner-scan-btn"
            onClick={handleScanNow}
            disabled={scanningNow}
            title="Run a single scan now"
          >
            {scanningNow ? '⏳ Scanning...' : '⚡ Scan Now'}
          </button>
          <button
            className="scanner-config-btn"
            onClick={openConfigPanel}
            title="Configure scanner"
          >
            ⚙️
          </button>
          <button
            className={`scanner-toggle-btn ${isRunning ? 'toggle-stop' : 'toggle-start'}`}
            onClick={handleToggle}
            disabled={loading}
          >
            {loading ? '...' : isRunning ? '⏹ Stop Bot' : '▶ Start Bot'}
          </button>
        </div>
      </div>

      {/* Stats row */}
      {status && (
        <div className="scanner-stats">
          <div className="scanner-stat">
            <span className="scanner-stat-label">Scans</span>
            <span className="scanner-stat-value">{status.scans_today}</span>
          </div>
          <div className="scanner-stat">
            <span className="scanner-stat-label">Auto Trades</span>
            <span className="scanner-stat-value scanner-stat-accent">{status.auto_trades_today}</span>
          </div>
          <div className="scanner-stat">
            <span className="scanner-stat-label">Auto Exits</span>
            <span className="scanner-stat-value">{status.auto_exits_today}</span>
          </div>
          <div className="scanner-stat">
            <span className="scanner-stat-label">Last Scan</span>
            <span className="scanner-stat-value">
              {timeSinceLastScan != null
                ? timeSinceLastScan === 0 ? 'Just now' : `${timeSinceLastScan}m ago`
                : '—'}
            </span>
          </div>
          <div className="scanner-stat">
            <span className="scanner-stat-label">Movers</span>
            <span className="scanner-stat-value">{lastScan.movers_found ?? '—'}</span>
          </div>
          <div className="scanner-stat">
            <span className="scanner-stat-label">Interval</span>
            <span className="scanner-stat-value">{status.config?.interval_minutes ?? 5}m</span>
          </div>
        </div>
      )}

      {/* Recent activity feed */}
      {lastScan.auto_buys && lastScan.auto_buys.length > 0 && (
        <div className="scanner-activity">
          {lastScan.auto_buys.map((b, i) => (
            <span key={`buy-${i}`} className="scanner-event scanner-event-buy">
              🤖 BUY {b.symbol} @ ₹{fmt(b.price)} (score: {fmt(b.score * 100, 0)}%)
            </span>
          ))}
        </div>
      )}
      {lastScan.auto_sells && lastScan.auto_sells.length > 0 && (
        <div className="scanner-activity">
          {lastScan.auto_sells.map((s, i) => (
            <span key={`sell-${i}`} className={`scanner-event ${s.pnl >= 0 ? 'scanner-event-win' : 'scanner-event-loss'}`}>
              🤖 SELL {s.symbol} @ ₹{fmt(s.exit_price)} → {s.pnl >= 0 ? '+' : ''}₹{fmt(s.pnl)}
            </span>
          ))}
        </div>
      )}
      {lastScan.position_exits && lastScan.position_exits.length > 0 && (
        <div className="scanner-activity">
          {lastScan.position_exits.map((e, i) => (
            <span key={`exit-${i}`} className={`scanner-event ${e.pnl >= 0 ? 'scanner-event-win' : 'scanner-event-loss'}`}>
              🔔 EXIT {e.symbol} [{e.reason}] → {e.pnl >= 0 ? '+' : ''}₹{fmt(e.pnl)}
            </span>
          ))}
        </div>
      )}

      {/* Market status */}
      {lastScan.status === 'market_closed' && (
        <div className="scanner-info-banner">
          📅 Market is closed — scanner will activate on the next trading day
        </div>
      )}
      {lastScan.status === 'circuit_breaker' && (
        <div className="scanner-warn-banner">
          ⏸ Circuit breaker active — paused after 3 consecutive losses
        </div>
      )}
      {lastScan.status === 'daily_loss_limit' && (
        <div className="scanner-warn-banner">
          🛑 Daily loss limit reached — no more trades today
        </div>
      )}

      {/* Config panel */}
      {showConfig && status?.config && (
        <div className="scanner-config-panel">
          <h4>Scanner Configuration</h4>
          <div className="scanner-config-grid">
            <label>
              Interval (min)
              <input
                type="number" min={1} max={30}
                value={configDraft.interval_minutes ?? status.config.interval_minutes}
                onChange={e => setConfigDraft(d => ({ ...d, interval_minutes: +e.target.value }))}
              />
            </label>
            <label>
              Buy Threshold
              <input
                type="number" min={0.5} max={0.9} step={0.05}
                value={configDraft.buy_score_threshold ?? status.config.buy_score_threshold}
                onChange={e => setConfigDraft(d => ({ ...d, buy_score_threshold: +e.target.value }))}
              />
            </label>
            <label>
              Sell Threshold
              <input
                type="number" min={0.1} max={0.5} step={0.05}
                value={configDraft.sell_score_threshold ?? status.config.sell_score_threshold}
                onChange={e => setConfigDraft(d => ({ ...d, sell_score_threshold: +e.target.value }))}
              />
            </label>
            <label>
              Max Positions
              <input
                type="number" min={1} max={5}
                value={configDraft.max_auto_positions ?? status.config.max_auto_positions}
                onChange={e => setConfigDraft(d => ({ ...d, max_auto_positions: +e.target.value }))}
              />
            </label>
            <label>
              Position Size %
              <input
                type="number" min={1} max={10} step={0.5}
                value={configDraft.position_size_pct ?? status.config.position_size_pct}
                onChange={e => setConfigDraft(d => ({ ...d, position_size_pct: +e.target.value }))}
              />
            </label>
            <label>
              Mover Threshold %
              <input
                type="number" min={0.1} max={3} step={0.1}
                value={configDraft.mover_threshold_pct ?? status.config.mover_threshold_pct}
                onChange={e => setConfigDraft(d => ({ ...d, mover_threshold_pct: +e.target.value }))}
              />
            </label>
          </div>
          <div className="scanner-config-actions">
            <button className="scanner-config-save" onClick={handleSaveConfig}>💾 Save</button>
            <button className="scanner-config-cancel" onClick={() => setShowConfig(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}


function PortfolioCard({ portfolio }: { portfolio: PaperPortfolio | null }) {
  if (!portfolio) return (
    <div className="pt-portfolio-card pt-skeleton">
      <div className="skeleton-line" /><div className="skeleton-line short" />
    </div>
  )
  const totalPnlPct = portfolio.total_pnl_pct
  return (
    <div className="pt-portfolio-card">
      <div className="pt-portfolio-header">
        <span className="pt-portfolio-title">Paper Portfolio</span>
        <span className="pt-live-badge">LIVE</span>
      </div>
      <div className="pt-portfolio-stats">
        <div className="pt-stat">
          <span className="pt-stat-label">Capital</span>
          <span className="pt-stat-value">₹{fmt(portfolio.capital)}</span>
        </div>
        <div className="pt-stat">
          <span className="pt-stat-label">Total P&L</span>
          <span className={`pt-stat-value ${pnlClass(portfolio.total_pnl)}`}>
            {portfolio.total_pnl >= 0 ? '+' : ''}₹{fmt(portfolio.total_pnl)}
            <small className={pnlClass(totalPnlPct)}>
              {' '}({totalPnlPct >= 0 ? '+' : ''}{fmt(totalPnlPct)}%)
            </small>
          </span>
        </div>
        <div className="pt-stat">
          <span className="pt-stat-label">Today's P&L</span>
          <span className={`pt-stat-value ${pnlClass(portfolio.daily_pnl)}`}>
            {portfolio.daily_pnl >= 0 ? '+' : ''}₹{fmt(portfolio.daily_pnl)}
          </span>
        </div>
        <div className="pt-stat">
          <span className="pt-stat-label">Positions</span>
          <span className="pt-stat-value">{portfolio.position_count} / 5</span>
        </div>
        <div className="pt-stat">
          <span className="pt-stat-label">Win Rate</span>
          <span className="pt-stat-value">
            {portfolio.total_win_rate != null ? `${portfolio.total_win_rate}%` : '—'}
          </span>
        </div>
        <div className="pt-stat">
          <span className="pt-stat-label">Today</span>
          <span className="pt-stat-value">{portfolio.daily_wins}W / {portfolio.daily_losses}L</span>
        </div>
      </div>
      {portfolio.daily_loss_limit_active && (
        <div className="pt-alert-banner">
          🛑 Daily loss limit reached — no new trades today
        </div>
      )}
    </div>
  )
}

function OpenPositionsTable({
  positions,
  quotes,
  onExit,
}: {
  positions: PaperPosition[]
  quotes: Record<string, number>
  onExit: (symbol: string, price: number) => void
}) {
  if (positions.length === 0) return (
    <div className="pt-empty-state">
      <span>📭</span>
      <p>No open positions. Signals scoring ≥ 0.65 will auto-suggest a trade.</p>
    </div>
  )
  return (
    <div className="pt-table-wrap">
      <table className="pt-table">
        <thead>
          <tr>
            <th>Symbol</th><th>Qty</th><th>Entry</th><th>LTP</th>
            <th>Unr. P&L</th><th>SL</th><th>Target</th><th>Strategy</th><th></th>
          </tr>
        </thead>
        <tbody>
          {positions.map(pos => {
            const ltp = quotes[pos.symbol] ?? pos.entry_price
            const pnl = (ltp - pos.entry_price) * pos.quantity
            const pnlPct = ((ltp - pos.entry_price) / pos.entry_price) * 100
            return (
              <tr key={pos.symbol}>
                <td className="pt-symbol">{pos.symbol}</td>
                <td>{pos.quantity}</td>
                <td>₹{fmt(pos.entry_price)}</td>
                <td>₹{fmt(ltp)}</td>
                <td className={pnlClass(pnl)}>
                  {pnl >= 0 ? '+' : ''}₹{fmt(pnl)}
                  <small> ({pnlPct >= 0 ? '+' : ''}{fmt(pnlPct)}%)</small>
                </td>
                <td className="pt-sl">₹{fmt(pos.stop_loss)}</td>
                <td className="pt-target">₹{fmt(pos.target_price)}</td>
                <td><span className="pt-strategy-badge">{pos.strategy}</span></td>
                <td>
                  <button
                    className="pt-exit-btn"
                    onClick={() => onExit(pos.symbol, ltp)}
                  >
                    Exit
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function SignalRow({
  symbol,
  ltp,
  signal,
  loading,
  onBuy,
}: {
  symbol: string
  ltp: number | null
  signal: SignalData | null
  loading: boolean
  onBuy: (symbol: string, signal: SignalData, ltp: number) => void
}) {
  const score = signal?.score ?? null

  return (
    <tr className={score != null ? scoreColor(score) + '-row' : ''}>
      <td className="pt-symbol">{symbol}</td>
      <td>{ltp != null ? `₹${fmt(ltp)}` : '—'}</td>
      <td>
        {loading ? (
          <span className="pt-loading-dot">···</span>
        ) : score != null ? (
          <div className="pt-score-bar">
            <div className="pt-score-fill" style={{ width: `${score * 100}%` }} />
            <span className="pt-score-text">{fmt(score * 100, 0)}%</span>
          </div>
        ) : '—'}
      </td>
      <td>
        {score != null ? (
          <span className={`signal-badge ${scoreColor(score)}`}>{scoreLabel(score)}</span>
        ) : '—'}
      </td>
      <td>{signal?.signals.rsi != null ? fmt(signal.signals.rsi, 1) : '—'}</td>
      <td>
        {signal?.signals.macd_bullish != null
          ? (signal.signals.macd_bullish ? '🟢 Bull' : '🔴 Bear')
          : '—'}
      </td>
      <td>
        {signal?.signals.above_vwap != null
          ? (signal.signals.above_vwap ? '↑ Above' : '↓ Below')
          : '—'}
      </td>
      <td>{signal?.signals.atr != null ? fmt(signal.signals.atr, 1) : '—'}</td>
      <td>
        {score != null && score >= 0.65 && ltp != null ? (
          <button className="pt-buy-btn" onClick={() => onBuy(symbol, signal!, ltp)}>
            Paper BUY
          </button>
        ) : null}
      </td>
    </tr>
  )
}

// ── Trade history ─────────────────────────────────────────────────────────

interface TradeRecord {
  id: number
  symbol: string
  side: string
  quantity: number
  entry_price: number
  exit_price: number | null
  pnl: number | null
  pnl_pct: number | null
  is_win: number | null
  exit_reason: string | null
  strategy: string
  entry_time: string
  exit_time: string | null
}

function TradeHistoryTable({ trades }: { trades: TradeRecord[] }) {
  if (trades.length === 0) return (
    <div className="pt-empty-state">
      <span>📋</span>
      <p>No completed trades yet.</p>
    </div>
  )
  return (
    <div className="pt-table-wrap">
      <table className="pt-table">
        <thead>
          <tr>
            <th>Symbol</th><th>Qty</th><th>Entry</th><th>Exit</th>
            <th>P&L</th><th>Return</th><th>Reason</th><th>Strategy</th><th>Date</th>
          </tr>
        </thead>
        <tbody>
          {trades.map(t => (
            <tr key={t.id} className={t.is_win === 1 ? 'win-row' : t.is_win === 0 ? 'loss-row' : ''}>
              <td className="pt-symbol">{t.symbol}</td>
              <td>{t.quantity}</td>
              <td>₹{fmt(t.entry_price)}</td>
              <td>{t.exit_price != null ? `₹${fmt(t.exit_price)}` : '—'}</td>
              <td className={t.pnl != null ? pnlClass(t.pnl) : ''}>
                {t.pnl != null ? `${t.pnl >= 0 ? '+' : ''}₹${fmt(t.pnl)}` : '—'}
              </td>
              <td className={t.pnl_pct != null ? pnlClass(t.pnl_pct) : ''}>
                {t.pnl_pct != null ? `${t.pnl_pct >= 0 ? '+' : ''}${fmt(t.pnl_pct)}%` : '—'}
              </td>
              <td>
                <span className={`exit-reason-badge ${t.exit_reason?.toLowerCase().replace('_', '-') ?? ''}`}>
                  {t.exit_reason ?? '—'}
                </span>
              </td>
              <td><span className="pt-strategy-badge">{t.strategy}</span></td>
              <td className="pt-date">{t.entry_time?.slice(0, 10)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Buy modal ─────────────────────────────────────────────────────────────

interface BuyModalProps {
  symbol: string
  ltp: number
  signal: SignalData
  onConfirm: (qty: number, sl: number, target: number) => void
  onClose: () => void
}

function BuyModal({ symbol, ltp, signal, onConfirm, onClose }: BuyModalProps) {
  const atr = signal.signals.atr ?? ltp * 0.01
  const defaultSL = parseFloat((ltp - atr * 1.5).toFixed(2))
  const defaultTarget = parseFloat((ltp + atr * 2.5).toFixed(2))
  const [qty, setQty] = useState(1)
  const [sl, setSL] = useState(defaultSL)
  const [target, setTarget] = useState(defaultTarget)

  const riskReward = ((target - ltp) / (ltp - sl)).toFixed(2)
  const estimatedPnl = ((target - ltp) * qty).toFixed(2)

  return (
    <div className="pt-modal-overlay" onClick={onClose}>
      <div className="pt-modal" onClick={e => e.stopPropagation()}>
        <div className="pt-modal-header">
          <h3>Paper BUY — {symbol}</h3>
          <button className="pt-modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="pt-modal-body">
          <div className="pt-modal-price">
            LTP: <strong>₹{fmt(ltp)}</strong>
            <span className={`signal-badge ${scoreColor(signal.score)}`}>
              Score: {fmt(signal.score * 100, 0)}%
            </span>
          </div>
          <div className="pt-modal-fields">
            <label>
              Quantity
              <input type="number" min={1} value={qty} onChange={e => setQty(+e.target.value)} />
            </label>
            <label>
              Stop Loss (₹)
              <input type="number" step={0.05} value={sl} onChange={e => setSL(+e.target.value)} />
            </label>
            <label>
              Target (₹)
              <input type="number" step={0.05} value={target} onChange={e => setTarget(+e.target.value)} />
            </label>
          </div>
          <div className="pt-modal-summary">
            <span>Risk/Reward: <strong>{riskReward}x</strong></span>
            <span>Est. Profit: <strong className="pnl-positive">+₹{estimatedPnl}</strong></span>
            <span>Cost: <strong>₹{fmt(ltp * qty)}</strong></span>
          </div>
        </div>
        <div className="pt-modal-footer">
          <button className="pt-modal-cancel" onClick={onClose}>Cancel</button>
          <button className="pt-modal-confirm" onClick={() => onConfirm(qty, sl, target)}>
            Confirm BUY
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main view ─────────────────────────────────────────────────────────────

export default function PaperTradingView() {
  const [activeIndex, setActiveIndex] = useState<'NIFTY 50' | 'NIFTY BANK'>('NIFTY 50')
  const [activeTab, setActiveTab] = useState<'signals' | 'positions' | 'history'>('signals')

  const [portfolio, setPortfolio] = useState<PaperPortfolio | null>(null)
  const [quotes, setQuotes] = useState<Record<string, number>>({})
  const [signals, setSignals] = useState<Record<string, SignalData | null>>({})
  const [signalLoading, setSignalLoading] = useState<Record<string, boolean>>({})
  const [trades, setTrades] = useState<TradeRecord[]>([])
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)
  const [buyModal, setBuyModal] = useState<{ symbol: string; ltp: number; signal: SignalData } | null>(null)

  const symbols = activeIndex === 'NIFTY 50' ? NIFTY50 : NIFTY_BANK
  const quoteInterval = useRef<ReturnType<typeof setInterval> | null>(null)

  // Show toast
  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  // Fetch portfolio
  const fetchPortfolio = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/paper/portfolio`)
      if (r.ok) setPortfolio(await r.json())
    } catch { /* silent */ }
  }, [])

  // Fetch trade history
  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/paper/history?limit=30`)
      if (r.ok) {
        const d = await r.json()
        setTrades(d.trades ?? [])
      }
    } catch { /* silent */ }
  }, [])

  // Fetch LTPs for current index — single batch call instead of 50 individual ones
  const fetchQuotes = useCallback(async () => {
    try {
      const indexParam = activeIndex === 'NIFTY 50' ? 'NIFTY50' : 'NIFTY_BANK'
      const r = await fetch(`${API}/api/upstox/ltp/batch?index=${indexParam}`)
      if (r.ok) {
        const d = await r.json()
        setQuotes(prev => ({ ...prev, ...(d.prices ?? {}) }))
      }
    } catch { /* silent */ }
  }, [activeIndex])

  // Fetch signals one by one (heavy — only on demand)
  const fetchSignals = useCallback(async () => {
    setSignalLoading(prev => {
      const next = { ...prev }
      symbols.forEach(s => { next[s] = true })
      return next
    })

    for (const sym of symbols) {
      try {
        const r = await fetch(`${API}/api/upstox/signals/${sym}`)
        if (r.ok) {
          const d = await r.json()
          setSignals(prev => ({ ...prev, [sym]: d.signal }))
        } else {
          setSignals(prev => ({ ...prev, [sym]: null }))
        }
      } catch {
        setSignals(prev => ({ ...prev, [sym]: null }))
      }
      setSignalLoading(prev => ({ ...prev, [sym]: false }))
      // Small delay between requests to respect rate limits
      await new Promise(res => setTimeout(res, 200))
    }
  }, [symbols])

  // Mount: initial load
  useEffect(() => {
    fetchPortfolio()
    fetchHistory()
    fetchQuotes()
  }, [fetchPortfolio, fetchHistory, fetchQuotes])

  // Poll portfolio + quotes every 30s
  useEffect(() => {
    quoteInterval.current = setInterval(() => {
      fetchPortfolio()
      fetchQuotes()
    }, 30_000)
    return () => { if (quoteInterval.current) clearInterval(quoteInterval.current) }
  }, [fetchPortfolio, fetchQuotes])

  // Reset signals when switching index
  useEffect(() => {
    setSignals({})
    setSignalLoading({})
    fetchQuotes()
  }, [activeIndex, fetchQuotes])

  // Enter paper trade
  const handleBuyConfirm = async (qty: number, sl: number, target: number) => {
    if (!buyModal) return
    const { symbol, ltp } = buyModal
    try {
      const r = await fetch(`${API}/api/paper/buy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol, quantity: qty, price: ltp,
          stop_loss: sl, target_price: target, strategy: 'signal_based',
        }),
      })
      const d = await r.json()
      if (r.ok) {
        showToast(`✅ BUY ${qty}x ${symbol} @ ₹${ltp}`)
        fetchPortfolio()
      } else {
        showToast(d.detail ?? 'Trade failed', 'error')
      }
    } catch {
      showToast('Failed to place trade', 'error')
    }
    setBuyModal(null)
  }

  // Exit paper trade
  const handleExit = async (symbol: string, price: number) => {
    try {
      const r = await fetch(`${API}/api/paper/sell`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, price, reason: 'MANUAL' }),
      })
      const d = await r.json()
      if (r.ok) {
        const pnl = d.pnl ?? 0
        showToast(`${pnl >= 0 ? '✅' : '❌'} SELL ${symbol} — P&L: ${pnl >= 0 ? '+' : ''}₹${fmt(pnl)}`)
        fetchPortfolio()
        fetchHistory()
      } else {
        showToast(d.detail ?? 'Exit failed', 'error')
      }
    } catch {
      showToast('Failed to exit trade', 'error')
    }
  }

  return (
    <div className="pt-view">
      {/* Toast */}
      {toast && (
        <div className={`pt-toast ${toast.type}`}>{toast.msg}</div>
      )}

      {/* Buy Modal */}
      {buyModal && (
        <BuyModal
          symbol={buyModal.symbol}
          ltp={buyModal.ltp}
          signal={buyModal.signal}
          onConfirm={handleBuyConfirm}
          onClose={() => setBuyModal(null)}
        />
      )}

      {/* Auto-Scanner Control Panel */}
      <ScannerControlPanel />

      {/* Portfolio card */}
      <PortfolioCard portfolio={portfolio} />

      {/* Controls row */}
      <div className="pt-controls">
        <div className="pt-index-tabs">
          {(['NIFTY 50', 'NIFTY BANK'] as const).map(idx => (
            <button
              key={idx}
              className={`pt-index-tab ${activeIndex === idx ? 'active' : ''}`}
              onClick={() => setActiveIndex(idx)}
            >
              {idx}
            </button>
          ))}
        </div>

        <div className="pt-view-tabs">
          {(['signals', 'positions', 'history'] as const).map(tab => (
            <button
              key={tab}
              className={`pt-view-tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => {
                setActiveTab(tab)
                if (tab === 'history') fetchHistory()
              }}
            >
              {tab === 'signals' ? '📊 Signals' : tab === 'positions' ? '📂 Positions' : '📋 History'}
              {tab === 'positions' && portfolio && portfolio.position_count > 0 && (
                <span className="pt-badge">{portfolio.position_count}</span>
              )}
            </button>
          ))}
        </div>

        {activeTab === 'signals' && (
          <button className="pt-scan-btn" onClick={fetchSignals}>
            🔍 Scan Signals
          </button>
        )}
      </div>

      {/* Content */}
      {activeTab === 'signals' && (
        <div className="pt-table-wrap">
          <table className="pt-table pt-signals-table">
            <thead>
              <tr>
                <th>Symbol</th><th>LTP</th><th>Score</th><th>Signal</th>
                <th>RSI</th><th>MACD</th><th>VWAP</th><th>ATR</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {symbols.map(sym => (
                <SignalRow
                  key={sym}
                  symbol={sym}
                  ltp={quotes[sym] ?? null}
                  signal={signals[sym] ?? null}
                  loading={!!signalLoading[sym]}
                  onBuy={(s, sig, ltp) => setBuyModal({ symbol: s, signal: sig, ltp })}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'positions' && (
        <OpenPositionsTable
          positions={portfolio?.open_positions ?? []}
          quotes={quotes}
          onExit={handleExit}
        />
      )}

      {activeTab === 'history' && (
        <TradeHistoryTable trades={trades} />
      )}
    </div>
  )
}
