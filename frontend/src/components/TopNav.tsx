// TopNav — site-wide navigation bar

import type { View } from '../types'

interface TopNavProps {
  view: View
  onNav: (v: 'screener' | 'results') => void
}

export default function TopNav({ view, onNav }: TopNavProps) {
  return (
    <nav className="topnav">
      <div className="topnav-brand">
        <div className="brand-icon">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="8" width="3" height="10" rx="1" />
            <rect x="5" y="5" width="1" height="3" />
            <rect x="5" y="18" width="1" height="2" />
            <rect x="10.5" y="4" width="3" height="10" rx="1" />
            <rect x="12" y="2" width="1" height="2" />
            <rect x="12" y="14" width="1" height="3" />
            <rect x="17" y="9" width="3" height="8" rx="1" />
            <rect x="18.5" y="7" width="1" height="2" />
            <rect x="18.5" y="17" width="1" height="2" />
          </svg>
        </div>
        <span className="brand-name">Trade<span>BotX</span></span>
      </div>

      <div className="topnav-links">
        <button
          id="nav-screener"
          className={`nav-link ${view === 'screener' || view === 'analysis' ? 'active' : ''}`}
          onClick={() => onNav('screener')}
        >
          Screener
        </button>
        <button
          id="nav-results"
          className={`nav-link ${view === 'results' ? 'active' : ''}`}
          onClick={() => onNav('results')}
        >
          Results
        </button>
      </div>
    </nav>
  )
}
