<template>
  <div class="scanner-page">
    <!-- ═══════ NAVBAR ═══════ -->
    <nav class="sc-nav">
      <div class="sc-nav-left" @click="$router.push('/')">
        <span class="sc-nav-brand">MIROFISH OFFLINE</span>
      </div>
      <div class="sc-nav-center">
        <div class="sc-nav-links">
          <button class="sc-nav-link" @click="$router.push('/')">Home</button>
          <button class="sc-nav-link" @click="$router.push('/prediction')">Prediction</button>
          <button class="sc-nav-link" @click="$router.push('/backtest')">Backtest</button>
          <button class="sc-nav-link active" @click="$router.push('/scanner')">Scanner</button>
        </div>
        <span class="paper-badge">PAPER</span>
      </div>
      <div class="sc-nav-right">
        <button class="sc-nav-back" @click="$router.push('/')">
          <span class="back-arrow">←</span> Home
        </button>
      </div>
    </nav>

    <!-- ═══════ HERO STRIP ═══════ -->
    <div class="sc-hero">
      <div class="sc-hero-inner">
        <div class="sc-hero-left">
          <span class="sc-hero-tag">SCANNER</span>
          <span class="sc-hero-sep">/</span>
          <span class="sc-hero-tag accent">SIGNAL DETECTION</span>
          <span class="sc-hero-sep">/</span>
          <span class="sc-hero-tag">MARKET SCANNING</span>
        </div>
        <div class="sc-hero-right">
          <div class="sc-hero-stat">
            <span class="sc-hero-stat-val">{{ scanRuns.length }}</span>
            <span class="sc-hero-stat-label">Scans</span>
          </div>
          <div class="sc-hero-stat">
            <span class="sc-hero-stat-val">{{ totalActionableAll }}</span>
            <span class="sc-hero-stat-label">Signals Found</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════ MAIN CONTENT ═══════ -->
    <div class="sc-main">
      <div class="sc-grid">

        <!-- ══════════════ LEFT PANEL ══════════════ -->
        <div class="sc-col sc-col-left">

          <!-- Scan Config Panel -->
          <div class="sc-panel">
            <div class="sc-panel-head">
              <div class="sc-panel-title">
                <span class="sc-dot"></span>
                Scan Markets
              </div>
            </div>
            <div class="sc-run-form">
              <div class="sc-form-row">
                <label class="sc-label">Markets</label>
                <input
                  v-model.number="marketCount"
                  type="number"
                  class="sc-input"
                  min="1"
                  max="100"
                  :disabled="isRunning"
                />
              </div>
              <div class="sc-form-row">
                <label class="sc-label">Min Volume</label>
                <input
                  v-model.number="minVolume"
                  type="number"
                  class="sc-input"
                  min="0"
                  step="1000"
                  :disabled="isRunning"
                />
              </div>
              <button
                class="sc-run-btn"
                :class="{ disabled: isRunning }"
                @click="runScan"
                :disabled="isRunning"
              >
                <span class="run-btn-label">
                  <span v-if="!isRunning">Scan Markets</span>
                  <span v-else class="running-text">
                    <span class="run-spinner"></span>
                    Scanning...
                  </span>
                </span>
                <span class="run-btn-arrow" v-if="!isRunning">→</span>
              </button>
            </div>
          </div>

          <!-- Progress Badge -->
          <div v-if="isRunning && currentRun" class="sc-progress-badge">
            <span class="progress-pulse"></span>
            SCANNING — {{ currentRun.completed_markets + (currentRun.failed_markets || 0) }}/{{ currentRun.total_markets || '?' }} markets
          </div>

          <!-- Scan History Panel -->
          <div class="sc-panel">
            <div class="sc-panel-head">
              <div class="sc-panel-title">
                <span class="sc-dot"></span>
                Scan History
              </div>
              <button class="sc-btn-sm" @click="loadScans">Refresh</button>
            </div>
            <div class="sc-history">
              <template v-if="loadingHistory && scanRuns.length === 0">
                <div v-for="i in 3" :key="'skel-'+i" class="sc-skeleton">
                  <div class="skel-line skel-title"></div>
                  <div class="skel-line skel-meta"></div>
                </div>
              </template>

              <div v-if="!loadingHistory && scanRuns.length === 0" class="sc-empty-mini">
                No scans yet
              </div>

              <div
                v-for="run in scanRuns"
                :key="run.id"
                class="history-row"
                :class="{ active: activeRunId === run.id }"
                @click="selectRun(run)"
              >
                <div class="history-left">
                  <div class="history-title">{{ run.id.substring(0, 15) }}...</div>
                  <div class="history-date">{{ formatDate(run.started_at) }}</div>
                </div>
                <div class="history-right">
                  <span class="history-status" :class="'status-' + run.status">
                    {{ run.status }}
                  </span>
                  <span v-if="run.status === 'SCANNING' || run.status === 'PENDING'" class="history-progress">
                    {{ (run.completed_markets || 0) + (run.failed_markets || 0) }}/{{ run.total_markets || '?' }}
                  </span>
                  <span v-if="run.actionable_count" class="history-actionable">
                    {{ run.actionable_count }} signals
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ══════════════ RIGHT PANEL ══════════════ -->
        <div class="sc-col sc-col-right">

          <!-- Error State -->
          <div v-if="errorMsg" class="sc-panel panel-error">
            <div class="sc-panel-head">
              <div class="sc-panel-title">
                <span class="sc-dot error-dot"></span>
                Error
              </div>
            </div>
            <div class="error-msg">{{ errorMsg }}</div>
          </div>

          <!-- Empty State -->
          <div v-if="!currentRun && !errorMsg && !loadingRun" class="sc-panel">
            <div class="sc-empty-state">
              <div class="empty-icon">◇</div>
              <div class="empty-text">Scan markets to find the best trading signals</div>
              <div class="empty-hint">Configure market count and click Scan Markets</div>
            </div>
          </div>

          <!-- Loading State -->
          <div v-if="loadingRun && !currentRun" class="sc-panel">
            <div class="sc-skeleton-results">
              <div v-for="i in 4" :key="'rskel-'+i" class="skel-metric-card">
                <div class="skel-line skel-val"></div>
                <div class="skel-line skel-label"></div>
              </div>
            </div>
          </div>

          <!-- Summary Cards -->
          <div v-if="currentRun" class="sc-panel">
            <div class="sc-panel-head">
              <div class="sc-panel-title">
                <span class="sc-dot"></span>
                Summary
              </div>
              <span v-if="currentRun.status === 'COMPLETED'" class="status-badge completed">COMPLETED</span>
              <span v-else-if="currentRun.status === 'FAILED'" class="status-badge failed">FAILED</span>
              <span v-else-if="currentRun.status === 'SCANNING'" class="status-badge scanning">SCANNING</span>
            </div>
            <div class="sc-metrics-grid">
              <div class="sc-metric-card">
                <div class="sc-metric-val accent-val">{{ actionableSignals.length }}</div>
                <div class="sc-metric-label">Actionable Signals</div>
              </div>
              <div class="sc-metric-card">
                <div class="sc-metric-val" :class="avgEdgeClass">{{ formatEdge(avgEdge) }}</div>
                <div class="sc-metric-label">Avg Edge</div>
              </div>
              <div class="sc-metric-card">
                <div class="sc-metric-val" :class="bestEdgeClass">{{ formatEdge(bestEdge) }}</div>
                <div class="sc-metric-label">Best Signal</div>
              </div>
              <div class="sc-metric-card">
                <div class="sc-metric-val">{{ currentRun.duration_seconds ? currentRun.duration_seconds + 's' : '...' }}</div>
                <div class="sc-metric-label">Scan Duration</div>
              </div>
            </div>
          </div>

          <!-- Filter Bar -->
          <div v-if="currentRun && allSignals.length > 0" class="sc-filter-bar">
            <select v-model="filterCategory" class="sc-filter-select">
              <option value="">All Categories</option>
              <option v-for="cat in availableCategories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
            <select v-model="filterTier" class="sc-filter-select">
              <option value="">All Tiers</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
            </select>
            <select v-model="filterDirection" class="sc-filter-select">
              <option value="">All Directions</option>
              <option value="BUY_YES">BUY YES</option>
              <option value="BUY_NO">BUY NO</option>
              <option value="HOLD">HOLD</option>
            </select>
            <label class="sc-filter-toggle">
              <input type="checkbox" v-model="hideHold" />
              <span>Hide HOLD</span>
            </label>
          </div>

          <!-- Signal Table -->
          <div v-if="currentRun && filteredSignals.length > 0" class="sc-panel">
            <div class="sc-panel-head">
              <div class="sc-panel-title">
                <span class="sc-dot"></span>
                Signals
              </div>
              <span class="sc-results-count">{{ filteredSignals.length }} signals</span>
            </div>
            <div class="sc-table-wrap">
              <table class="sc-table">
                <thead>
                  <tr>
                    <th class="sortable" @click="sortBy('market_title')">
                      Market <span class="sort-arrow">{{ sortArrow('market_title') }}</span>
                    </th>
                    <th class="sortable" @click="sortBy('category')">
                      Category <span class="sort-arrow">{{ sortArrow('category') }}</span>
                    </th>
                    <th class="sortable" @click="sortBy('direction')">
                      Action <span class="sort-arrow">{{ sortArrow('direction') }}</span>
                    </th>
                    <th class="sortable" @click="sortBy('edge')">
                      Edge <span class="sort-arrow">{{ sortArrow('edge') }}</span>
                    </th>
                    <th class="sortable" @click="sortBy('confidence_tier')">
                      Tier <span class="sort-arrow">{{ sortArrow('confidence_tier') }}</span>
                    </th>
                    <th class="sortable" @click="sortBy('market_prob')">
                      Price <span class="sort-arrow">{{ sortArrow('market_prob') }}</span>
                    </th>
                    <th class="sortable" @click="sortBy('market_volume')">
                      Volume <span class="sort-arrow">{{ sortArrow('market_volume') }}</span>
                    </th>
                    <th class="sortable" @click="sortBy('days_remaining')">
                      Days <span class="sort-arrow">{{ sortArrow('days_remaining') }}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(sig, idx) in sortedSignals"
                    :key="sig.id"
                    class="sc-table-row fade-in"
                    :style="{ animationDelay: (idx * 20) + 'ms' }"
                    @click="toggleReasoning(sig.id)"
                  >
                    <td class="col-market">{{ truncate(sig.market_title, 45) }}</td>
                    <td><span v-if="sig.category" class="category-badge">{{ sig.category }}</span><span v-else>-</span></td>
                    <td>
                      <span class="signal-badge-sm" :class="directionClass(sig.direction)">
                        {{ formatDirection(sig.direction) }}
                      </span>
                    </td>
                    <td class="col-num" :class="edgeClass(sig.edge)">
                      {{ formatEdge(sig.edge) }}
                    </td>
                    <td>
                      <span class="tier-badge" :class="'tier-' + (sig.confidence_tier || 'LOW').toLowerCase()">
                        {{ sig.confidence_tier || 'LOW' }}
                      </span>
                    </td>
                    <td class="col-num">{{ formatPct(sig.market_prob) }}</td>
                    <td class="col-num">{{ formatVolume(sig.market_volume) }}</td>
                    <td class="col-num">{{ sig.days_remaining != null ? Math.round(sig.days_remaining) + 'd' : '-' }}</td>
                  </tr>
                  <!-- Expandable reasoning row -->
                  <tr v-for="sig in sortedSignals" :key="'reason-'+sig.id" v-show="expandedId === sig.id" class="reasoning-row">
                    <td colspan="8">
                      <div class="reasoning-content">{{ sig.reasoning || 'No reasoning available' }}</div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- No Signals Message -->
          <div v-if="currentRun && currentRun.status === 'COMPLETED' && allSignals.length === 0" class="sc-panel">
            <div class="sc-empty-state">
              <div class="empty-icon">◇</div>
              <div class="empty-text">No signals generated</div>
              <div class="empty-hint">Try scanning with different parameters</div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { startScan, getScanRun, listScanRuns } from '../api/scanner'

// ═══════ STATE ═══════
const marketCount = ref(30)
const minVolume = ref(10000)
const isRunning = ref(false)
const loadingHistory = ref(false)
const loadingRun = ref(false)
const errorMsg = ref('')
const scanRuns = ref([])
const currentRun = ref(null)
const allSignals = ref([])
const activeRunId = ref(null)
const sortKey = ref('edge')
const sortDir = ref('desc')
const filterCategory = ref('')
const filterTier = ref('')
const filterDirection = ref('')
const hideHold = ref(true)
const expandedId = ref(null)
let pollInterval = null

// ═══════ COMPUTED ═══════
const totalActionableAll = computed(() => {
  return scanRuns.value.reduce((sum, r) => sum + (r.actionable_count || 0), 0)
})

const actionableSignals = computed(() => {
  return allSignals.value.filter(s => s.direction !== 'HOLD')
})

const avgEdge = computed(() => {
  const sigs = actionableSignals.value
  if (!sigs.length) return null
  return sigs.reduce((sum, s) => sum + Math.abs(s.edge), 0) / sigs.length
})

const bestEdge = computed(() => {
  const sigs = actionableSignals.value
  if (!sigs.length) return null
  return sigs.reduce((best, s) => Math.abs(s.edge) > Math.abs(best) ? s.edge : best, 0)
})

const avgEdgeClass = computed(() => edgeClass(avgEdge.value))
const bestEdgeClass = computed(() => edgeClass(bestEdge.value))

const availableCategories = computed(() => {
  const cats = new Set(allSignals.value.map(s => s.category).filter(Boolean))
  return [...cats].sort()
})

const filteredSignals = computed(() => {
  let sigs = [...allSignals.value]
  if (hideHold.value) sigs = sigs.filter(s => s.direction !== 'HOLD')
  if (filterCategory.value) sigs = sigs.filter(s => s.category === filterCategory.value)
  if (filterTier.value) sigs = sigs.filter(s => s.confidence_tier === filterTier.value)
  if (filterDirection.value) sigs = sigs.filter(s => s.direction === filterDirection.value)
  return sigs
})

const sortedSignals = computed(() => {
  const arr = [...filteredSignals.value]
  if (!sortKey.value) return arr
  arr.sort((a, b) => {
    let av = a[sortKey.value]
    let bv = b[sortKey.value]
    if (sortKey.value === 'edge') {
      av = Math.abs(av || 0)
      bv = Math.abs(bv || 0)
    }
    if (sortKey.value === 'market_title') {
      av = (av || '').toLowerCase()
      bv = (bv || '').toLowerCase()
    }
    if (av == null) return 1
    if (bv == null) return -1
    if (av < bv) return sortDir.value === 'asc' ? -1 : 1
    if (av > bv) return sortDir.value === 'asc' ? 1 : -1
    return 0
  })
  return arr
})

// ═══════ METHODS ═══════
const formatPct = (v) => {
  if (v == null) return '-'
  return (v * 100).toFixed(1) + '%'
}
const formatEdge = (v) => {
  if (v == null) return '-'
  const pct = (v * 100).toFixed(1)
  return (v >= 0 ? '+' : '') + pct + '%'
}
const formatVolume = (v) => {
  if (v == null) return '-'
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M'
  if (v >= 1_000) return (v / 1_000).toFixed(0) + 'K'
  return v.toFixed(0)
}
const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
const formatDirection = (d) => {
  if (d === 'BUY_YES') return 'BUY YES'
  if (d === 'BUY_NO') return 'BUY NO'
  return d || '-'
}
const truncate = (s, n) => s && s.length > n ? s.substring(0, n) + '...' : s

const directionClass = (d) => {
  if (d === 'BUY_YES') return 'signal-buy-yes'
  if (d === 'BUY_NO') return 'signal-buy-no'
  return 'signal-hold'
}

const edgeClass = (edge) => {
  if (edge == null) return ''
  return edge >= 0 ? 'val-positive' : 'val-negative'
}

const sortBy = (key) => {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = key === 'edge' || key === 'market_volume' ? 'desc' : 'asc'
  }
}

const sortArrow = (key) => {
  if (sortKey.value !== key) return ''
  return sortDir.value === 'asc' ? '↑' : '↓'
}

const toggleReasoning = (id) => {
  expandedId.value = expandedId.value === id ? null : id
}

// ═══════ API CALLS ═══════
const runScan = async () => {
  if (isRunning.value) return
  isRunning.value = true
  errorMsg.value = ''
  currentRun.value = null
  allSignals.value = []
  try {
    const res = await startScan(marketCount.value, minVolume.value)
    const resp = res.data || res
    const runId = resp.data?.run_id || resp.run_id
    activeRunId.value = runId
    currentRun.value = { id: runId, status: 'PENDING', total_markets: marketCount.value, completed_markets: 0, failed_markets: 0 }
    startPolling(runId)
  } catch (e) {
    errorMsg.value = 'Failed to start scan: ' + (e.message || '')
    isRunning.value = false
  }
}

const selectRun = async (run) => {
  activeRunId.value = run.id
  errorMsg.value = ''
  loadingRun.value = true
  try {
    const res = await getScanRun(run.id)
    const data = res.data || res
    currentRun.value = data
    allSignals.value = data.signals || []
    if (data.status === 'SCANNING' || data.status === 'PENDING') {
      isRunning.value = true
      startPolling(run.id)
    }
  } catch (e) {
    errorMsg.value = 'Failed to load scan: ' + (e.message || '')
  } finally {
    loadingRun.value = false
  }
}

const loadScans = async () => {
  loadingHistory.value = true
  try {
    const res = await listScanRuns()
    scanRuns.value = res.data || res || []
  } catch (e) {
    console.error('Failed to load scans:', e)
  } finally {
    loadingHistory.value = false
  }
}

const startPolling = (runId) => {
  stopPolling()
  pollInterval = setInterval(async () => {
    try {
      const res = await getScanRun(runId)
      const data = res.data || res
      currentRun.value = data
      allSignals.value = data.signals || []
      if (data.status === 'COMPLETED' || data.status === 'FAILED') {
        stopPolling()
        isRunning.value = false
        loadScans()
      }
    } catch (e) {
      console.error('Poll error:', e)
    }
  }, 5000)
}

const stopPolling = () => {
  if (pollInterval) { clearInterval(pollInterval); pollInterval = null }
}

// ═══════ LIFECYCLE ═══════
onMounted(() => { loadScans() })
onUnmounted(() => { stopPolling() })
</script>

<style scoped>
/* ═══════ VARIABLES ═══════ */
:root {
  --mono: 'JetBrains Mono', 'SF Mono', monospace;
  --sans: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  --orange: #FF4500;
  --green: #10B981;
  --red: #dc2626;
  --border: #EAEAEA;
  --bg-subtle: #FAFAFA;
  --text-primary: #000;
  --text-secondary: #666;
  --text-muted: #999;
}

/* ═══════ PAGE ═══════ */
.scanner-page {
  min-height: 100vh;
  background: #fff;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

/* ═══════ NAVBAR ═══════ */
.sc-nav {
  height: 60px;
  background: #000;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
}
.sc-nav-left { cursor: pointer; }
.sc-nav-brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.15rem;
}
.sc-nav-center {
  display: flex;
  align-items: center;
  gap: 12px;
}
.sc-nav-links {
  display: flex;
  align-items: center;
  gap: 4px;
}
.sc-nav-link {
  background: none;
  border: 1px solid rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.6);
  padding: 5px 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}
.sc-nav-link:hover {
  border-color: rgba(255,255,255,0.4);
  color: rgba(255,255,255,0.9);
}
.sc-nav-link.active {
  border-color: #FF4500;
  color: #FF4500;
}
.paper-badge {
  background: #FF4500;
  color: #000;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 6px;
  letter-spacing: 0.1em;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
}
.sc-nav-right { display: flex; align-items: center; }
.sc-nav-back {
  background: none;
  border: 1px solid rgba(255,255,255,0.2);
  color: rgba(255,255,255,0.7);
  padding: 6px 18px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.sc-nav-back:hover { border-color: #FF4500; color: #FF4500; }
.back-arrow { font-size: 1rem; }

/* ═══════ HERO STRIP ═══════ */
.sc-hero {
  border-bottom: 1px solid #EAEAEA;
  background: #FAFAFA;
}
.sc-hero-inner {
  max-width: 1400px;
  margin: 0 auto;
  padding: 14px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sc-hero-left {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 1.5px;
  color: #999;
}
.sc-hero-tag { text-transform: uppercase; }
.sc-hero-tag.accent { color: #FF4500; }
.sc-hero-sep { color: #DDD; }
.sc-hero-right { display: flex; gap: 30px; }
.sc-hero-stat { display: flex; flex-direction: column; align-items: center; }
.sc-hero-stat-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.3rem;
  font-weight: 700;
  color: #000;
}
.sc-hero-stat-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* ═══════ MAIN LAYOUT ═══════ */
.sc-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 30px 40px 60px;
}
.sc-grid {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 30px;
  align-items: start;
}

/* ═══════ PANELS ═══════ */
.sc-panel {
  border: 1px solid #EAEAEA;
  background: #fff;
  margin-bottom: 20px;
}
.sc-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #F5F5F5;
}
.sc-panel-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: #999;
  display: flex;
  align-items: center;
  gap: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.sc-dot {
  width: 8px;
  height: 8px;
  background: #FF4500;
  display: inline-block;
}
.sc-dot.error-dot { background: #dc2626; }

/* ═══════ SMALL BUTTON ═══════ */
.sc-btn-sm {
  background: none;
  border: 1px solid #E5E5E5;
  padding: 4px 14px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: #999;
  cursor: pointer;
  transition: all 0.2s;
}
.sc-btn-sm:hover { border-color: #000; color: #000; }

/* ═══════ RUN FORM ═══════ */
.sc-run-form { padding: 20px; }
.sc-form-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.sc-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  min-width: 100px;
}
.sc-input {
  flex: 1;
  border: 1px solid #EAEAEA;
  padding: 8px 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  background: #FAFAFA;
  outline: revert;
  transition: border-color 0.2s;
}
.sc-input:focus { border-color: #999; }

/* ═══════ RUN BUTTON ═══════ */
.sc-run-btn {
  width: 100%;
  background: #000;
  color: #fff;
  border: none;
  padding: 16px 20px;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: 0.5px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
}
.sc-run-btn:hover:not(.disabled) { background: #FF4500; }
.sc-run-btn.disabled { background: #333; cursor: not-allowed; }
.run-btn-arrow { font-size: 1.2rem; }
.running-text { display: flex; align-items: center; gap: 10px; }
.run-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

/* ═══════ PROGRESS BADGE ═══════ */
.sc-progress-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  font-weight: 600;
  color: #FF4500;
  padding: 10px 20px;
  border: 1px solid #FF4500;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.progress-pulse {
  width: 8px;
  height: 8px;
  background: #FF4500;
  display: inline-block;
  animation: pulse-dot 1.5s infinite;
}

/* ═══════ HISTORY ═══════ */
.sc-history {
  max-height: 350px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #DDD #F5F5F5;
}
.sc-history::-webkit-scrollbar { width: 4px; }
.sc-history::-webkit-scrollbar-track { background: #F5F5F5; }
.sc-history::-webkit-scrollbar-thumb { background: #DDD; }

.history-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #F5F5F5;
  cursor: pointer;
  transition: background 0.15s;
  gap: 12px;
}
.history-row:hover { background: #FAFAFA; }
.history-row.active { background: #FFF8F5; }
.history-left { flex: 1; min-width: 0; }
.history-title {
  font-size: 0.85rem;
  font-weight: 500;
  line-height: 1.3;
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.history-date {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: #CCC;
  margin-top: 3px;
}
.history-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.history-status {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  padding: 2px 8px;
  letter-spacing: 0.5px;
}
.status-COMPLETED { color: #10B981; background: #ECFDF5; }
.status-FAILED { color: #dc2626; background: #FEF2F2; }
.status-SCANNING, .status-PENDING { color: #FF4500; background: #FFF5F0; }
.history-progress {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: #FF4500;
}
.history-actionable {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: #10B981;
}

/* ═══════ ERROR PANEL ═══════ */
.panel-error { border-color: #dc2626; }
.error-msg {
  padding: 16px 20px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem;
  color: #dc2626;
  line-height: 1.5;
}

/* ═══════ EMPTY STATE ═══════ */
.sc-empty-state {
  padding: 50px 20px;
  text-align: center;
}
.empty-icon { font-size: 2rem; margin-bottom: 12px; color: #DDD; }
.empty-text { font-weight: 500; color: #999; margin-bottom: 6px; }
.empty-hint {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #CCC;
  max-width: 300px;
  margin: 0 auto;
  line-height: 1.5;
}
.sc-empty-mini {
  padding: 20px;
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: #CCC;
}

/* ═══════ SKELETON ═══════ */
.sc-skeleton {
  padding: 14px 20px;
  border-bottom: 1px solid #F5F5F5;
}
.skel-line {
  height: 12px;
  background: linear-gradient(90deg, #F0F0F0 25%, #E5E5E5 50%, #F0F0F0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skel-title { width: 80%; margin-bottom: 10px; }
.skel-meta { width: 50%; height: 10px; }
.sc-skeleton-results {
  display: flex;
  gap: 1px;
  background: #F0F0F0;
}
.skel-metric-card {
  flex: 1;
  background: #fff;
  padding: 20px;
  text-align: center;
}
.skel-val { width: 60%; height: 20px; margin: 0 auto 8px; }
.skel-label { width: 80%; height: 10px; margin: 0 auto; }

/* ═══════ STATUS BADGES ═══════ */
.status-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 4px 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.status-badge.completed { background: #ECFDF5; color: #10B981; }
.status-badge.failed { background: #FEF2F2; color: #dc2626; }
.status-badge.scanning { background: #FFF5F0; color: #FF4500; }

/* ═══════ METRICS GRID ═══════ */
.sc-metrics-grid {
  display: flex;
  gap: 1px;
  background: #F0F0F0;
}
.sc-metric-card {
  flex: 1;
  background: #fff;
  padding: 20px;
  text-align: center;
}
.sc-metric-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 4px;
}
.sc-metric-val.accent-val { color: #FF4500; }
.sc-metric-val.val-positive { color: #10B981; }
.sc-metric-val.val-negative { color: #dc2626; }
.sc-metric-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: #BBB;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ═══════ FILTER BAR ═══════ */
.sc-filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.sc-filter-select {
  border: 1px solid #EAEAEA;
  padding: 6px 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  background: #FAFAFA;
  color: #666;
  cursor: pointer;
  outline: none;
}
.sc-filter-select:focus { border-color: #999; }
.sc-filter-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #666;
  cursor: pointer;
}
.sc-filter-toggle input {
  accent-color: #FF4500;
}

/* ═══════ SIGNAL TABLE ═══════ */
.sc-results-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: #BBB;
}
.sc-table-wrap {
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: #DDD #F5F5F5;
}
.sc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.sc-table thead {
  border-bottom: 1px solid #EAEAEA;
}
.sc-table th {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 10px 14px;
  text-align: left;
  white-space: nowrap;
}
.sc-table th.sortable {
  cursor: pointer;
  user-select: none;
  transition: color 0.2s;
}
.sc-table th.sortable:hover { color: #000; }
.sort-arrow {
  font-size: 0.7rem;
  color: #FF4500;
}
.sc-table td {
  padding: 10px 14px;
  border-bottom: 1px solid #F5F5F5;
  color: #333;
}
.sc-table-row {
  transition: background 0.15s;
  cursor: pointer;
}
.sc-table-row:hover { background: #FAFAFA; }
.col-market {
  max-width: 220px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.col-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  font-weight: 500;
}
.col-num.val-positive { color: #10B981; }
.col-num.val-negative { color: #dc2626; }

/* Signal badges */
.signal-badge-sm {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 8px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.signal-badge-sm.signal-buy-yes { background: #ECFDF5; color: #10B981; }
.signal-badge-sm.signal-buy-no { background: #FEF2F2; color: #dc2626; }
.signal-badge-sm.signal-hold { background: #F5F5F5; color: #999; }

/* Tier badges */
.tier-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 700;
  padding: 2px 8px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.tier-badge.tier-high { background: #ECFDF5; color: #10B981; }
.tier-badge.tier-medium { background: #FFFBEB; color: #F59E0B; }
.tier-badge.tier-low { background: #F5F5F5; color: #999; }

/* Category badge */
.category-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 600;
  padding: 2px 8px;
  background: #F5F5F5;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

/* Reasoning row */
.reasoning-row td {
  padding: 0 14px 14px;
  border-bottom: 1px solid #EAEAEA;
}
.reasoning-content {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #666;
  line-height: 1.6;
  padding: 12px 16px;
  background: #FAFAFA;
  border-left: 3px solid #FF4500;
}

/* ═══════ ANIMATIONS ═══════ */
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.fade-in {
  animation: fadeInUp 0.3s ease both;
}

/* ═══════ RESPONSIVE ═══════ */
@media (max-width: 1024px) {
  .sc-grid { grid-template-columns: 1fr; }
  .sc-col-left { order: 1; }
  .sc-col-right { order: 2; }
  .sc-main { padding: 20px; }
  .sc-nav { padding: 0 20px; }
  .sc-hero-inner { padding: 12px 20px; }
  .sc-hero-left { display: none; }
}
@media (max-width: 768px) {
  .sc-nav-center { display: none; }
  .sc-hero-right { gap: 16px; }
  .sc-metrics-grid { flex-direction: column; gap: 0; }
  .sc-filter-bar { flex-direction: column; align-items: stretch; }
}
</style>
