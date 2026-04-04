import { useEffect, useState } from 'react'
import { api } from '../api'

const EXCHANGES = ['NSE', 'BSE', 'NASDAQ', 'NYSE']
const SUFFIX    = { NSE: '.NS', BSE: '.BO', NASDAQ: '', NYSE: '' }

const NSE_INDICES = [
  { key: 'NIFTY50',     label: 'NIFTY 50',      count: 50  },
  { key: 'NIFTYNEXT50', label: 'NIFTY Next 50',  count: 50  },
  { key: 'NIFTY100',    label: 'NIFTY 100',      count: 100 },
  { key: 'NIFTY200',    label: 'NIFTY 200',      count: 200 },
  { key: 'NIFTY500',    label: 'NIFTY 500',      count: 500 },
  { key: 'NIFTYIT',     label: 'NIFTY IT',       count: 10  },
  { key: 'NIFTYBANK',   label: 'NIFTY Bank',     count: 12  },
  { key: 'NIFTYREIT',   label: 'NIFTY REIT',     count: 7   },
]

const inputStyle = {
  width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid #2a2a2a',
  borderRadius: 8, padding: '10px 12px', color: '#fff', fontSize: 13,
  outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box',
}
const labelStyle = { display: 'block', fontSize: 11, color: '#555', marginBottom: 6 }

export default function Watchlist() {
  const [stocks,   setStocks]   = useState([])
  const [loading,  setLoading]  = useState(true)
  const [adding,   setAdding]   = useState(false)
  const [seeding,  setSeeding]  = useState(false)
  const [clearing, setClearing] = useState(false)
  const [error,    setError]    = useState('')
  const [success,  setSuccess]  = useState('')
  const [form,     setForm]     = useState({ ticker: '', name: '', exchange: 'NSE' })
  const [confirmClear, setConfirmClear] = useState(false)

  const load = async () => {
    try { setStocks(await api.getStocks()) }
    catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const flash = (msg, isError = false) => {
    if (isError) setError(msg); else setSuccess(msg)
    setTimeout(() => { setError(''); setSuccess('') }, 4000)
  }

  /* ── Add single stock ── */
  const handleAdd = async e => {
    e.preventDefault()
    setAdding(true); setError(''); setSuccess('')
    try {
      let ticker = form.ticker.trim().toUpperCase()
      const sfx = SUFFIX[form.exchange]
      if (sfx && !ticker.endsWith(sfx)) ticker += sfx
      await api.addStock({ ticker, name: form.name.trim(), exchange: form.exchange })
      flash(`${ticker} added`)
      setForm({ ticker: '', name: '', exchange: 'NSE' })
      await load()
    } catch (e) { flash(e.message, true) } finally { setAdding(false) }
  }

  /* ── Seed from NSE ── */
  const handleSeed = async (indexKey) => {
    setSeeding(true); setError(''); setSuccess('')
    try {
      const res = await api.seedFromNSE(indexKey)
      flash(`${res.added} stocks added from ${indexKey} (${res.skipped} already present)`)
      await load()
    } catch (e) { flash(e.message, true) } finally { setSeeding(false) }
  }

  /* ── Remove single stock ── */
  const handleRemove = async ticker => {
    setError('')
    try {
      await api.removeStock(ticker)
      setStocks(prev => prev.filter(s => s.ticker !== ticker))
    } catch (e) { flash(e.message, true) }
  }

  /* ── Clear all ── */
  const handleClearAll = async () => {
    setClearing(true); setConfirmClear(false)
    try {
      await api.clearStocks()
      flash('Watchlist cleared')
      setStocks([])
    } catch (e) { flash(e.message, true) } finally { setClearing(false) }
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '28px 16px', display: 'flex', flexDirection: 'column', gap: 24 }}>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: 18, fontWeight: 700, color: '#fff', margin: 0 }}>Watchlist</h1>
        {stocks.length > 0 && (
          <span style={{ fontSize: 12, color: '#555' }}>{stocks.length} stock{stocks.length !== 1 ? 's' : ''}</span>
        )}
      </div>

      {error   && <Banner text={error}   type="error" />}
      {success && <Banner text={success} type="success" />}

      {/* ── Seed from NSE Index ── */}
      <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: 12, padding: 20 }}>
        <div style={{ marginBottom: 14 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: '#e5e7eb', margin: '0 0 4px' }}>
            Load from NSE Index
          </p>
          <p style={{ fontSize: 12, color: '#555', margin: 0 }}>
            Fetch live constituent list from NSE archives. Falls back to hardcoded list if NSE is unreachable.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8 }}>
          {NSE_INDICES.map(idx => (
            <button
              key={idx.key}
              onClick={() => handleSeed(idx.key)}
              disabled={seeding}
              style={{
                padding: '9px 10px', borderRadius: 8, fontSize: 12, fontWeight: 500,
                background: 'rgba(255,255,255,0.04)', border: '1px solid #2a2a2a',
                color: seeding ? '#444' : '#ccc', cursor: seeding ? 'not-allowed' : 'pointer',
                textAlign: 'left', transition: 'all 0.15s',
              }}
              onMouseEnter={e => { if (!seeding) { e.currentTarget.style.borderColor = '#22c55e'; e.currentTarget.style.color = '#22c55e' }}}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2a2a'; e.currentTarget.style.color = seeding ? '#444' : '#ccc' }}
            >
              <div style={{ fontWeight: 600 }}>{idx.label}</div>
              <div style={{ fontSize: 10, color: '#555', marginTop: 2 }}>~{idx.count} stocks</div>
            </button>
          ))}
        </div>

        {seeding && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, fontSize: 12, color: '#555' }}>
            <Spinner /> Fetching from NSE…
          </div>
        )}
      </div>

      {/* ── Add single stock ── */}
      <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: 12, padding: 20 }}>
        <p style={{ fontSize: 11, fontWeight: 600, color: '#555', textTransform: 'uppercase', letterSpacing: '0.07em', margin: '0 0 16px' }}>
          Add single stock
        </p>
        <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Ticker symbol</label>
              <input
                value={form.ticker}
                onChange={e => setForm(f => ({ ...f, ticker: e.target.value }))}
                placeholder="RELIANCE"
                required
                style={{ ...inputStyle, fontFamily: 'JetBrains Mono, monospace' }}
              />
            </div>
            <div>
              <label style={labelStyle}>Exchange</label>
              <select value={form.exchange} onChange={e => setForm(f => ({ ...f, exchange: e.target.value }))} style={inputStyle}>
                {EXCHANGES.map(ex => <option key={ex} value={ex}>{ex}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label style={labelStyle}>Company name</label>
            <input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Reliance Industries"
              required
              style={inputStyle}
            />
          </div>
          <button
            type="submit"
            disabled={adding}
            style={{
              padding: '9px', background: '#fff', color: '#000', fontWeight: 600,
              fontSize: 13, borderRadius: 8, border: 'none',
              cursor: adding ? 'not-allowed' : 'pointer', opacity: adding ? 0.6 : 1,
            }}
          >
            {adding ? 'Adding…' : '+ Add to Watchlist'}
          </button>
        </form>
      </div>

      {/* ── Stock list ── */}
      <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: 12, overflow: 'hidden' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px', borderBottom: '1px solid #1a1a1a' }}>
          <p style={{ fontSize: 11, fontWeight: 600, color: '#555', textTransform: 'uppercase', letterSpacing: '0.07em', margin: 0 }}>
            Tracking · {stocks.length} stock{stocks.length !== 1 ? 's' : ''}
          </p>
          {stocks.length > 0 && (
            confirmClear ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 12, color: '#9ca3af' }}>Remove all?</span>
                <button onClick={handleClearAll} disabled={clearing} style={{ fontSize: 12, color: '#f87171', background: 'none', border: '1px solid rgba(248,113,113,0.3)', padding: '3px 10px', borderRadius: 6, cursor: 'pointer' }}>
                  {clearing ? 'Clearing…' : 'Yes, clear'}
                </button>
                <button onClick={() => setConfirmClear(false)} style={{ fontSize: 12, color: '#555', background: 'none', border: 'none', cursor: 'pointer' }}>
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmClear(true)}
                style={{ fontSize: 12, color: '#555', background: 'none', border: 'none', cursor: 'pointer' }}
                onMouseEnter={e => e.currentTarget.style.color = '#f87171'}
                onMouseLeave={e => e.currentTarget.style.color = '#555'}
              >
                Clear all
              </button>
            )
          )}
        </div>

        {loading ? (
          <p style={{ padding: '32px 20px', textAlign: 'center', color: '#555', fontSize: 13 }}>Loading…</p>
        ) : stocks.length === 0 ? (
          <p style={{ padding: '32px 20px', textAlign: 'center', color: '#555', fontSize: 13 }}>
            No stocks yet. Load an NSE index above or add manually.
          </p>
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, maxHeight: 480, overflowY: 'auto' }}>
            {stocks.map((s, i) => (
              <StockRow key={s.ticker} s={s} last={i === stocks.length - 1} onRemove={() => handleRemove(s.ticker)} />
            ))}
          </ul>
        )}
      </div>

    </div>
  )
}

function StockRow({ s, last, onRemove }) {
  const [hovered, setHovered] = useState(false)
  return (
    <li
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '11px 20px',
        background: hovered ? '#161616' : '#111',
        borderBottom: last ? 'none' : '1px solid #1a1a1a',
        transition: 'background 0.12s',
      }}
    >
      <div>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#fff', fontFamily: 'JetBrains Mono, monospace' }}>{s.ticker}</span>
        <span style={{ fontSize: 11, color: '#555', marginLeft: 10 }}>{s.name} · {s.exchange}</span>
      </div>
      <button
        onClick={onRemove}
        style={{ fontSize: 12, color: '#444', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px', borderRadius: 6 }}
        onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
        onMouseLeave={e => e.currentTarget.style.color = '#444'}
      >
        Remove
      </button>
    </li>
  )
}

function Banner({ text, type }) {
  const isErr = type === 'error'
  return (
    <div style={{
      padding: '10px 14px', borderRadius: 8, fontSize: 13,
      background: isErr ? 'rgba(239,68,68,0.08)' : 'rgba(34,197,94,0.08)',
      border: `1px solid ${isErr ? 'rgba(239,68,68,0.2)' : 'rgba(34,197,94,0.2)'}`,
      color: isErr ? '#f87171' : '#4ade80',
    }}>
      {text}
    </div>
  )
}

function Spinner() {
  return (
    <span style={{
      width: 12, height: 12, borderRadius: '50%',
      border: '2px solid #333', borderTopColor: '#22c55e',
      animation: 'spin 0.7s linear infinite', display: 'inline-block',
    }} />
  )
}
