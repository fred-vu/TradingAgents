<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <header class="border-b border-slate-800 bg-slate-900/60 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div>
          <p class="text-xs uppercase tracking-[0.4rem] text-primary-100">
            TradingAgents Desktop
          </p>
          <h1 class="mt-1 text-3xl font-semibold text-primary-50">
            Research Control Center
          </h1>
        </div>
        <div class="flex items-center gap-3 text-sm text-slate-300">
          <span class="inline-flex h-2 w-2 rounded-full bg-success"></span>
          Backend connected
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-6 py-10">
      <Dashboard
        :refresh-token="refreshToken"
        @analysis-started="handleAnalysisStarted"
        @analysis-complete="handleAnalysisComplete"
      />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import Dashboard from '@/components/Dashboard.vue'

const refreshToken = ref(0)

const handleAnalysisStarted = () => {
  // Reserved for future loading indicators
}

const handleAnalysisComplete = () => {
  refreshToken.value += 1
}
</script>
