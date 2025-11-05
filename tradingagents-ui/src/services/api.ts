import axios from 'axios'

import type { AnalyzePayload, MetricsSummary, TradeRecommendation } from '@/types'

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8000/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60_000,
})

const toTradeRecommendation = (payload: any): TradeRecommendation => ({
  symbol: payload.symbol,
  recommendation: payload.recommendation,
  confidence: payload.confidence ?? 0,
  riskScore: payload.risk_score ?? payload.riskScore ?? 0,
  analysts: (payload.analysts ?? []).map((analyst: any) => ({
    name: analyst.name,
    signal: analyst.signal,
    confidence: analyst.confidence ?? 0,
    reasoning: analyst.reasoning ?? '',
  })),
  debateRounds: payload.debate_rounds ?? payload.debateRounds ?? 0,
  traderNotes: payload.trader_notes ?? payload.traderNotes ?? '',
  timestamp: typeof payload.timestamp === 'string' ? payload.timestamp : new Date().toISOString(),
  priceSeries: (payload.price_series ?? payload.priceSeries ?? []).map((point: any) => ({
    timestamp: typeof point.timestamp === 'string' ? point.timestamp : new Date(point.timestamp).toISOString(),
    value: point.value ?? 0,
    label: point.label ?? null,
  })),
  debateHistory: (payload.debate_history ?? payload.debateHistory ?? []).map((turn: any) => ({
    round: turn.round ?? 0,
    speaker: turn.speaker ?? 'unknown',
    stance: turn.stance ?? 'neutral',
    summary: turn.summary ?? '',
    confidence: turn.confidence ?? null,
  })),
  keyInsights: payload.key_insights ?? payload.keyInsights ?? [],
  strategy: payload.strategy ?? 'balanced',
})

const toMetricsSummary = (payload: any): MetricsSummary => ({
  accuracy: payload.accuracy ?? 0,
  winRate: payload.win_rate ?? payload.winRate ?? 0,
  avgConfidence: payload.avg_confidence ?? payload.avgConfidence ?? 0,
  sharpeRatio: payload.sharpe_ratio ?? payload.sharpeRatio ?? null,
  monthlyPerformance: payload.monthly_performance ?? payload.monthlyPerformance ?? [],
  equityCurve: (payload.equity_curve ?? payload.equityCurve ?? []).map((point: any) => ({
    timestamp: typeof point.timestamp === 'string' ? point.timestamp : new Date(point.timestamp).toISOString(),
    value: point.value ?? 0,
    label: point.label ?? null,
  })),
  recommendationDistribution:
    payload.recommendation_distribution ?? payload.recommendationDistribution ?? {},
})

export const analyzeSymbol = async (payload: AnalyzePayload): Promise<TradeRecommendation> => {
  const response = await client.post('/analyze', {
    symbol: payload.symbol,
    lookback_days: payload.lookbackDays,
    strategy: payload.strategy,
  })
  return toTradeRecommendation(response.data)
}

export const getMetrics = async (days = 30): Promise<MetricsSummary> => {
  const response = await client.get('/metrics', { params: { days } })
  return toMetricsSummary(response.data)
}
