<template>
  <section class="space-y-10">
    <form
      class="grid gap-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl backdrop-blur"
      @submit.prevent="runAnalysis"
    >
      <div class="grid gap-4 sm:grid-cols-3">
        <label class="flex flex-col gap-2 text-sm font-medium uppercase tracking-wide text-slate-300">
          Symbol
          <input
            v-model="form.symbol"
            class="rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-lg font-semibold uppercase tracking-wide text-primary-50 outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-500/60"
            maxlength="12"
            placeholder="AAPL"
            required
          />
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium uppercase tracking-wide text-slate-300">
          Lookback (days)
          <div class="relative">
            <input
              v-model.number="form.lookbackDays"
              type="number"
              min="5"
              max="365"
              class="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-lg font-semibold text-primary-50 outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-500/60"
            />
            <span class="absolute inset-y-0 right-4 flex items-center text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">Lookback</span>
          </div>
        </label>

        <label class="flex flex-col gap-2 text-sm font-medium uppercase tracking-wide text-slate-300">
          Strategy
          <select
            v-model="form.strategy"
            class="appearance-none rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-lg font-semibold capitalize text-primary-50 outline-none transition focus:border-primary-500 focus:ring-2 focus:ring-primary-500/60"
          >
            <option
              v-for="option in strategyOptions"
              :key="option.value"
              :value="option.value"
              class="bg-slate-900 text-slate-100"
            >
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-4">
        <p class="text-sm text-slate-400">
          Configure the analysis request. Balanced mode blends fundamental, news, and technical signals.
        </p>
        <button
          type="submit"
          class="inline-flex items-center gap-3 rounded-full bg-primary-500 px-6 py-3 text-sm font-semibold uppercase tracking-[0.3em] text-slate-950 transition hover:bg-primary-500/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="h-3 w-3 animate-spin rounded-full border-2 border-slate-900 border-t-transparent"></span>
          <span>{{ isLoading ? 'Running' : 'Run Analysis' }}</span>
        </button>
      </div>

      <p v-if="errorMessage" class="rounded-lg border border-danger/60 bg-danger/10 px-4 py-3 text-sm text-danger">
        {{ errorMessage }}
      </p>
    </form>

    <div class="grid gap-6 lg:grid-cols-3">
      <article class="lg:col-span-2 space-y-6">
        <section class="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <header class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-semibold uppercase tracking-[0.35em] text-slate-300">Recommendation</h2>
              <p class="text-sm text-slate-400">Aggregated analyst reasoning with debate history.</p>
            </div>
            <div v-if="analysis" class="flex items-center gap-3">
              <span class="rounded-full bg-primary-500/10 px-3 py-1 text-sm font-semibold uppercase tracking-[0.3em] text-primary-100">
                {{ analysis.strategy }}
              </span>
              <span
                :class="['rounded-full px-3 py-1 text-sm font-semibold uppercase tracking-[0.3em]', recommendationBadge]"
              >
                {{ analysis.recommendation }}
              </span>
            </div>
          </header>

          <div v-if="analysis" class="grid gap-6 md:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
            <div class="space-y-5">
              <div class="grid grid-cols-2 gap-4 text-sm text-slate-300">
                <div class="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
                  <p class="text-xs uppercase tracking-[0.3em] text-slate-500">Confidence</p>
                  <p class="mt-1 text-3xl font-semibold text-primary-50">{{ formatPercent(analysis.confidence) }}</p>
                </div>
                <div class="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
                  <p class="text-xs uppercase tracking-[0.3em] text-slate-500">Risk Score</p>
                  <p class="mt-1 text-3xl font-semibold text-primary-50">{{ formatPercent(analysis.riskScore) }}</p>
                </div>
              </div>

              <section class="space-y-3">
                <h3 class="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">Analyst Signals</h3>
                <ul class="grid gap-3 md:grid-cols-2">
                  <li
                    v-for="analyst in analysis.analysts"
                    :key="analyst.name"
                    class="rounded-xl border border-slate-800 bg-slate-950/80 p-4"
                  >
                    <div class="flex items-center justify-between gap-3">
                      <p class="text-sm font-semibold uppercase tracking-[0.25em] text-primary-100">{{ analyst.name }}</p>
                      <span class="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
                        {{ formatPercent(analyst.confidence) }}
                      </span>
                    </div>
                    <p class="mt-2 text-xs uppercase tracking-[0.3em] text-slate-500">{{ analyst.signal }}</p>
                    <p class="mt-3 text-sm text-slate-300 leading-relaxed">
                      {{ analyst.reasoning }}
                    </p>
                  </li>
                </ul>
              </section>

              <section v-if="analysis.keyInsights.length" class="space-y-3">
                <h3 class="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">Key Insights</h3>
                <ul class="grid gap-3 md:grid-cols-2">
                  <li
                    v-for="insight in analysis.keyInsights"
                    :key="insight"
                    class="rounded-xl border border-primary-500/40 bg-primary-500/10 p-4 text-sm text-primary-100"
                  >
                    {{ insight }}
                  </li>
                </ul>
              </section>
            </div>

            <aside class="space-y-4">
              <div class="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
                <p class="text-xs uppercase tracking-[0.3em] text-slate-500">Trader Notes</p>
                <p class="mt-3 whitespace-pre-line text-sm leading-relaxed text-slate-200">
                  {{ analysis.traderNotes }}
                </p>
              </div>

              <section v-if="analysis.debateHistory.length" class="rounded-xl border border-slate-800 bg-slate-950/80 p-4 space-y-3">
                <h3 class="text-xs uppercase tracking-[0.3em] text-slate-500">Debate Transcript</h3>
                <ul class="space-y-3 text-sm text-slate-300">
                  <li
                    v-for="turn in analysis.debateHistory"
                    :key="`${turn.round}-${turn.speaker}`"
                    class="rounded-lg border border-slate-800/80 bg-slate-900/60 px-3 py-3"
                  >
                    <p class="text-xs uppercase tracking-[0.4em] text-slate-500">
                      Round {{ turn.round }} · {{ turn.speaker }} ({{ turn.stance }})
                    </p>
                    <p class="mt-2 leading-relaxed">{{ turn.summary }}</p>
                  </li>
                </ul>
              </section>
            </aside>
          </div>

          <div v-else class="rounded-xl border border-dashed border-slate-800 bg-slate-950/60 p-6 text-sm text-slate-400">
            Submit a symbol to generate a multi-agent trading recommendation. Results will appear here once complete.
          </div>
        </section>
      </article>

      <aside class="space-y-6">
        <section class="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <header>
            <h2 class="text-lg font-semibold uppercase tracking-[0.35em] text-slate-300">Performance Metrics</h2>
            <p class="text-sm text-slate-400">Rolling 30-day evaluation of the research stack.</p>
          </header>
          <div v-if="metrics" class="grid gap-3 text-sm text-slate-300">
            <div class="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
              <p class="text-xs uppercase tracking-[0.3em] text-slate-500">Accuracy</p>
              <p class="mt-2 text-2xl font-semibold text-primary-50">{{ formatPercent(metrics.accuracy) }}</p>
            </div>
            <div class="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
              <p class="text-xs uppercase tracking-[0.3em] text-slate-500">Win Rate</p>
              <p class="mt-2 text-2xl font-semibold text-primary-50">{{ formatPercent(metrics.winRate) }}</p>
            </div>
            <div class="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
              <p class="text-xs uppercase tracking-[0.3em] text-slate-500">Average Confidence</p>
              <p class="mt-2 text-2xl font-semibold text-primary-50">{{ formatPercent(metrics.avgConfidence) }}</p>
            </div>
            <div class="rounded-xl border border-slate-800 bg-slate-950/80 p-4">
              <p class="text-xs uppercase tracking-[0.3em] text-slate-500">Sharpe Ratio</p>
              <p class="mt-2 text-2xl font-semibold text-primary-50">
                {{ metrics.sharpeRatio === null ? '—' : metrics.sharpeRatio.toFixed(2) }}
              </p>
            </div>
          </div>
          <div v-else class="rounded-xl border border-dashed border-slate-800 bg-slate-950/60 p-6 text-sm text-slate-400">
            Metrics will appear once an analysis has been completed.
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { analyzeSymbol, getMetrics } from '@/services/api'
import type { MetricsSummary, TradeRecommendation } from '@/types'

const props = defineProps<{
  refreshToken: number
}>()

const emit = defineEmits<{
  (event: 'analysis-started'): void
  (event: 'analysis-complete'): void
}>()

const form = reactive({
  symbol: 'AAPL',
  lookbackDays: 30,
  strategy: 'balanced',
})

const strategyOptions = [
  { label: 'Balanced', value: 'balanced' },
  { label: 'Aggressive', value: 'aggressive' },
  { label: 'Conservative', value: 'conservative' },
]

const analysis = ref<TradeRecommendation | null>(null)
const metrics = ref<MetricsSummary | null>(null)
const isLoading = ref(false)
const errorMessage = ref('')

const recommendationBadge = computed(() => {
  if (!analysis.value) {
    return 'bg-slate-800 text-slate-300 border border-slate-700'
  }
  const signal = analysis.value.recommendation.toUpperCase()
  if (signal === 'BUY' || signal === 'STRONG_BUY') {
    return 'bg-success/10 text-success border border-success/40'
  }
  if (signal === 'SELL' || signal === 'STRONG_SELL') {
    return 'bg-danger/10 text-danger border border-danger/40'
  }
  return 'bg-warning/10 text-warning border border-warning/40'
})

const formatPercent = (value: number) => `${Math.round((value ?? 0) * 100)}%`

const loadMetrics = async () => {
  try {
    metrics.value = await getMetrics()
  } catch (error) {
    console.error('Failed to load metrics', error)
  }
}

const runAnalysis = async () => {
  if (isLoading.value) {
    return
  }

  isLoading.value = true
  errorMessage.value = ''
  emit('analysis-started')

  try {
    const result = await analyzeSymbol({
      symbol: form.symbol.trim(),
      lookbackDays: form.lookbackDays,
      strategy: form.strategy,
    })
    analysis.value = result
    emit('analysis-complete')
    await loadMetrics()
  } catch (error: any) {
    console.error('Analysis failed', error)
    errorMessage.value =
      error?.response?.data?.detail ??
      error?.message ??
      'Analysis failed. Please verify your backend is running.'
  } finally {
    isLoading.value = false
  }
}

watch(
  () => props.refreshToken,
  () => {
    loadMetrics()
  },
  { immediate: true },
)

onMounted(() => {
  if (!metrics.value) {
    loadMetrics()
  }
})
</script>
