import service from './index'

// Start a signal scan
export const startScan = (numMarkets = 30, minVolume = 10000, maxThreads = 5) => {
  return service.post('/api/scanner/run', {
    num_markets: numMarkets,
    min_volume: minVolume,
    max_threads: maxThreads,
  })
}

// Get a specific scan run (includes signals)
export const getScanRun = (runId) => {
  return service.get(`/api/scanner/run/${runId}`)
}

// List all scan runs
export const listScanRuns = () => {
  return service.get('/api/scanner/runs')
}

// Delete a scan run
export const deleteScanRun = (runId) => {
  return service.delete(`/api/scanner/run/${runId}`)
}
