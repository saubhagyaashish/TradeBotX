// ReportAccordion — expandable per-agent report sections

import { ChevronDown } from 'lucide-react'
import { REPORT_LABELS } from '../types'

interface ReportAccordionProps {
  reports: Record<string, string>
  openReports: Set<string>
  onToggle: (key: string) => void
}

export default function ReportAccordion({ reports, openReports, onToggle }: ReportAccordionProps) {
  const entries = Object.entries(reports).filter(([, v]) => v && v.trim().length > 0)

  if (entries.length === 0) return null

  return (
    <div className="reports-stack">
      {entries.map(([key, value]) => {
        const isOpen = openReports.has(key)
        return (
          <div className="report-card" key={key}>
            <div
              className="report-trigger"
              onClick={() => onToggle(key)}
              id={`report-toggle-${key.replace(/\s+/g, '-').toLowerCase()}`}
            >
              <div className="report-trigger-left">
                <span className="report-dot" />
                <span className="report-title">{REPORT_LABELS[key] || key}</span>
              </div>
              <ChevronDown
                size={16}
                className={`report-chevron ${isOpen ? 'open' : ''}`}
              />
            </div>
            {isOpen && <div className="report-body">{value}</div>}
          </div>
        )
      })}
    </div>
  )
}
