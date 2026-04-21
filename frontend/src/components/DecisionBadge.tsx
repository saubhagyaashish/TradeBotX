// DecisionBadge — final trade decision display card

interface DecisionBadgeProps {
  decision: string
  ticker: string
  date: string
}

export default function DecisionBadge({ decision, ticker, date }: DecisionBadgeProps) {
  return (
    <div className="decision-card">
      <div className="decision-eyebrow">Final Decision</div>
      <div className={`decision-pill ${decision}`}>{decision}</div>
      <div className="decision-meta">
        {ticker} · {date}
      </div>
    </div>
  )
}
