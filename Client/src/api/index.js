const BASE = '/api'

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  // Watchlist
  getStocks:    ()         => req('/watchlist/stocks'),
  addStock:     (data)     => req('/watchlist/stocks', { method: 'POST', body: JSON.stringify(data) }),
  removeStock:  (ticker)   => req(`/watchlist/stocks/${ticker}`, { method: 'DELETE' }),
  clearStocks:  ()         => req('/watchlist/stocks', { method: 'DELETE' }),
  seedFromNSE:  (index)    => req(`/watchlist/seed?index=${index}`, { method: 'POST' }),
  getSignals:  ()         => req('/watchlist/signals'),
  runAnalysis: (force = false) => req(`/watchlist/run${force ? '?force=true' : ''}`, { method: 'POST' }),
  runStatus:   ()              => req('/watchlist/run/status'),

  // Predictions
  predict:       (data)    => req('/predictions/predict', { method: 'POST', body: JSON.stringify(data) }),
  getHistory:    ({ ticker, limit } = {}) => {
    const p = new URLSearchParams()
    if (ticker) p.set('ticker', ticker)
    if (limit)  p.set('limit', limit)
    const qs = p.toString()
    return req(`/predictions/history${qs ? `?${qs}` : ''}`)
  },
  getAccuracy:   (ticker)  => req(`/predictions/accuracy${ticker ? `?ticker=${ticker}` : ''}`),
  recordOutcome: (data)    => req('/predictions/outcome', { method: 'POST', body: JSON.stringify(data) }),

  // Accuracy / backtest
  verifyPredictions: (date) => req(`/predictions/verify${date ? `?date=${date}` : ''}`, { method: 'POST' }),
  getBacktest:       (days) => req(`/predictions/backtest?days=${days || 14}`),

  // News
  getNews: (ticker, name) =>
    req(`/predictions/news/${ticker}${name ? `?name=${encodeURIComponent(name)}` : ''}`),

  // Settings
  getSettings:      ()       => req('/settings/'),
  updateSettings:   (data)   => req('/settings/', { method: 'PATCH', body: JSON.stringify(data) }),
  testWhatsApp:     ()       => req('/settings/test-whatsapp', { method: 'POST' }),
  sendReportNow:    ()       => req('/settings/send-report',   { method: 'POST' }),

  // Reports
  downloadPdfReport: (date) => {
    const url = `${BASE}/predictions/report.pdf${date ? `?date=${date}` : ''}`
    window.location.href = url
  },
}
