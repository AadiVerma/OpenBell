import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import SignalCard from '../components/SignalCard'

/* ── small helpers ── */
function fmtTime() {
  return new Date().toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Kolkata',
  }) + ' IST'
}
function fmtDate() {
  return new Date().toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'short', year: 'numeric',
  })
}
function fmt(n) {
  return n != null ? `₹${Number(n).toLocaleString('en-IN')}` : '—'
}

/* ── segmented confidence bar ── */
function ConfBar({ value, signal }) {
  const filled = Math.round((value / 100) * 5)
  const color =
    signal === 'bullish' ? '#22c55e' :
    signal === 'bearish' ? '#ef4444' : '#6b7280'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      {[1,2,3,4,5].map(i => (
        <div
          key={i}
          style={{
            width: 18, height: 7, borderRadius: 2,
            backgroundColor: i <= filled ? color : 'rgba(255,255,255,0.08)',
          }}
        />
      ))}
      <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: '#9ca3af', marginLeft: 4, minWidth: 32 }}>
        {value}%
      </span>
    </div>
  )
}

/* ── signal badge ── */
const BADGE = {
  bullish: { bg: 'rgba(34,197,94,0.12)',   color: '#22c55e', border: 'rgba(34,197,94,0.3)',   icon: '▲' },
  bearish: { bg: 'rgba(239,68,68,0.12)',   color: '#ef4444', border: 'rgba(239,68,68,0.3)',   icon: '▼' },
  neutral: { bg: 'rgba(107,114,128,0.15)', color: '#9ca3af', border: 'rgba(107,114,128,0.3)', icon: '—' },
}
function SignalBadge({ signal }) {
  const s = BADGE[signal] || BADGE.neutral
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
      background: s.bg, color: s.color, border: `1px solid ${s.border}`,
    }}>
      <span style={{ fontSize: 8 }}>{s.icon}</span>
      {signal.charAt(0).toUpperCase() + signal.slice(1)}
    </span>
  )
}

/* ── detail modal ── */
function DetailModal({ prediction, onClose }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 50,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '0 16px',
        background: 'rgba(0,0,0,0.78)', backdropFilter: 'blur(6px)',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{ width: '100%', maxWidth: 680, maxHeight: '90vh', overflowY: 'auto' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 11, color: '#555', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Signal detail
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255,255,255,0.06)', border: '1px solid #2a2a2a',
              color: '#666', width: 28, height: 28, borderRadius: 6,
              fontSize: 18, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            ×
          </button>
        </div>
        <SignalCard prediction={prediction} />
      </div>
    </div>
  )
}

/* ── filter tabs ── */
const FILTERS = [
  { id: 'all',     label: 'All' },
  { id: 'bullish', label: 'Bullish only' },
  { id: 'bearish', label: 'Bearish only' },
  { id: 'high',    label: 'High confidence 70%+' },
]

/* shared grid template */
const COLS = '2rem 1fr 110px 175px 90px 115px 110px'

/* ── page ── */
export default function Dashboard() {
  const [signals,  setSignals]  = useState([])
  const [accuracy, setAccuracy] = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [filter,   setFilter]   = useState('all')
  const [search,   setSearch]   = useState('')
  const [selected, setSelected] = useState(null)
  const [jobStatus, setJobStatus] = useState(null) // null | {running, total, processed, skipped, errors, current}
  const pollRef = useRef(null)

  const loadSignals = async () => {
    try {
      const [sigs, acc] = await Promise.all([api.getSignals(), api.getAccuracy()])
      setSignals(sigs)
      setAccuracy(acc)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadSignals() }, [])

  // Poll job status while running
  const startPolling = () => {
    if (pollRef.current) return
    pollRef.current = setInterval(async () => {
      try {
        const s = await api.runStatus()
        setJobStatus(s)
        // Refresh signals as each stock finishes
        await loadSignals()
        if (!s.running) {
          clearInterval(pollRef.current)
          pollRef.current = null
          // Keep the completed status visible for 3s then clear
          setTimeout(() => setJobStatus(null), 3000)
        }
      } catch { /* ignore poll errors */ }
    }, 3000)
  }

  useEffect(() => () => clearInterval(pollRef.current), [])

  const handleRun = async (force = false) => {
    setError('')
    try {
      await api.runAnalysis(force)
      // Immediately show "running" state by fetching status once
      const s = await api.runStatus()
      setJobStatus(s)
      startPolling()
    } catch (e) {
      setError(e.message)
    }
  }

  const counts = { bullish: 0, bearish: 0, neutral: 0 }
  signals.forEach(s => { if (counts[s.signal] != null) counts[s.signal]++ })
  const avgConf = signals.length
    ? Math.round(signals.reduce((a, s) => a + s.confidence, 0) / signals.length)
    : null

  const q = search.trim().toLowerCase()
  const visible = signals.filter(s => {
    if (filter === 'bullish' && s.signal !== 'bullish') return false
    if (filter === 'bearish' && s.signal !== 'bearish') return false
    if (filter === 'high'    && s.confidence < 70)      return false
    if (q && !s.ticker.toLowerCase().includes(q) && !s.name?.toLowerCase().includes(q)) return false
    return true
  })

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '28px 16px 40px' }}>

      {/* header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16, marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 700, color: '#fff', margin: 0 }}>Evening signal sheet</h1>
          <p style={{ fontSize: 13, color: '#555', marginTop: 4 }}>
            {fmtDate()} · {fmtTime()}
            {signals.length > 0 && <span style={{ color: '#444' }}> · {signals.length} stocks analysed</span>}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Excel download button */}
          {signals.length > 0 && (
            <a
              href="/api/predictions/report.xlsx"
              download
              title="Download Excel report"
              style={{
                padding: '7px 12px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                background: 'transparent', color: '#22c55e', border: '1px solid #166534',
                cursor: 'pointer', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 5,
              }}
            >
              ⬇ Excel
            </a>
          )}
          {/* Force re-run button */}
          {!jobStatus?.running && signals.length > 0 && (
            <button
              onClick={() => handleRun(true)}
              title="Re-run and overwrite today's predictions"
              style={{
                padding: '7px 12px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                background: 'transparent', color: '#555', border: '1px solid #2a2a2a',
                cursor: 'pointer',
              }}
            >
              ↺ Force re-run
            </button>
          )}
          <button
            onClick={() => handleRun(false)}
            disabled={!!jobStatus?.running}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '7px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
              background: '#16a34a', color: '#fff', border: 'none',
              cursor: jobStatus?.running ? 'not-allowed' : 'pointer',
              opacity: jobStatus?.running ? 0.7 : 1,
            }}
          >
            {jobStatus?.running ? (
              <>
                <span style={{
                  width: 13, height: 13, borderRadius: '50%',
                  border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff',
                  animation: 'spin 0.7s linear infinite', display: 'inline-block',
                }} />
                Analysing…
              </>
            ) : 'Run Analysis'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171', borderRadius: 8, padding: '10px 14px', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* ── Live analysis progress ── */}
      {jobStatus?.running && (
        <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: 10, padding: '14px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontSize: 13, color: '#aaa', fontWeight: 500 }}>
              Analysing watchlist
              {jobStatus.current && (
                <span style={{ color: '#555', marginLeft: 6, fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
                  · {jobStatus.current}
                </span>
              )}
            </span>
            <span style={{ fontSize: 12, color: '#555', fontFamily: 'JetBrains Mono, monospace' }}>
              {jobStatus.processed + jobStatus.skipped + jobStatus.errors} / {jobStatus.total || '?'}
            </span>
          </div>
          {/* progress bar */}
          <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 2,
              background: 'linear-gradient(90deg, #22c55e, #4ade80)',
              width: jobStatus.total
                ? `${Math.round(((jobStatus.processed + jobStatus.skipped + jobStatus.errors) / jobStatus.total) * 100)}%`
                : '0%',
              transition: 'width 0.4s ease',
            }} />
          </div>
          <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 11, color: '#555' }}>
            <span style={{ color: '#22c55e' }}>✓ {jobStatus.processed} done</span>
            {jobStatus.skipped > 0 && <span>⟳ {jobStatus.skipped} skipped</span>}
            {jobStatus.errors > 0  && <span style={{ color: '#f87171' }}>✗ {jobStatus.errors} errors</span>}
          </div>
        </div>
      )}

      {/* summary stats */}
      {signals.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 20 }}>
          <StatBox label="Bullish signals" value={counts.bullish} color="#22c55e" />
          <StatBox label="Bearish signals" value={counts.bearish} color="#ef4444" />
          <StatBox label="Neutral"         value={counts.neutral} color="#9ca3af" />
          <StatBox label="Avg confidence"  value={avgConf != null ? `${avgConf}%` : '—'} color="#fff" large />
        </div>
      )}

      {/* accuracy */}
      {accuracy?.total >= 10 && (
        <p style={{ fontSize: 12, color: '#555', marginBottom: 16 }}>
          Model accuracy{' '}
          <span style={{ color: '#fff', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>{accuracy.accuracy_pct}%</span>
          <span style={{ color: '#444', marginLeft: 4 }}>({accuracy.correct}/{accuracy.total} correct)</span>
        </p>
      )}

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 180, color: '#555', fontSize: 13 }}>
          <span style={{
            width: 18, height: 18, borderRadius: '50%',
            border: '2px solid #333', borderTopColor: '#777',
            animation: 'spin 0.7s linear infinite', display: 'inline-block', marginRight: 10,
          }} />
          Loading…
        </div>
      ) : signals.length === 0 ? (
        <div style={{ background: '#111', border: '1px solid #222', borderRadius: 12, padding: '40px 24px', textAlign: 'center' }}>
          <p style={{ color: '#9ca3af', marginBottom: 8 }}>No signals for today yet.</p>
          <p style={{ color: '#555', fontSize: 13 }}>Add stocks to your watchlist, then click <strong style={{ color: '#fff' }}>Run Analysis</strong>.</p>
        </div>
      ) : (
        <>
          {/* filter tabs + search */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10, marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {FILTERS.map(f => (
                <button
                  key={f.id}
                  onClick={() => setFilter(f.id)}
                  style={{
                    padding: '6px 14px', borderRadius: 8, fontSize: 13, fontWeight: 500,
                    cursor: 'pointer', transition: 'all 0.15s',
                    ...(filter === f.id
                      ? { background: '#fff', color: '#000', border: '1px solid #fff' }
                      : { background: 'transparent', color: '#6b7280', border: '1px solid #2a2a2a' }
                    ),
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', fontSize: 12, color: '#444', pointerEvents: 'none' }}>⌕</span>
              <input
                type="text"
                placeholder="Search ticker or name…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{
                  paddingLeft: 28, paddingRight: search ? 28 : 12, paddingTop: 6, paddingBottom: 6,
                  borderRadius: 8, fontSize: 13, width: 200,
                  background: 'transparent', color: '#e5e7eb',
                  border: '1px solid #2a2a2a', outline: 'none',
                  fontFamily: 'inherit',
                }}
              />
              {search && (
                <button
                  onClick={() => setSearch('')}
                  style={{
                    position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', color: '#555', cursor: 'pointer',
                    fontSize: 14, lineHeight: 1, padding: 0,
                  }}
                >×</button>
              )}
            </div>
          </div>

          {/* table */}
          <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: 12, overflow: 'hidden' }}>

            {/* header row */}
            <div style={{
              display: 'grid', gridTemplateColumns: COLS, gap: '0 12px',
              padding: '10px 20px', background: '#0d0d0d', borderBottom: '1px solid #1e1e1e',
              fontSize: 11, fontWeight: 600, color: '#555', textTransform: 'uppercase', letterSpacing: '0.06em',
            }}>
              <span>#</span>
              <span>Stock</span>
              <span>Signal</span>
              <span>Confidence</span>
              <span style={{ textAlign: 'right' }}>Today close</span>
              <span style={{ textAlign: 'right' }}>Limit order</span>
              <span style={{ textAlign: 'right' }}>Target</span>
            </div>

            {visible.length === 0 ? (
              <div style={{ padding: '32px 20px', textAlign: 'center', color: '#555', fontSize: 13 }}>
                {q ? `No signals match "${search}".` : 'No signals match this filter.'}
              </div>
            ) : (
              visible.map((s, i) => (
                <SignalRow
                  key={s.id}
                  s={s}
                  rank={i + 1}
                  last={i === visible.length - 1}
                  onClick={() => setSelected(s)}
                />
              ))
            )}
          </div>
        </>
      )}


      {selected && <DetailModal prediction={selected} onClose={() => setSelected(null)} />}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}

function SignalRow({ s, rank, last, onClick }) {
  const [hovered, setHovered] = useState(false)
  const accentColor =
    s.signal === 'bullish' ? '#22c55e' :
    s.signal === 'bearish' ? '#ef4444' : 'transparent'

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'grid', gridTemplateColumns: COLS, gap: '0 12px',
        padding: '13px 20px', alignItems: 'center',
        background: hovered ? '#161616' : '#111',
        borderBottom: last ? 'none' : '1px solid #1a1a1a',
        borderLeft: `3px solid ${accentColor}`,
        cursor: 'pointer', transition: 'background 0.12s',
      }}
    >
      {/* rank */}
      <span style={{ fontSize: 12, color: '#444', fontFamily: 'JetBrains Mono, monospace' }}>{rank}</span>

      {/* stock */}
      <div>
        <p style={{ fontSize: 13, fontWeight: 700, color: '#fff', fontFamily: 'JetBrains Mono, monospace', margin: 0, lineHeight: 1.2 }}>
          {s.ticker}
        </p>
        <p style={{ fontSize: 11, color: '#555', margin: 0, marginTop: 2 }}>{s.name}</p>
      </div>

      {/* signal */}
      <SignalBadge signal={s.signal} />

      {/* confidence */}
      <ConfBar value={s.confidence} signal={s.signal} />

      {/* today close */}
      <p style={{ textAlign: 'right', fontSize: 13, fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: '#e5e7eb', margin: 0 }}>
        {fmt(s.current_price)}
      </p>

      {/* limit order */}
      <div style={{ textAlign: 'right' }}>
        <p style={{ fontSize: 13, fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: '#38bdf8', margin: 0 }}>
          {fmt(s.limit_price)}
        </p>
        {s.limit_price != null && <p style={{ fontSize: 10, color: '#444', margin: 0, marginTop: 2 }}>limit price</p>}
      </div>

      {/* target */}
      <div style={{ textAlign: 'right' }}>
        <p style={{ fontSize: 13, fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', color: s.target_high != null ? '#e5e7eb' : '#333', margin: 0 }}>
          {s.target_high != null ? fmt(s.target_high) : '—'}
        </p>
        {s.target_high != null && <p style={{ fontSize: 10, color: '#444', margin: 0, marginTop: 2 }}>target</p>}
      </div>
    </div>
  )
}

function StatBox({ label, value, color, large }) {
  return (
    <div style={{ background: '#0f0f0f', border: '1px solid #1e1e1e', borderRadius: 10, padding: '12px 16px' }}>
      <p style={{ fontSize: 11, color: '#555', margin: 0, marginBottom: 6 }}>{label}</p>
      <p style={{ fontSize: large ? 28 : 26, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color, margin: 0, lineHeight: 1 }}>
        {value}
      </p>
    </div>
  )
}
