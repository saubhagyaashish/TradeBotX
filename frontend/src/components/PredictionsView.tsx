// PredictionsView — accuracy dashboard: stats cards + predictions table

import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, TrendingUp, TrendingDown, Target, Clock } from 'lucide-react'
import type { Prediction, PredictionStats } from '../types'

const API = 'http://localhost:8000'

const RATING_CLASS: Record<string, string> = {
  BUY: 'badge-buy', OVERWEIGHT: 'badge-buy', 'STRONG BUY': 'badge-buy',
  HOLD: 'badge-hold',
  SELL: 'badge-sell', UNDERWEIGHT: 'badge-sell', 'STRONG SELL': 'badge-sell',
}

const RATING_FILTERS = ['All', 'BUY', 'OVERWEIGHT', 'HOLD', 'UNDERWEIGHT', 'SELL']

function fmtPrice(v: number | null): string {
  if (v == null) return '—'
  return `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
}

function fmtReturn(v: number | null): { text: string; cls: string } {
  if (v == null) return { text: '—', cls: '' }
  const sign = v >= 0 ? '+' : ''
  const cls = v >= 0 ? 'text-gain' : 'text-loss'
  return { text: `${sign}${v.toFixed(2)}%`, cls }
}

function fmtDate(s: string): string {
  try { return new Date(s).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' }) }
  catch { return s }
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({
  label, value, sub, icon, color,
}: {
  label: string
  value: string
  sub?: string
  icon: React.ReactNode
  color: 'blue' | 'green' | 'red' | 'amber'
}) {
  const colorMap = {
    blue:  { bg: 'var(--blue-dim)',   border: 'rgba(37,99,235,.25)',    text: 'var(--blue)' },
    green: { bg: 'var(--green-dim)',  border: 'rgba(34,197,94,.25)',    text: 'var(--green)' },
    red:   { bg: 'var(--red-dim)',    border: 'rgba(239,68,68,.25)',    text: 'var(--red)' },
    amber: { bg: 'var(--amber-dim)', border: 'rgba(245,158,11,.25)',   text: 'var(--amber)' },
  }
  const c = colorMap[color]
  return (
    <div className="pred-stat-card" style={{ background: c.bg, borderColor: c.border }}>
      <div className="pred-stat-icon" style={{ color: c.text }}>{icon}</div>
      <div className="pred-stat-value" style={{ color: c.text }}>{value}</div>
      <div className="pred-stat-label">{label}</div>
      {sub && <div className="pred-stat-sub">{sub}</div>}
    </div>
  )
}

// ── Main view ─────────────────────────────────────────────────────────────────

export default function PredictionsView() {
  const [stats, setStats] = useState<PredictionStats | null>(null)
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [total, setTotal] = useState(0)
  const [filter, setFilter] = useState('All')
  const [loading, setLoading] = useState(false)
  const [updating, setUpdating] = useState(false)
  const [updatedCount, setUpdatedCount] = useState<number | null>(null)

  const load = useCallback(async (selectedFilter = filter) => {
    setLoading(true)
    try {
      const ratingParam = selectedFilter !== 'All' ? `&rating=${selectedFilter}` : ''
      const [predsResp, statsResp] = await Promise.all([
        fetch(`${API}/api/predictions?limit=100${ratingParam}`),
        fetch(`${API}/api/predictions/stats`),
      ])
      const predsData = await predsResp.json()
      const statsData = await statsResp.json()
      setPredictions(predsData.predictions || [])
      setTotal(predsData.total || 0)
      setStats(statsData)
    } catch { /* backend offline */ }
    setLoading(false)
  }, [filter])

  useEffect(() => { load() }, [])  // eslint-disable-line

  const handleFilter = (f: string) => {
    setFilter(f)
    load(f)
  }

  const handleUpdateOutcomes = async () => {
    setUpdating(true)
    setUpdatedCount(null)
    try {
      const r = await fetch(`${API}/api/predictions/update-outcomes?days=3`, { method: 'POST' })
      const d = await r.json()
      setUpdatedCount(d.updated)
      await load()
    } catch { /* ignore */ }
    setUpdating(false)
  }

  const winRateColor = stats?.win_rate != null
    ? stats.win_rate >= 60 ? 'green' : stats.win_rate >= 40 ? 'amber' : 'red'
    : 'blue'

  const avgRetColor = stats?.avg_return != null
    ? stats.avg_return >= 0 ? 'green' : 'red'
    : 'blue'

  return (
    <>
      {/* Header */}
      <div className="page-header">
        <h1>Prediction <em>Accuracy</em></h1>
        <p>Track every AI decision against real price movement. Win = BUY↑ / SELL↓ / HOLD (neutral).</p>
      </div>

      {/* ── Stats Cards ─────────────────────────────────────────── */}
      {stats && (
        <div className="pred-stats-grid">
          <StatCard
            label="Total Predictions"
            value={String(stats.total)}
            sub={`${stats.pending} pending`}
            icon={<Target size={18} />}
            color="blue"
          />
          <StatCard
            label="Win Rate"
            value={stats.win_rate != null ? `${stats.win_rate}%` : '—'}
            sub={`${stats.settled} settled`}
            icon={<TrendingUp size={18} />}
            color={winRateColor}
          />
          <StatCard
            label="Avg Return"
            value={stats.avg_return != null ? `${stats.avg_return >= 0 ? '+' : ''}${stats.avg_return}%` : '—'}
            sub="on settled predictions"
            icon={stats.avg_return != null && stats.avg_return < 0 ? <TrendingDown size={18} /> : <TrendingUp size={18} />}
            color={avgRetColor}
          />
          <StatCard
            label="Pending Outcomes"
            value={String(stats.pending)}
            sub="≥3 days old → click Refresh"
            icon={<Clock size={18} />}
            color="amber"
          />
        </div>
      )}

      {/* ── Per-rating table ─────────────────────────────────────── */}
      {stats && Object.keys(stats.by_rating).length > 0 && (
        <div className="pred-rating-table-wrap">
          <table className="pred-rating-table">
            <thead>
              <tr>
                <th>Rating</th>
                <th>Predictions</th>
                <th>Win Rate</th>
                <th>Avg Return</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(stats.by_rating).map(([rating, rs]) => {
                const ret = rs.avg_return
                return (
                  <tr key={rating}>
                    <td>
                      <span className={`decision-pill ${RATING_CLASS[rating] ?? 'badge-hold'}`}>
                        {rating}
                      </span>
                    </td>
                    <td className="pred-rating-num">{rs.count}</td>
                    <td className="pred-rating-num">
                      {rs.win_rate != null ? `${rs.win_rate}%` : '—'}
                    </td>
                    <td className={`pred-rating-num ${ret != null ? (ret >= 0 ? 'text-gain' : 'text-loss') : ''}`}>
                      {ret != null ? `${ret >= 0 ? '+' : ''}${ret}%` : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Toolbar ──────────────────────────────────────────────── */}
      <div className="control-bar" style={{ marginTop: '1.5rem' }}>
        <div className="filter-pills">
          {RATING_FILTERS.map(f => (
            <button
              key={f}
              id={`pred-filter-${f.toLowerCase()}`}
              className={`filter-pill ${filter === f ? 'active' : ''}`}
              onClick={() => handleFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', marginLeft: 'auto', alignItems: 'center' }}>
          {updatedCount != null && (
            <span className="pred-updated-msg">
              ✓ {updatedCount} outcome{updatedCount !== 1 ? 's' : ''} updated
            </span>
          )}
          <button
            id="btn-update-outcomes"
            className="btn-ghost"
            style={{ height: 32, gap: '0.35rem' }}
            onClick={handleUpdateOutcomes}
            disabled={updating}
            title="Fetch current prices and compute returns for settled predictions (≥3 days old)"
          >
            {updating
              ? <><RefreshCw size={13} className="spin" /> Checking…</>
              : <><RefreshCw size={13} /> Refresh Outcomes</>
            }
          </button>
          <button
            id="btn-refresh-preds"
            className="btn-icon"
            onClick={() => load()}
            disabled={loading}
            title="Refresh"
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      {/* ── Predictions table ─────────────────────────────────────── */}
      {predictions.length > 0 ? (
        <div className="pred-table-wrap">
          <table className="pred-table">
            <thead>
              <tr>
                <th className="th-left">Ticker</th>
                <th className="th-left">Date</th>
                <th>Rating</th>
                <th>Price at Call</th>
                <th>Current Price</th>
                <th>Return</th>
                <th>Outcome</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map(p => {
                const ret = fmtReturn(p.return_pct)
                return (
                  <tr key={p.id} className="pred-row">
                    <td><span className="symbol-badge">{p.ticker}</span></td>
                    <td className="td-right" style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      {fmtDate(p.trade_date)}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span className={`decision-pill ${RATING_CLASS[p.rating] ?? 'badge-hold'}`}>
                        {p.rating}
                      </span>
                    </td>
                    <td className="td-right">{fmtPrice(p.price_at_prediction)}</td>
                    <td className="td-right">{fmtPrice(p.current_price)}</td>
                    <td className={`td-right ${ret.cls}`}>{ret.text}</td>
                    <td style={{ textAlign: 'center' }}>
                      {p.outcome_checked_at == null
                        ? <span className="pred-outcome-pending">Pending</span>
                        : p.is_win === 1
                          ? <span className="pred-outcome-win">✓ Win</span>
                          : <span className="pred-outcome-loss">✗ Loss</span>
                      }
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <div className="pred-table-footer">
            Showing {predictions.length} of {total} predictions
          </div>
        </div>
      ) : !loading && (
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <p>
            {filter !== 'All'
              ? <>No <strong>{filter}</strong> predictions. Try a different filter.</>
              : <>No predictions yet. Run an analysis from the <strong>Screener</strong> or <strong>Watchlist</strong> tab — each result is automatically tracked here.</>
            }
          </p>
        </div>
      )}
    </>
  )
}
