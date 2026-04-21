// AnalysisView — live agent pipeline + decision + reports for a single stock

import { ArrowLeft, Loader2 } from 'lucide-react'
import AgentPipeline from './AgentPipeline'
import DecisionBadge from './DecisionBadge'
import ReportAccordion from './ReportAccordion'
import type { Stock, AnalysisResult } from '../types'

interface AnalysisViewProps {
  stock: Stock
  isLoading: boolean
  completedAgents: Set<string>
  result: AnalysisResult | null
  error: string
  openReports: Set<string>
  onToggleReport: (key: string) => void
  onBack: () => void
}

const fmt = (n: number, d = 2) => n?.toLocaleString('en-IN', { maximumFractionDigits: d }) ?? '—'

export default function AnalysisView({
  stock,
  isLoading,
  completedAgents,
  result,
  error,
  openReports,
  onToggleReport,
  onBack,
}: AnalysisViewProps) {
  const today = new Date().toISOString().split('T')[0]

  return (
    <>
      {/* Back navigation */}
      <button id="btn-back-screener" className="btn-back" onClick={onBack}>
        <ArrowLeft size={16} /> Back to Screener
      </button>

      {/* Stock summary header */}
      <div className="analysis-header">
        <div>
          <div className="analysis-ticker-badge">
            {stock.symbol}<span>.NS</span>
          </div>
          <div className="analysis-company">{stock.name}</div>
        </div>
        <div className="analysis-ltp">
          <div className="analysis-price">₹{fmt(stock.ltp)}</div>
          <div className={`analysis-change ${stock.change >= 0 ? 'text-gain' : 'text-loss'}`}>
            {stock.change >= 0 ? '▲' : '▼'} {Math.abs(stock.change).toFixed(2)} ({stock.pct_change >= 0 ? '+' : ''}{stock.pct_change?.toFixed(2)}%)
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="error-box" role="alert">
          ⚠ {error}
        </div>
      )}

      {/* Pipeline stepper — show while running OR after completion */}
      {(isLoading || result) && (
        <AgentPipeline completedAgents={completedAgents} isRunning={isLoading} />
      )}

      {/* Initialising spinner (before first progress event) */}
      {isLoading && !result && !error && completedAgents.size === 0 && (
        <div className="empty-state">
          <Loader2 size={28} className="spin" style={{ marginBottom: '1rem', color: 'var(--blue)' }} />
          <p>Initialising the 13-agent pipeline…</p>
        </div>
      )}

      {/* Decision badge */}
      {result && (
        <DecisionBadge decision={result.decision} ticker={stock.ticker} date={today} />
      )}

      {/* Agent reports accordion */}
      {result?.reports && (
        <ReportAccordion
          reports={result.reports}
          openReports={openReports}
          onToggle={onToggleReport}
        />
      )}
    </>
  )
}
