// ResultsView — table of past AI analysis results with expandable reports

import { useState, useEffect } from 'react'
import { RefreshCw, ChevronDown } from 'lucide-react'
import type { ResultEntry } from '../types'
import ReportAccordion from './ReportAccordion'

const API = 'http://localhost:8000'

const RATING_CLASS: Record<string, string> = {
  BUY: 'badge-buy',
  OVERWEIGHT: 'badge-buy',
  HOLD: 'badge-hold',
  UNDERWEIGHT: 'badge-sell',
  SELL: 'badge-sell',
}

const FILTERS = ['All', 'BUY', 'OVERWEIGHT', 'HOLD', 'UNDERWEIGHT', 'SELL']

export default function ResultsView() {
  const [results, setResults] = useState<ResultEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('All')
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const [openReports, setOpenReports] = useState<Set<string>>(new Set())

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const resp = await fetch(`${API}/api/results`)
      const data = await resp.json()
      if (data.error) setError(data.error)
      else setResults(data.results || [])
    } catch {
      setError('Failed to reach backend. Is api_server.py running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = filter === 'All'
    ? results
    : results.filter(r => r.rating === filter)

  const toggleRow = (key: string) => {
    setExpandedRow(prev => prev === key ? null : key)
    setOpenReports(new Set())
  }

  const toggleReport = (key: string) => {
    setOpenReports(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  return (
    <>
      <div className="page-header">
        <h1>Analysis <em>History</em></h1>
        <p>All past AI pipeline results — sorted newest first. Click any row to expand agent reports.</p>
      </div>

      {/* Toolbar */}
      <div className="control-bar">
        <div className="filter-pills">
          {FILTERS.map(f => (
            <button
              key={f}
              id={`filter-${f.toLowerCase()}`}
              className={`filter-pill ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <button
          id="btn-refresh-results"
          className="btn-icon"
          onClick={load}
          disabled={loading}
          title="Refresh"
        >
          <RefreshCw size={15} className={loading ? 'spin' : ''} />
        </button>
      </div>

      {error && <div className="error-box" role="alert">⚠ {error}</div>}

      {/* Results table */}
      {!loading && filtered.length > 0 && (
        <div className="results-table-wrap">
          <table className="results-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Date</th>
                <th>Rating</th>
                <th>Key Action</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => {
                const key = `${r.ticker}-${r.date}`
                const isOpen = expandedRow === key
                // one-liner from portfolio manager report
                const pm = r.reports?.['Portfolio Manager'] ?? ''
                const keyAction = pm.slice(0, 120).replace(/\n/g, ' ') + (pm.length > 120 ? '…' : '')
                return (
                  <>
                    <tr
                      key={key}
                      className={`results-row ${isOpen ? 'expanded' : ''}`}
                      onClick={() => toggleRow(key)}
                    >
                      <td className="col-ticker">{r.ticker}</td>
                      <td className="col-date">{r.date}</td>
                      <td>
                        <span className={`decision-pill ${RATING_CLASS[r.rating] ?? 'badge-hold'}`}>
                          {r.rating}
                        </span>
                      </td>
                      <td className="col-action">{keyAction || '—'}</td>
                      <td className="col-chevron">
                        <ChevronDown size={14} className={`report-chevron ${isOpen ? 'open' : ''}`} />
                      </td>
                    </tr>
                    {isOpen && (
                      <tr key={`${key}-detail`} className="results-detail-row">
                        <td colSpan={5}>
                          <ReportAccordion
                            reports={r.reports}
                            openReports={openReports}
                            onToggle={toggleReport}
                          />
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && filtered.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <p>
            {filter === 'All'
              ? <>No past results yet. Run an analysis from the <strong>Screener</strong> tab to see results here.</>
              : <>No <strong>{filter}</strong> results found. Try a different filter.</>
            }
          </p>
        </div>
      )}
    </>
  )
}
