import { useEffect, useState } from 'react'
import {
  ResponsiveContainer, ComposedChart, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ReferenceLine, Cell, Legend,
} from 'recharts'
import { api } from '../api'

/* ── helpers ── */
function yesterday() {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toISOString().split('T')[0]
}

function fmtDate(str) {
  return new Date(str).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

/* ── Custom tooltip for comparison chart ── */
function CompareTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div style={{ background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: 8, padding: '10px 14px', fontSize: 12 }}>
      <p style={{ color: '#fff', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', marginBottom: 6 }}>{label}</p>
      <p style={{ color: '#9ca3af', margin: '2px 0' }}>Signal: <span style={{ color: d?.signal === 'bullish' ? '#22c55e' : d?.signal === 'bearish' ? '#ef4444' : '#9ca3af', fontWeight: 600 }}>{d?.signal}</span></p>
      <p style={{ color: '#9ca3af', margin: '2px 0' }}>Confidence: <span style={{ color: '#fff' }}>{d?.confidence}%</span></p>
      <p style={{ color: '#9ca3af', margin: '2px 0' }}>Predicted Δ: <span style={{ color: '#60a5fa' }}>{d?.predicted_chg_pct > 0 ? '+' : ''}{d?.predicted_chg_pct}%</span></p>
      <p style={{ color: '#9ca3af', margin: '2px 0' }}>Actual Δ: <span style={{ color: d?.is_correct ? '#22c55e' : '#ef4444', fontWeight: 600 }}>{d?.actual_chg_pct > 0 ? '+' : ''}{d?.actual_chg_pct}%</span></p>
      <p style={{ marginTop: 6, fontWeight: 600, color: d?.is_correct ? '#22c55e' : '#ef4444' }}>
        {d?.is_correct ? '✓ Correct' : '✗ Incorrect'}
      </p>
    </div>
  )
}

/* ── Accuracy trend tooltip ── */
function TrendTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div style={{ background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: 8, padding: '10px 14px', fontSize: 12 }}>
      <p style={{ color: '#fff', fontWeight: 600, marginBottom: 4 }}>{fmtDate(label)}</p>
      <p style={{ color: '#9ca3af', margin: '2px 0' }}>Accuracy: <span style={{ color: '#22c55e', fontWeight: 700 }}>{d?.accuracy_pct}%</span></p>
      <p style={{ color: '#9ca3af', margin: '2px 0' }}>{d?.correct}/{d?.total} correct</p>
    </div>
  )
}

/* ── Main page ── */
export default function Accuracy() {
  const [data,      setData]      = useState([])
  const [loading,   setLoading]   = useState(true)
  const [verifying, setVerifying] = useState(false)
  const [error,     setError]     = useState('')
  const [success,   setSuccess]   = useState('')
  const [days,      setDays]      = useState(14)
  const [selDate,   setSelDate]   = useState(null) // selected date for comparison chart

  const load = async () => {
    setLoading(true)
    try {
      const d = await api.getBacktest(days)
      setData(d)
      // Default selected date to the most recent date with data
      if (d.length && !selDate) {
        const dates = [...new Set(d.map(r => r.date))].sort().reverse()
        setSelDate(dates[0])
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [days])

  const handleVerify = async () => {
    setVerifying(true); setError(''); setSuccess('')
    try {
      const res = await api.verifyPredictions(yesterday())
      if (res.not_yet) {
        setError(`Can't verify yet — next trading day is ${res.next_trading_day} and market hasn't closed. Come back after 4 PM IST on ${res.next_trading_day}.`)
      } else if (res.already_done) {
        setSuccess(`Yesterday's predictions are already verified.`)
      } else {
        setSuccess(`Verified ${res.verified} predictions for ${res.date} using ${res.next_trading_day} actual closes.${res.errors ? ` (${res.errors} failed)` : ''}`)
        await load()
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setVerifying(false)
    }
  }

  // ── Derived data ──
  const dates = [...new Set(data.map(r => r.date))].sort().reverse()

  // Per-date accuracy for trend chart
  const trendData = dates.map(date => {
    const rows = data.filter(r => r.date === date)
    const correct = rows.filter(r => r.is_correct).length
    return {
      date,
      total:        rows.length,
      correct,
      accuracy_pct: rows.length ? Math.round(correct / rows.length * 100) : 0,
    }
  }).reverse() // chronological for the line chart

  // Comparison chart data for selected date
  const compareData = data
    .filter(r => r.date === selDate)
    .sort((a, b) => b.confidence - a.confidence)

  // Overall stats
  const totalVerified = data.length
  const totalCorrect  = data.filter(r => r.is_correct).length
  const overallAcc    = totalVerified ? Math.round(totalCorrect / totalVerified * 100) : null

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '28px 16px', display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 700, color: '#fff', margin: 0 }}>Accuracy & Backtest</h1>
          <p style={{ fontSize: 13, color: '#555', marginTop: 4 }}>
            How close were yesterday's predictions to actual market moves?
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* days selector */}
          {[7, 14, 30].map(d => (
            <button key={d} onClick={() => setDays(d)} style={{
              padding: '6px 12px', borderRadius: 8, fontSize: 12, fontWeight: 500, cursor: 'pointer',
              ...(days === d
                ? { background: '#fff', color: '#000', border: '1px solid #fff' }
                : { background: 'transparent', color: '#555', border: '1px solid #2a2a2a' })
            }}>
              {d}d
            </button>
          ))}
          <button
            onClick={handleVerify}
            disabled={verifying}
            style={{
              padding: '7px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
              background: '#16a34a', color: '#fff', border: 'none',
              cursor: verifying ? 'not-allowed' : 'pointer', opacity: verifying ? 0.7 : 1,
              display: 'flex', alignItems: 'center', gap: 8,
            }}
          >
            {verifying ? <><Spin /> Verifying…</> : '↻ Verify yesterday'}
          </button>
        </div>
      </div>

      {error   && <Banner text={error}   type="error" />}
      {success && <Banner text={success} type="success" />}

      {/* overall stat boxes */}
      {totalVerified > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 }}>
          <StatBox label="Predictions verified" value={totalVerified} color="#fff" />
          <StatBox label="Correct"              value={totalCorrect}  color="#22c55e" />
          <StatBox label={`Accuracy (${days}d)`} value={overallAcc != null ? `${overallAcc}%` : '—'} color="#38bdf8" />
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200, color: '#555', fontSize: 13 }}>
          <Spin /> <span style={{ marginLeft: 10 }}>Loading…</span>
        </div>
      ) : data.length === 0 ? (
        <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: 12, padding: '40px 24px', textAlign: 'center' }}>
          <p style={{ color: '#9ca3af', marginBottom: 8 }}>No verified predictions yet.</p>
          <p style={{ color: '#555', fontSize: 13 }}>
            Run analysis on a weekday, then click <strong style={{ color: '#fff' }}>↻ Verify yesterday</strong> the next day to auto-fetch actual closing prices.
          </p>
        </div>
      ) : (
        <>
          {/* ── Chart 1: Accuracy trend ── */}
          {trendData.length > 1 && (
            <Card title="Daily accuracy trend">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={trendData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                  <XAxis
                    dataKey="date"
                    tickFormatter={fmtDate}
                    tick={{ fill: '#555', fontSize: 11 }}
                    axisLine={false} tickLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tickFormatter={v => `${v}%`}
                    tick={{ fill: '#555', fontSize: 11 }}
                    axisLine={false} tickLine={false}
                    width={36}
                  />
                  <Tooltip content={<TrendTooltip />} />
                  <ReferenceLine y={50} stroke="#2a2a2a" strokeDasharray="4 4" />
                  <Line
                    type="monotone"
                    dataKey="accuracy_pct"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={{ fill: '#22c55e', r: 4, strokeWidth: 0 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
              <p style={{ fontSize: 11, color: '#555', marginTop: 8 }}>
                Dashed line = 50% baseline (random chance). Anything above = model has edge.
              </p>
            </Card>
          )}

          {/* ── Chart 2: Prediction vs Actual ── */}
          <Card
            title="Prediction vs actual move"
            right={
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {dates.map(d => (
                  <button key={d} onClick={() => setSelDate(d)} style={{
                    padding: '4px 10px', borderRadius: 6, fontSize: 11, cursor: 'pointer',
                    ...(selDate === d
                      ? { background: '#fff', color: '#000', border: '1px solid #fff' }
                      : { background: 'transparent', color: '#555', border: '1px solid #2a2a2a' })
                  }}>
                    {fmtDate(d)}
                  </button>
                ))}
              </div>
            }
          >
            {compareData.length === 0 ? (
              <p style={{ color: '#555', fontSize: 13, padding: '20px 0' }}>No data for this date.</p>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={compareData.length * 40 + 40}>
                  <ComposedChart
                    data={compareData}
                    layout="vertical"
                    margin={{ top: 0, right: 60, bottom: 0, left: 0 }}
                  >
                    <XAxis
                      type="number"
                      tickFormatter={v => `${v > 0 ? '+' : ''}${v}%`}
                      tick={{ fill: '#555', fontSize: 11 }}
                      axisLine={false} tickLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="ticker"
                      width={80}
                      tick={{ fill: '#9ca3af', fontSize: 12, fontFamily: 'JetBrains Mono, monospace' }}
                      axisLine={false} tickLine={false}
                    />
                    <Tooltip content={<CompareTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                    <ReferenceLine x={0} stroke="#333" />

                    {/* predicted change bar (faint blue) */}
                    <Bar dataKey="predicted_chg_pct" barSize={6} radius={[0, 3, 3, 0]} name="Predicted Δ%">
                      {compareData.map((_, i) => (
                        <Cell key={i} fill="rgba(96,165,250,0.35)" />
                      ))}
                    </Bar>

                    {/* actual change bar (bright, correct=green wrong=red) */}
                    <Bar dataKey="actual_chg_pct" barSize={10} radius={[0, 3, 3, 0]} name="Actual Δ%">
                      {compareData.map((entry, i) => (
                        <Cell
                          key={i}
                          fill={entry.is_correct ? '#22c55e' : '#ef4444'}
                          opacity={0.85}
                        />
                      ))}
                    </Bar>

                    <Legend
                      wrapperStyle={{ fontSize: 11, color: '#555', paddingTop: 12 }}
                      formatter={(v) => <span style={{ color: '#666' }}>{v}</span>}
                    />
                  </ComposedChart>
                </ResponsiveContainer>

                {/* Hit/miss summary row */}
                <div style={{ display: 'flex', gap: 20, marginTop: 16, flexWrap: 'wrap' }}>
                  {compareData.map(r => (
                    <div key={r.ticker} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                      <span style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: r.is_correct ? '#22c55e' : '#ef4444',
                        flexShrink: 0,
                      }} />
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', color: '#9ca3af' }}>{r.ticker}</span>
                      <span style={{ color: r.actual_chg_pct >= 0 ? '#22c55e' : '#ef4444' }}>
                        {r.actual_chg_pct > 0 ? '+' : ''}{r.actual_chg_pct}%
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>
        </>
      )}
    </div>
  )
}

/* ── small components ── */
function Card({ title, right, children }) {
  return (
    <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: 12, padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <p style={{ fontSize: 12, fontWeight: 600, color: '#555', textTransform: 'uppercase', letterSpacing: '0.07em', margin: 0 }}>
          {title}
        </p>
        {right}
      </div>
      {children}
    </div>
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

function Banner({ text, type }) {
  const err = type === 'error'
  return (
    <div style={{
      padding: '10px 14px', borderRadius: 8, fontSize: 13,
      background: err ? 'rgba(239,68,68,0.08)' : 'rgba(34,197,94,0.08)',
      border: `1px solid ${err ? 'rgba(239,68,68,0.2)' : 'rgba(34,197,94,0.2)'}`,
      color: err ? '#f87171' : '#4ade80',
    }}>
      {text}
    </div>
  )
}

function Spin() {
  return (
    <span style={{
      width: 13, height: 13, borderRadius: '50%', display: 'inline-block',
      border: '2px solid rgba(255,255,255,0.25)', borderTopColor: '#fff',
      animation: 'spin 0.7s linear infinite',
    }} />
  )
}
