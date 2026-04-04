import { useState } from 'react'
import { api } from '../api'
import SignalCard from '../components/SignalCard'

const EXCHANGES = ['NSE', 'BSE', 'NASDAQ', 'NYSE']
const SUFFIX = { NSE: '.NS', BSE: '.BO', NASDAQ: '', NYSE: '' }

const inputStyle = {
  width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid #2a2a2a',
  borderRadius: 8, padding: '10px 12px', color: '#fff', fontSize: 13,
  outline: 'none', fontFamily: 'inherit',
}
const labelStyle = { display: 'block', fontSize: 11, color: '#555', marginBottom: 6 }

export default function Predict() {
  const [form,    setForm]    = useState({ ticker: '', name: '', exchange: 'NSE' })
  const [result,  setResult]  = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  const handleSubmit = async e => {
    e.preventDefault()
    setLoading(true); setError(''); setResult(null)
    try {
      let ticker = form.ticker.trim().toUpperCase()
      const sfx = SUFFIX[form.exchange]
      if (sfx && !ticker.endsWith(sfx)) ticker += sfx
      const data = await api.predict({ ticker, name: form.name.trim(), exchange: form.exchange })
      setResult(data)
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '28px 16px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div>
        <h1 style={{ fontSize: 18, fontWeight: 700, color: '#fff', margin: 0 }}>Ad-hoc Prediction</h1>
        <p style={{ fontSize: 13, color: '#555', marginTop: 4 }}>Run a one-off analysis on any stock right now.</p>
      </div>

      <div style={{ background: '#111', border: '1px solid #1e1e1e', borderRadius: 12, padding: 24 }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <div>
              <label style={labelStyle}>Ticker symbol</label>
              <input
                value={form.ticker}
                onChange={e => setForm(f => ({ ...f, ticker: e.target.value }))}
                placeholder="INFY"
                required
                style={{ ...inputStyle, fontFamily: 'JetBrains Mono, monospace' }}
              />
            </div>
            <div>
              <label style={labelStyle}>Exchange</label>
              <select
                value={form.exchange}
                onChange={e => setForm(f => ({ ...f, exchange: e.target.value }))}
                style={inputStyle}
              >
                {EXCHANGES.map(ex => <option key={ex} value={ex}>{ex}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label style={labelStyle}>Company name</label>
            <input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Infosys"
              required
              style={inputStyle}
            />
          </div>

          {error && <p style={{ fontSize: 13, color: '#f87171', margin: 0 }}>{error}</p>}

          <button
            type="submit"
            disabled={loading}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              padding: '10px', background: '#16a34a', color: '#fff',
              fontWeight: 600, fontSize: 13, borderRadius: 8, border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? (
              <>
                <span style={{
                  width: 13, height: 13, borderRadius: '50%',
                  border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff',
                  animation: 'spin 0.7s linear infinite', display: 'inline-block',
                }} />
                Analysing…
              </>
            ) : '▶  Run Prediction'}
          </button>
        </form>
      </div>

      {result && (
        <div>
          <p style={{ fontSize: 11, color: '#555', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600, marginBottom: 10 }}>
            Result
          </p>
          <SignalCard prediction={result} />
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
