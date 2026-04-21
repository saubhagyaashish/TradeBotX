// StockTable — screener results table component

import { ArrowRight, AlertTriangle } from 'lucide-react'
import type { Stock } from '../types'

interface StockTableProps {
  stocks: Stock[]
  showFlaggedOnly: boolean
  onToggleFlagged: () => void
  totalCount: number
  flaggedCount: number
  lastUpdated: string
  onAnalyse: (stock: Stock) => void
}

const fmt = (n: number, decimals = 2) =>
  n?.toLocaleString('en-IN', { maximumFractionDigits: decimals }) ?? '—'

export default function StockTable({
  stocks,
  showFlaggedOnly,
  onToggleFlagged,
  totalCount,
  flaggedCount,
  lastUpdated,
  onAnalyse,
}: StockTableProps) {
  const display = showFlaggedOnly ? stocks.filter((s) => s.flagged) : stocks

  return (
    <>
      {/* Stats row */}
      <div className="stats-row">
        <span>{totalCount} stocks scanned</span>
        <span className="stat-sep">·</span>
        <span className="stat-flagged">
          <AlertTriangle size={13} />
          {flaggedCount} flagged
        </span>
        <span className="stat-sep">·</span>
        <span className="stat-time">{lastUpdated || 'just now'}</span>

        <button
          id="btn-toggle-flagged"
          className={`btn-ghost ${showFlaggedOnly ? 'active' : ''}`}
          style={{ marginLeft: 'auto' }}
          onClick={onToggleFlagged}
        >
          {showFlaggedOnly ? 'Show All' : 'Flagged Only'}
        </button>
      </div>

      {/* Table */}
      <div className="table-wrap">
        <table className="stock-table">
          <thead>
            <tr>
              <th className="th-left">Symbol</th>
              <th>LTP (₹)</th>
              <th>Change</th>
              <th>% Chg</th>
              <th>Volume</th>
              <th>52W H</th>
              <th>52W L</th>
              <th>Signals</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {display.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-dim)' }}>
                  No stocks match the current filter.
                </td>
              </tr>
            ) : (
              display.map((stock) => (
                <tr
                  key={stock.symbol}
                  className={`stock-row ${stock.flagged ? 'row-flagged' : ''}`}
                >
                  <td className="td-left">
                    <span className="symbol-badge">{stock.symbol}</span>
                  </td>
                  <td className="td-right">₹{fmt(stock.ltp)}</td>
                  <td className={`td-right ${stock.change >= 0 ? 'text-gain' : 'text-loss'}`}>
                    {stock.change >= 0 ? '+' : ''}{fmt(stock.change)}
                  </td>
                  <td className={`td-right ${stock.pct_change >= 0 ? 'text-gain' : 'text-loss'}`}>
                    {stock.pct_change >= 0 ? '+' : ''}{fmt(stock.pct_change)}%
                  </td>
                  <td className="td-right">{(stock.volume / 100_000).toFixed(1)}L</td>
                  <td className="td-right">₹{fmt(stock.year_high, 0)}</td>
                  <td className="td-right">₹{fmt(stock.year_low, 0)}</td>
                  <td>
                    {stock.flag_reasons?.map((r, i) => (
                      <span key={i} className="flag-chip">{r}</span>
                    ))}
                  </td>
                  <td>
                    <button
                      id={`btn-analyse-${stock.symbol}`}
                      className="btn-analyse"
                      onClick={() => onAnalyse(stock)}
                    >
                      Analyse <ArrowRight size={13} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}
