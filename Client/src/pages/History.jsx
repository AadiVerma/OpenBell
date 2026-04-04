import { useEffect, useState } from 'react'
import { api } from '../api'

const BADGE = {
  bullish: { bg: 'rgba(34,197,94,0.12)',   color: '#22c55e', border: 'rgba(34,197,94,0.3)'   },
  bearish: { bg: 'rgba(239,68,68,0.12)',   color: '#ef4444', border: 'rgba(239,68,68,0.3)'   },
  neutral: { bg: 'rgba(107,114,128,0.15)', color: '#9ca3af', border: 'rgba(107,114,128,0.3)' },
}
const BADGE_ICON = { bullish: '▲', bearish: '▼', neutral: '—' }

function fmt(n) {
  return n != null ? `₹${Number(n).toLocaleString('en-IN')}` : '—'
}

function OutcomeModal({ prediction, onClose, onSave }) {
  const [val, setVal] = useState('')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const handleSave = async () => {
    const n = parseFloat(val)
    if (isNaN(n) || n <= 0) { setErr('Enter a valid price'); return }
    setSaving(true)
    try { await onSave(prediction.id, n); onClose() }
    catch (e) { setErr(e.message); setSaving(false) }
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 50,
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 16px',
        background: 'rgba(0,0,0,0.78)', backdropFilter: 'blur(6px)',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{ background: '#111', border: '1px solid #222', borderRadius: 12, padding: 24, width: '100%', maxWidth: 360 }}
      >
        <h3 style={{ color: '#fff', fontWeight: 600, fontSize: 15, margin: '0 0 4px' }}>Record Outcome</h3>
        <p style={{ fontSize: 12, color: '#555', margin: '0 0 20px' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', color: '#fff' }}>{prediction.ticker}</span> · {prediction.date}
        </p>
        <label style={{ display: 'block', fontSize: 11, color: '#555', marginBottom: 6 }}>Actual closing price</label>
        <input
          type="number" step="0.01"
          value={val}
          onChange={e => setVal(e.target.value)}
          placeholder="0.00"
          style={{
            width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid #2a2a2a',
            borderRadius: 8, padding: '10px 12px', color: '#fff', fontSize: 13, outline: 'none',
            fontFamily: 'JetBrains Mono, monospace', marginBottom: 8, boxSizing: 'border-box',
          }}
        />
        {err && <p style={{ fontSize: 12, color: '#f87171', margin: '0 0 12px' }}>{err}</p>}
        <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
          <button onClick={onClose} style={{ flex: 1, padding: '9px', background: 'transparent', border: '1px solid #2a2a2a', color: '#666', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 500 }}>
            Cancel
          </button>
          <button onClick={handleSave} disabled={saving} style={{ flex: 1, padding: '9px', background: '#fff', color: '#000', border: 'none', borderRadius: 8, cursor: saving ? 'not-allowed' : 'pointer', fontSize: 13, fontWeight: 600, opacity: saving ? 0.6 : 1 }}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

const TH = ({ children, right }) => (
  <th style={{ padding: '10px 14px', fontSize: 11, fontWeight: 600, color: '#555', textTransform: 'uppercase', letterSpacing: '0.06em', textAlign: right ? 'right' : 'left', whiteSpace: 'nowrap' }}>
    {children}
  </th>
)

export default function History() {
  const [history,  setHistory]  = useState([])
  const [accuracy, setAccuracy] = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [modal,    setModal]    = useState(null)
  const [filter,   setFilter]   = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [hist, acc] = await Promise.all([api.getHistory({ limit: 100 }), api.getAccuracy()])
      setHistory(hist); setAccuracy(acc)
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const handleSave = async (id, actualClose) => {
    const item = history.find(h => h.id === id)
    await api.recordOutcome({ id, actual_close: actualClose, ticker: item?.ticker })
    await load()
  }

  const filtered = filter
    ? history.filter(h => h.ticker.toUpperCase().includes(filter.toUpperCase()))
    : history

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '28px 16px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h1 style={{ fontSize: 18, fontWeight: 700, color: '#fff', margin: 0 }}>History</h1>

      {/* accuracy cards */}
      {accuracy?.total >= 10 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 }}>
          <StatBox label="Total predictions" value={accuracy.total}          color="#fff" />
          <StatBox label="Correct"           value={accuracy.correct}        color="#22c55e" />
          <StatBox label="Accuracy"          value={`${accuracy.accuracy_pct}%`} color="#38bdf8" />
        </div>
      )}

      {error && (
        <div style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#f87171', borderRadius: 8, padding: '10px 14px', fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <input
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="Filter by ticker…"
          style={{
            background: 'rgba(255,255,255,0.04)', border: '1px solid #2a2a2a',
            borderRadius: 8, padding: '8px 12px', color: '#fff', fontSize: 12, outline: 'none',
            fontFamily: 'JetBrains Mono, monospace', width: 180,
          }}
        />
        {filter && (
          <button onClick={() => setFilter('')} style={{ fontSize: 12, color: '#555', background: 'none', border: 'none', cursor: 'pointer' }}>
            Clear
          </button>
        )}
        <span style={{ fontSize: 11, color: '#444', marginLeft: 'auto' }}>{filtered.length} record{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {/* table */}
      <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: 12, overflow: 'hidden' }}>
        {loading ? (
          <p style={{ padding: '32px', textAlign: 'center', color: '#555', fontSize: 13 }}>Loading…</p>
        ) : filtered.length === 0 ? (
          <p style={{ padding: '32px', textAlign: 'center', color: '#555', fontSize: 13 }}>No predictions found.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1e1e1e', background: '#0d0d0d' }}>
                  <TH>Ticker</TH>
                  <TH>Date</TH>
                  <TH>Signal</TH>
                  <TH right>Conf.</TH>
                  <TH right>Current</TH>
                  <TH right>Target</TH>
                  <TH right>Actual</TH>
                  <TH right>Result</TH>
                  <TH />
                </tr>
              </thead>
              <tbody>
                {filtered.map((p, i) => (
                  <HistoryRow key={p.id} p={p} last={i === filtered.length - 1} onRecord={() => setModal(p)} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modal && <OutcomeModal prediction={modal} onClose={() => setModal(null)} onSave={handleSave} />}
    </div>
  )
}

function HistoryRow({ p, last, onRecord }) {
  const [hovered, setHovered] = useState(false)
  const b = BADGE[p.signal] || BADGE.neutral
  return (
    <tr
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ background: hovered ? '#161616' : '#111', borderBottom: last ? 'none' : '1px solid #1a1a1a', transition: 'background 0.12s' }}
    >
      <td style={{ padding: '12px 14px', fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, fontSize: 12, color: '#fff', whiteSpace: 'nowrap' }}>
        {p.ticker.replace('.NS', '').replace('.BO', '')}
      </td>
      <td style={{ padding: '12px 14px', fontSize: 12, color: '#666' }}>{p.date}</td>
      <td style={{ padding: '12px 14px' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700, background: b.bg, color: b.color, border: `1px solid ${b.border}` }}>
          <span style={{ fontSize: 7 }}>{BADGE_ICON[p.signal]}</span>
          {p.signal}
        </span>
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#9ca3af' }}>{p.confidence}%</td>
      <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#9ca3af' }}>{fmt(p.current_price)}</td>
      <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#e5e7eb' }}>
        {fmt(p.target_low)}–{fmt(p.target_high)}
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#9ca3af' }}>
        {p.actual_close != null ? fmt(p.actual_close) : <span style={{ color: '#333' }}>—</span>}
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right' }}>
        {p.is_correct === true  && <span style={{ color: '#22c55e', fontSize: 14 }}>✓</span>}
        {p.is_correct === false && <span style={{ color: '#ef4444', fontSize: 14 }}>✗</span>}
        {p.is_correct == null   && <span style={{ color: '#333', fontSize: 12 }}>—</span>}
      </td>
      <td style={{ padding: '12px 14px', textAlign: 'right' }}>
        {p.actual_close == null && (
          <button
            onClick={onRecord}
            style={{ fontSize: 11, color: '#555', background: 'none', border: '1px solid #2a2a2a', padding: '4px 8px', borderRadius: 6, cursor: 'pointer' }}
            onMouseEnter={e => { e.currentTarget.style.color = '#fff'; e.currentTarget.style.borderColor = '#555' }}
            onMouseLeave={e => { e.currentTarget.style.color = '#555'; e.currentTarget.style.borderColor = '#2a2a2a' }}
          >
            Record
          </button>
        )}
      </td>
    </tr>
  )
}

function StatBox({ label, value, color }) {
  return (
    <div style={{ background: '#0f0f0f', border: '1px solid #1e1e1e', borderRadius: 10, padding: '12px 16px' }}>
      <p style={{ fontSize: 11, color: '#555', margin: 0, marginBottom: 6 }}>{label}</p>
      <p style={{ fontSize: 26, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color, margin: 0, lineHeight: 1 }}>
        {value}
      </p>
    </div>
  )
}
