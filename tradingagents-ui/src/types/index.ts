export interface AnalystInsight {
  name: string
  signal: string
  confidence: number
  reasoning: string
}

export interface DebateTurn {
  round: number
  speaker: string
  stance: string
  summary: string
  confidence?: number | null
}

export interface PricePoint {
  timestamp: string
  value: number
  label?: string | null
}

export interface TradeRecommendation {
  symbol: string
  recommendation: string
  confidence: number
  riskScore: number
  analysts: AnalystInsight[]
  debateRounds: number
  traderNotes: string
  timestamp: string
  priceSeries: PricePoint[]
  debateHistory: DebateTurn[]
  keyInsights: string[]
  strategy: string
}

export interface MetricsSummary {
  accuracy: number
  winRate: number
  avgConfidence: number
  sharpeRatio: number | null
  monthlyPerformance: Array<Record<string, unknown>>
  equityCurve: PricePoint[]
  recommendationDistribution: Record<string, number>
}

export interface AnalyzePayload {
  symbol: string
  lookbackDays: number
  strategy: string
}

export interface StatusSnapshot {
  lastAnalysis: string | null
  pendingJobs: number
  memoryMb: number
  systemStatus: string
}
