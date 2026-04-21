// ScreenerView — index selector, scan controls, and results table

import { Search, Loader2 } from 'lucide-react'
import StockTable from './StockTable'
import type { ScreenResult, Stock } from '../types'

interface ScreenerViewProps {
  indices: string[]
  selectedIndex: string
  onIndexChange: (idx: string) => void
  onScan: () => void
  isLoading: boolean
  screenData: ScreenResult | null
  screenError: string
  showFlaggedOnly: boolean
  onToggleFlagged: () => void
  onAnalyse: (stock: Stock) => void
}

export default function ScreenerView({
  indices,
  selectedIndex,
  onIndexChange,
  onScan,
  isLoading,
  screenData,
  screenError,
  showFlaggedOnly,
  onToggleFlagged,
  onAnalyse,
}: ScreenerViewProps) {
  return (
    <>
      <div className="page-header">
        <h1>NSE <em>Market Scanner</em></h1>
        <p>Select an index, scan live stock data, and launch AI deep analysis on flagged stocks.</p>
      </div>

      {/* Controls */}
      <div className="control-bar">
        <div className="field">
          <label className="field-label" htmlFor="index-select">Index</label>
          <select
            id="index-select"
            className="select-input"
            value={selectedIndex}
            onChange={(e) => onIndexChange(e.target.value)}
          >
            {indices.length > 0
              ? indices.map((idx) => <option key={idx} value={idx}>{idx}</option>)
              : <option value="NIFTY 50">NIFTY 50</option>
            }
          </select>
        </div>

        <button
          id="btn-scan-market"
          className="btn-primary"
          onClick={onScan}
          disabled={isLoading}
        >
          {isLoading
            ? <><Loader2 size={15} className="spin" /> Scanning…</>
            : <><Search size={15} /> Scan Market</>
          }
        </button>
      </div>

      {/* Error */}
      {screenError && (
        <div className="error-box" role="alert">
          ⚠ {screenError}
        </div>
      )}

      {/* Results table */}
      {screenData && (
        <StockTable
          stocks={screenData.stocks}
          showFlaggedOnly={showFlaggedOnly}
          onToggleFlagged={onToggleFlagged}
          totalCount={screenData.total_count}
          flaggedCount={screenData.flagged_count}
          lastUpdated={screenData.last_updated}
          onAnalyse={onAnalyse}
        />
      )}

      {/* Empty state */}
      {!isLoading && !screenData && !screenError && (
        <div className="empty-state">
          <div className="empty-icon">📡</div>
          <p>
            Select an index above and click <strong>Scan Market</strong> to screen live NSE stocks.
            <br />Flagged stocks are pre-filtered by RSI, volume spikes, and price action.
          </p>
        </div>
      )}
    </>
  )
}
