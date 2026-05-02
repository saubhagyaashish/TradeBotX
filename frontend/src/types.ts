// types.ts — shared TypeScript interfaces

export interface Stock {
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

export interface ScreenResult {
  index_name: string
  last_updated: string
  stocks: Stock[]
  flagged: Stock[]
  flagged_count: number
  total_count: number
}

export interface AnalysisResult {
  decision: string
  reports: Record<string, string>
}

export type View = 'screener' | 'analysis' | 'results' | 'watchlist' | 'predictions' | 'paper'

export interface Prediction {
  id: number
  ticker: string
  trade_date: string
  decision: string
  rating: string
  price_at_prediction: number | null
  current_price: number | null
  return_pct: number | null
  is_win: number | null        // 1 = win, 0 = loss, null = pending
  outcome_checked_at: string | null
  created_at: string
}

export interface RatingStats {
  count: number
  wins: number
  win_rate: number | null
  avg_return: number | null
}

export interface PredictionStats {
  total: number
  settled: number
  pending: number
  win_rate: number | null
  avg_return: number | null
  by_rating: Record<string, RatingStats>
}


export interface CustomWatchlist {
  tickers: string[]
}

export type TickerStatus = 'queued' | 'running' | 'done' | 'error'

export interface BatchTickerState {
  ticker: string
  status: TickerStatus
  currentAgent?: string
  rating?: string
  decision?: string
  error?: string
}

export interface BatchState {
  running: boolean
  done: boolean
  total: number
  items: BatchTickerState[]
}

export interface ResultEntry {
  ticker: string
  date: string
  decision: string
  rating: string
  reports: Record<string, string>
}

export const PIPELINE = [
  'Market Analyst',
  'Social Media Analyst',
  'News Analyst',
  'Fundamentals Analyst',
  'India Macro Analyst',
  'Bull Researcher',
  'Bear Researcher',
  'Research Manager',
  'Trader',
  'Aggressive Analyst',
  'Conservative Analyst',
  'Neutral Analyst',
  'Portfolio Manager',
] as const

export const REPORT_LABELS: Record<string, string> = {
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
// ── Paper Trading Types ──────────────────────────────────────────────────

export interface SignalData {
  score: number
  trend: string
  recommendation: string
  signals: {
    rsi: number
    rsi_signal: string
    macd_bullish: boolean
    macd_histogram: number
    above_ema_20: boolean
    above_ema_50: boolean
    ema_20: number
    ema_50: number
    above_vwap: boolean
    vwap: number
    bollinger_position: number
    stochastic_k: number
    volume_surge: boolean
    atr: number
    close: number
  }
  component_scores: Record<string, number>
}

export interface LiveQuote {
  symbol: string
  ltp: number
}

export interface PaperPosition {
  symbol: string
  quantity: number
  entry_price: number
  entry_time: string
  stop_loss: number
  target_price: number
  trailing_stop: number | null
  strategy: string
}

export interface PaperPortfolio {
  capital: number
  initial_capital: number
  total_pnl: number
  total_pnl_pct: number
  daily_pnl: number
  open_positions: PaperPosition[]
  position_count: number
  daily_trades: number
  daily_wins: number
  daily_losses: number
  total_trades: number
  total_wins: number
  total_win_rate: number | null
  daily_loss_limit_active: boolean
}
