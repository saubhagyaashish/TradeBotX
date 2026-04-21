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

export type View = 'screener' | 'analysis' | 'results' | 'watchlist'

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
