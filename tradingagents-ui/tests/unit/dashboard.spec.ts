import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import Dashboard from '@/components/Dashboard.vue'
import type { MetricsSummary, TradeRecommendation } from '@/types'

const mockRecommendation: TradeRecommendation = {
  symbol: 'AAPL',
  recommendation: 'BUY',
  confidence: 0.72,
  riskScore: 0.18,
  analysts: [
    { name: 'market_analyst', signal: 'BULLISH', confidence: 0.8, reasoning: 'Mock reasoning' },
  ],
  debateRounds: 2,
  traderNotes: 'Mock notes',
  timestamp: new Date().toISOString(),
  priceSeries: [
    { timestamp: new Date().toISOString(), value: 150 },
    { timestamp: new Date().toISOString(), value: 152 },
  ],
  debateHistory: [
    {
      round: 1,
      speaker: 'market_analyst',
      stance: 'support',
      summary: 'Mock summary',
      confidence: 0.8,
    },
  ],
  keyInsights: ['Mock insight'],
  strategy: 'balanced',
}

const mockMetrics: MetricsSummary = {
  accuracy: 0.7,
  winRate: 0.6,
  avgConfidence: 0.65,
  sharpeRatio: null,
  monthlyPerformance: [{ month: '2025-01', signals: 4 }],
  equityCurve: [
    { timestamp: new Date().toISOString(), value: 100 },
    { timestamp: new Date().toISOString(), value: 102 },
  ],
  recommendationDistribution: { BUY: 3, HOLD: 1, SELL: 1 },
}

vi.mock('@/services/api', () => ({
  analyzeSymbol: vi.fn(async () => mockRecommendation),
  getMetrics: vi.fn(async () => mockMetrics),
}))

vi.mock('vue-chartjs', () => ({
  Line: {
    name: 'LineStub',
    render: () => null,
  },
}))

describe('Dashboard.vue', () => {
  it('renders initial form defaults', () => {
    const wrapper = mount(Dashboard, { props: { refreshToken: 0 } })
    const symbolInput = wrapper.find('input')
    expect(symbolInput.element.value).toBe('AAPL')
    expect(wrapper.html()).toContain('Balanced')
    expect(wrapper.text()).toContain('Lookback')
  })

  it('emits events and displays analysis result', async () => {
    const wrapper = mount(Dashboard, { props: { refreshToken: 0 } })
    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(wrapper.emitted('analysis-started')).toBeTruthy()
    expect(wrapper.emitted('analysis-complete')).toBeTruthy()
    expect(wrapper.text()).toContain('Mock reasoning')
    expect(wrapper.text()).toContain('Mock insight')
  })
})
