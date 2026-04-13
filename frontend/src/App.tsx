import { useState, useRef, useCallback, useEffect } from 'react'
import { ChevronDown, Loader2, ArrowRight, ArrowLeft, Search, Filter, AlertTriangle } from 'lucide-react'
import './index.css'

// ── Agent pipeline phases ──────────────────────────────────────────────
const PIPELINE = [
  'Market Analyst', 'Social Media Analyst', 'News Analyst',
  'Fundamentals Analyst', 'India Macro Analyst',
  'Bull Researcher', 'Bear Researcher', 'Research Manager', 'Trader',
  'Aggressive Analyst', 'Conservative Analyst', 'Neutral Analyst',
  'Portfolio Manager',
]

const REPORT_LABELS: Record<string, string> = {
  'Market Analyst': 'Market Analysis',
  'Social Media Analyst': 'Social Sentiment',
  'News Analyst': 'News Analysis',
  'Fundamentals Analyst': 'Fundamental Analysis',
  'India Macro Analyst': 'India Macro Analysis',
  'Bull Researcher': 'Bull Case',
  'Bear Researcher': 'Bear Case',
  'Research Manager': 'Research Summary',
  'Trader': 'Trader Plan',
  'Aggressive Analyst': 'Aggressive Risk View',
  'Conservative Analyst': 'Conservative Risk View',
  'Neutral Analyst': 'Neutral Risk View',
  'Portfolio Manager': 'Final Rationale',
}

// ── Types ──────────────────────────────────────────────────────────────
interface Stock {
  symbol: string
  name: string
  ltp: number
  change: number
  pct_change: number
  open: number
  high: number
  low: number
  volume: number
  year_high: number
  year_low: number
  ticker: string
  flagged?: boolean
  flag_reasons?: string[]
}

interface ScreenResult {
  index_name: string
  last_updated: string
  stocks: Stock[]
  flagged: Stock[]
  flagged_count: number
  total_count: number
}

interface AnalysisResult {
  decision: string
  reports: Record<string, string>
}

type View = 'screener' | 'analysis'

// ── App ────────────────────────────────────────────────────────────────
export default function App() {
  // View state
  const [view, setView] = useState<View>('screener')

  // Screener state
  const [indices, setIndices] = useState<string[]>([])
  const [selectedIndex, setSelectedIndex] = useState('NIFTY 50')
  const [screenData, setScreenData] = useState<ScreenResult | null>(null)
  const [screenLoading, setScreenLoading] = useState(false)
  const [showFlaggedOnly, setShowFlaggedOnly] = useState(false)
  const [screenError, setScreenError] = useState('')

  // Analysis state
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [completedAgents, setCompletedAgents] = useState<Set<string>>(new Set())
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [analysisError, setAnalysisError] = useState('')
  const [openReports, setOpenReports] = useState<Set<string>>(new Set())
  const eventSourceRef = useRef<EventSource | null>(null)

  // Fetch available indices on mount
  useEffect(() => {
    fetch('http://localhost:8000/api/indices')
      .then((r) => r.json())
      .then((d) => setIndices(d.indices || []))
      .catch(() => {})
  }, [])

  // ── Screen stocks ─────────────────────────────────────────────────
  const handleScreen = useCallback(async () => {
    setScreenLoading(true)
    setScreenError('')
    try {
      const resp = await fetch(
        `http://localhost:8000/api/screen?index=${encodeURIComponent(selectedIndex)}`
      )
      const data = await resp.json()
      if (data.error) {
        setScreenError(data.error)
      } else {
        setScreenData(data)
      }
    } catch {
      setScreenError('Failed to connect to backend. Is the server running?')
    } finally {
      setScreenLoading(false)
    }
  }, [selectedIndex])

  // ── Analyse a single stock ────────────────────────────────────────
  const handleAnalyse = useCallback(
    (stock: Stock) => {
      setSelectedStock(stock)
      setView('analysis')
      setAnalysisLoading(true)
      setAnalysisError('')
      setAnalysisResult(null)
      setCompletedAgents(new Set())
      setOpenReports(new Set())

      if (eventSourceRef.current) eventSourceRef.current.close()

      const today = new Date().toISOString().split('T')[0]
      const url = `http://localhost:8000/api/analyze/stream?ticker=${encodeURIComponent(stock.ticker)}&date=${encodeURIComponent(today)}`
      const es = new EventSource(url)
      eventSourceRef.current = es

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'progress') {
            setCompletedAgents((prev) => new Set([...prev, data.agent]))
          } else if (data.type === 'result') {
            setAnalysisResult({ decision: data.decision, reports: data.reports })
            setAnalysisLoading(false)
            es.close()
          } else if (data.type === 'error') {
            setAnalysisError(data.message)
            setAnalysisLoading(false)
            es.close()
          }
        } catch { /* ignore */ }
      }

      es.onerror = () => {
        setAnalysisError('Connection lost. Make sure the backend is running.')
        setAnalysisLoading(false)
        es.close()
      }
    },
    []
  )

  const toggleReport = (key: string) => {
    setOpenReports((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const currentStep = PIPELINE.find((p) => !completedAgents.has(p))

  // ── Render: Screener View ─────────────────────────────────────────
  if (view === 'screener') {
    const stocks = screenData?.stocks || []
    const displayStocks = showFlaggedOnly ? stocks.filter((s) => s.flagged) : stocks

    return (
      <div className="app">
        <header className="header">
          <h1>TradingAgents <span>AI</span></h1>
          <p>Live NSE screener · Multi-agent AI analysis</p>
        </header>

        {/* Index selector + Scan button */}
        <div className="input-bar">
          <div className="field">
            <label>Index</label>
            <select
              value={selectedIndex}
              onChange={(e) => setSelectedIndex(e.target.value)}
              className="select-input"
            >
              {indices.length > 0
                ? indices.map((idx) => (
                    <option key={idx} value={idx}>{idx}</option>
                  ))
                : <option value="NIFTY 50">NIFTY 50</option>
              }
            </select>
          </div>
          <button className="btn-analyse" onClick={handleScreen} disabled={screenLoading}>
            {screenLoading ? (
              <><Loader2 size={16} className="spin-icon" /> Scanning…</>
            ) : (
              <><Search size={16} /> Scan Market</>
            )}
          </button>
        </div>

        {screenError && <div className="error-box">{screenError}</div>}

        {screenData && (
          <>
            {/* Stats bar */}
            <div className="stats-bar">
              <span>{screenData.total_count} stocks</span>
              <span className="stat-sep">·</span>
              <span className="stat-flagged">
                <AlertTriangle size={14} />
                {screenData.flagged_count} flagged
              </span>
              <span className="stat-sep">·</span>
              <span className="stat-time">Updated: {screenData.last_updated || 'Just now'}</span>
              <button
                className={`btn-filter ${showFlaggedOnly ? 'active' : ''}`}
                onClick={() => setShowFlaggedOnly(!showFlaggedOnly)}
              >
                <Filter size={14} />
                {showFlaggedOnly ? 'Show All' : 'Flagged Only'}
              </button>
            </div>

            {/* Stock table */}
            <div className="table-wrap">
              <table className="stock-table">
                <thead>
                  <tr>
                    <th className="th-left">Symbol</th>
                    <th>LTP</th>
                    <th>Change</th>
                    <th>% Chg</th>
                    <th>Volume</th>
                    <th>52W H</th>
                    <th>52W L</th>
                    <th>Signal</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {displayStocks.map((stock) => (
                    <tr
                      key={stock.symbol}
                      className={`stock-row ${stock.flagged ? 'row-flagged' : ''}`}
                    >
                      <td className="td-symbol">
                        <span className="symbol-name">{stock.symbol}</span>
                      </td>
                      <td className="td-num">₹{stock.ltp?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                      <td className={`td-num ${stock.change >= 0 ? 'txt-green' : 'txt-red'}`}>
                        {stock.change >= 0 ? '+' : ''}{stock.change?.toFixed(2)}
                      </td>
                      <td className={`td-num ${stock.pct_change >= 0 ? 'txt-green' : 'txt-red'}`}>
                        {stock.pct_change >= 0 ? '+' : ''}{stock.pct_change?.toFixed(2)}%
                      </td>
                      <td className="td-num">{(stock.volume / 100000).toFixed(1)}L</td>
                      <td className="td-num">₹{stock.year_high?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                      <td className="td-num">₹{stock.year_low?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                      <td className="td-flags">
                        {stock.flag_reasons?.map((r, i) => (
                          <span key={i} className="flag-tag">{r}</span>
                        ))}
                      </td>
                      <td>
                        <button className="btn-go" onClick={() => handleAnalyse(stock)}>
                          Analyse <ArrowRight size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {!screenLoading && !screenData && !screenError && (
          <div className="empty">
            <p>Select an index and click <strong>Scan Market</strong> to view live stocks.</p>
          </div>
        )}
      </div>
    )
  }

  // ── Render: Analysis View ─────────────────────────────────────────
  return (
    <div className="app">
      <header className="header">
        <button className="btn-back" onClick={() => { setView('screener'); eventSourceRef.current?.close() }}>
          <ArrowLeft size={18} /> Back to Screener
        </button>
        <h1>
          {selectedStock?.symbol} <span>.NS</span>
        </h1>
        <p>{selectedStock?.name} · ₹{selectedStock?.ltp?.toLocaleString('en-IN')}</p>
      </header>

      {analysisError && <div className="error-box">{analysisError}</div>}

      {/* Progress Stepper */}
      {(analysisLoading || analysisResult) && (
        <div className="stepper">
          <div className="stepper-title">Agent Pipeline</div>
          <div className="stepper-grid">
            {PIPELINE.map((name) => {
              const done = completedAgents.has(name)
              const active = !done && name === currentStep && analysisLoading
              return (
                <div key={name} className={`step ${done ? 'done' : ''} ${active ? 'active' : ''}`}>
                  <span className="step-dot" />
                  {name}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Decision Badge */}
      {analysisResult && (
        <div className="decision-section">
          <div className="decision-label">Final Decision</div>
          <div className={`decision-badge decision-${analysisResult.decision}`}>
            {analysisResult.decision}
          </div>
          <div className="decision-ticker">
            {selectedStock?.ticker} · {new Date().toISOString().split('T')[0]}
          </div>
        </div>
      )}

      {/* Report Accordion */}
      {analysisResult?.reports && (
        <div className="reports">
          {Object.entries(analysisResult.reports)
            .filter(([, value]) => value && value.trim().length > 0)
            .map(([key, value]) => {
              const isOpen = openReports.has(key)
              return (
                <div className="report" key={key}>
                  <div className="report-header" onClick={() => toggleReport(key)}>
                    <h3>{REPORT_LABELS[key] || key}</h3>
                    <span className={`report-toggle ${isOpen ? 'open' : ''}`}>
                      <ChevronDown size={16} />
                    </span>
                  </div>
                  {isOpen && <div className="report-body">{value}</div>}
                </div>
              )
            })}
        </div>
      )}

      {analysisLoading && !analysisResult && !analysisError && completedAgents.size === 0 && (
        <div className="empty">
          <Loader2 size={24} className="spin-icon" style={{ marginBottom: '1rem' }} />
          <p>Initialising agent pipeline…</p>
        </div>
      )}
    </div>
  )
}
