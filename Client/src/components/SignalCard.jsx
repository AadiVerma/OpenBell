/* Detail prediction card — matches screenshot layout */

const SIGNAL_STYLE = {
  bullish: { color: '#86efac', badgeBg: 'rgba(134,239,172,0.12)', badgeBorder: 'rgba(134,239,172,0.35)', icon: '▲', label: 'Bullish' },
  bearish: { color: '#fca5a5', badgeBg: 'rgba(252,165,165,0.12)', badgeBorder: 'rgba(252,165,165,0.35)', icon: '▼', label: 'Bearish' },
  neutral: { color: '#d1d5db', badgeBg: 'rgba(209,213,219,0.10)', badgeBorder: 'rgba(209,213,219,0.25)', icon: '—', label: 'Neutral' },
}

const FACTOR_DOT = { bullish: '#22c55e', bearish: '#ef4444', risk: '#ef4444', neutral: '#9ca3af' }
const FACTOR_BADGE = {
  bullish: { color: '#86efac', border: 'rgba(134,239,172,0.4)', bg: 'rgba(134,239,172,0.08)' },
  bearish: { color: '#fca5a5', border: 'rgba(252,165,165,0.4)', bg: 'rgba(252,165,165,0.08)' },
  risk:    { color: '#fca5a5', border: 'rgba(252,165,165,0.4)', bg: 'rgba(252,165,165,0.08)' },
  neutral: { color: '#d1d5db', border: 'rgba(209,213,219,0.3)', bg: 'rgba(209,213,219,0.07)' },
}

function fmt(n) {
  return n != null ? `₹${Number(n).toLocaleString('en-IN')}` : '—'
}

function fmtGenerated(dateStr) {
  if (!dateStr) return null
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Kolkata',
    }) + ' IST'
  } catch { return dateStr }
}

const BG      = '#252520'
const STAT_BG = '#1c1c18'
const BORDER  = 'rgba(255,255,255,0.07)'

export default function SignalCard({ prediction }) {
  const {
    signal, confidence, ticker, name, exchange,
    predicted_direction, target_low, target_high,
    current_price, reasoning, factors, generated_at,
  } = prediction

  const s = SIGNAL_STYLE[signal] || SIGNAL_STYLE.neutral

  const directionColor =
    predicted_direction === 'up'   ? '#86efac' :
    predicted_direction === 'down' ? '#fca5a5' : '#d1d5db'
  const directionIcon =
    predicted_direction === 'up' ? '▲' : predicted_direction === 'down' ? '▼' : '→'

  return (
    <div style={{
      background: BG,
      border: `1px solid ${BORDER}`,
      borderRadius: 16,
      overflow: 'hidden',
      fontFamily: 'Inter, system-ui, sans-serif',
    }}>

      {/* ── Header ── */}
      <div style={{ padding: '22px 24px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: '#fff', margin: 0, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '-0.01em' }}>
            {ticker}
          </h2>
          <p style={{ fontSize: 13, color: '#888', margin: '4px 0 0' }}>
            {name}{exchange ? ` · ${exchange}` : ''}
          </p>
        </div>
        {/* Signal pill */}
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '7px 14px', borderRadius: 20,
          background: s.badgeBg, border: `1px solid ${s.badgeBorder}`,
          fontSize: 13, fontWeight: 600, color: s.color,
        }}>
          <span style={{ fontSize: 9 }}>{s.icon}</span>
          {s.label}
        </span>
      </div>

      {/* ── Three stat boxes ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, padding: '0 24px' }}>
        <StatBox label="Today's close"      value={fmt(current_price)} />
        <StatBox
          label="Predicted direction"
          value={
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: directionColor, fontSize: 20, fontWeight: 700 }}>
              <span style={{ fontSize: 12 }}>{directionIcon}</span>
              {predicted_direction ? predicted_direction.charAt(0).toUpperCase() + predicted_direction.slice(1) : '—'}
            </span>
          }
          raw
        />
        <StatBox label="Target range" value={target_low != null && target_high != null ? `${fmt(target_low)}–${fmt(target_high)}` : '—'} />
      </div>

      {/* ── Confidence bar ── */}
      <div style={{ padding: '20px 24px 0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ fontSize: 13, color: '#aaa', fontWeight: 500 }}>Confidence</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#fff', fontFamily: 'JetBrains Mono, monospace' }}>{confidence}%</span>
        </div>
        <div style={{ height: 8, background: 'rgba(255,255,255,0.07)', borderRadius: 4, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${confidence}%`,
            background: confidence >= 60 ? '#4ade80' : confidence >= 40 ? '#fb923c' : '#f87171',
            borderRadius: 4,
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5, fontSize: 11, color: '#555' }}>
          <span>Low</span><span>Medium</span><span>High</span>
        </div>
      </div>

      {/* ── LLM reasoning ── */}
      {reasoning && (
        <div style={{ padding: '20px 24px 0' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb', margin: '0 0 10px' }}>LLM reasoning</h3>
          <div style={{
            background: '#1a1a16', border: `1px solid ${BORDER}`,
            borderRadius: 10, padding: '14px 16px',
          }}>
            <p style={{ fontSize: 13, color: '#9ca3af', lineHeight: 1.65, margin: 0 }}>{reasoning}</p>
          </div>
        </div>
      )}

      {/* ── Signal factors ── */}
      {factors?.length > 0 && (
        <div style={{ padding: '20px 24px 0' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#e5e7eb', margin: '0 0 4px' }}>Signal factors</h3>
          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 10, overflow: 'hidden', marginTop: 10 }}>
            {factors.map((f, i) => {
              const dot = FACTOR_DOT[f.type] || '#9ca3af'
              const fb  = FACTOR_BADGE[f.type] || FACTOR_BADGE.neutral
              const label = f.type ? f.type.charAt(0).toUpperCase() + f.type.slice(1) : 'Note'
              return (
                <div
                  key={i}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '13px 16px',
                    borderBottom: i < factors.length - 1 ? `1px solid rgba(255,255,255,0.05)` : 'none',
                  }}
                >
                  {/* dot */}
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: dot, flexShrink: 0 }} />
                  {/* badge */}
                  <span style={{
                    fontSize: 11, fontWeight: 600, padding: '3px 9px', borderRadius: 6,
                    background: fb.bg, color: fb.color, border: `1px solid ${fb.border}`,
                    flexShrink: 0,
                  }}>
                    {label}
                  </span>
                  {/* text */}
                  <span style={{ fontSize: 13, color: '#ccc' }}>{f.text}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Metadata footer ── */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8,
        padding: '16px 24px', marginTop: 20,
        borderTop: `1px solid ${BORDER}`,
        fontSize: 12, color: '#555',
      }}>
        <span>Generated: {fmtGenerated(generated_at) || '—'}</span>
        <span>Model: claude-opus-4-6</span>
        <span>Data lag: 0 min</span>
      </div>

      {/* ── Disclaimer ── */}
      <div style={{
        margin: '0 24px 20px',
        padding: '10px 14px',
        background: 'rgba(234,179,8,0.07)',
        borderLeft: '3px solid rgba(234,179,8,0.5)',
        borderRadius: '0 6px 6px 0',
        fontSize: 12, color: 'rgba(234,179,8,0.75)',
        lineHeight: 1.5,
      }}>
        This is an AI-generated signal, not financial advice. Always do your own research before trading.
      </div>

    </div>
  )
}

function StatBox({ label, value, raw }) {
  return (
    <div style={{
      background: STAT_BG,
      border: `1px solid ${BORDER}`,
      borderRadius: 10,
      padding: '14px 16px',
    }}>
      <p style={{ fontSize: 12, color: '#777', margin: '0 0 6px' }}>{label}</p>
      {raw ? value : (
        <p style={{ fontSize: 20, fontWeight: 700, color: '#fff', margin: 0, fontFamily: 'JetBrains Mono, monospace' }}>
          {value}
        </p>
      )}
    </div>
  )
}
