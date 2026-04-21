// App.tsx — root component: state management and view routing only

import { useState, useRef, useCallback, useEffect } from 'react'
import './index.css'

import TopNav from './components/TopNav'
import ScreenerView from './components/ScreenerView'
import AnalysisView from './components/AnalysisView'
import ResultsView from './components/ResultsView'
import WatchlistPanel from './components/WatchlistPanel'
import PredictionsView from './components/PredictionsView'
import type { Stock, ScreenResult, AnalysisResult, View } from './types'

const API = 'http://localhost:8000'

export default function App() {
  // ── View ─────────────────────────────────────────────────────────
  const [view, setView] = useState<View>('screener')

  // ── Screener ──────────────────────────────────────────────────────
  const [indices, setIndices] = useState<string[]>([])
  const [selectedIndex, setSelectedIndex] = useState('NIFTY 50')
  const [screenData, setScreenData] = useState<ScreenResult | null>(null)
  const [screenLoading, setScreenLoading] = useState(false)
  const [showFlaggedOnly, setShowFlaggedOnly] = useState(false)
  const [screenError, setScreenError] = useState('')

  // ── Analysis ──────────────────────────────────────────────────────
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [completedAgents, setCompletedAgents] = useState<Set<string>>(new Set())
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [analysisError, setAnalysisError] = useState('')
  const [openReports, setOpenReports] = useState<Set<string>>(new Set())
  const eventSourceRef = useRef<EventSource | null>(null)

  // ── Fetch indices on mount ────────────────────────────────────────
  useEffect(() => {
    fetch(`${API}/api/indices`)
      .then((r) => r.json())
      .then((d) => setIndices(d.indices || []))
      .catch(() => { /* backend not running yet — silently ignore */ })
  }, [])

  // ── Scan market ───────────────────────────────────────────────────
  const handleScreen = useCallback(async () => {
    setScreenLoading(true)
    setScreenError('')
    try {
      const resp = await fetch(`${API}/api/screen?index=${encodeURIComponent(selectedIndex)}`)
      const data = await resp.json()
      if (data.error) {
        setScreenError(data.error)
      } else {
        setScreenData(data)
      }
    } catch {
      setScreenError('Failed to connect to backend. Is api_server.py running?')
    } finally {
      setScreenLoading(false)
    }
  }, [selectedIndex])

  // ── Start deep analysis via SSE ───────────────────────────────────
  const handleAnalyse = useCallback((stock: Stock) => {
    setSelectedStock(stock)
    setView('analysis')
    setAnalysisLoading(true)
    setAnalysisError('')
    setAnalysisResult(null)
    setCompletedAgents(new Set())
    setOpenReports(new Set())

    eventSourceRef.current?.close()

    const today = new Date().toISOString().split('T')[0]
    const url = `${API}/api/analyze/stream?ticker=${encodeURIComponent(stock.ticker)}&date=${encodeURIComponent(today)}`
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
      } catch { /* ignore malformed frames */ }
    }

    es.onerror = () => {
      setAnalysisError('Connection lost. Make sure api_server.py is running.')
      setAnalysisLoading(false)
      es.close()
    }
  }, [])

  // ── Report accordion toggle ───────────────────────────────────────
  const toggleReport = useCallback((key: string) => {
    setOpenReports((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }, [])

  // ── Back to screener ──────────────────────────────────────────────
  const handleBack = useCallback(() => {
    eventSourceRef.current?.close()
    setView('screener')
  }, [])

  // ── Nav link clicks ────────────────────────────────────────────────
  const handleNav = useCallback((v: 'screener' | 'results' | 'watchlist' | 'predictions') => {
    eventSourceRef.current?.close()
    setView(v)
  }, [])

  // ── Render ────────────────────────────────────────────────────────
  return (
    <div className="app">
      <TopNav view={view} onNav={handleNav} />

      {view === 'results' ? (
        <ResultsView />
      ) : view === 'watchlist' ? (
        <WatchlistPanel />
      ) : view === 'predictions' ? (
        <PredictionsView />
      ) : view === 'screener' ? (
        <ScreenerView
          indices={indices}
          selectedIndex={selectedIndex}
          onIndexChange={setSelectedIndex}
          onScan={handleScreen}
          isLoading={screenLoading}
          screenData={screenData}
          screenError={screenError}
          showFlaggedOnly={showFlaggedOnly}
          onToggleFlagged={() => setShowFlaggedOnly((v) => !v)}
          onAnalyse={handleAnalyse}
        />
      ) : selectedStock ? (
        <AnalysisView
          stock={selectedStock}
          isLoading={analysisLoading}
          completedAgents={completedAgents}
          result={analysisResult}
          error={analysisError}
          openReports={openReports}
          onToggleReport={toggleReport}
          onBack={handleBack}
        />
      ) : null}
    </div>
  )
}
