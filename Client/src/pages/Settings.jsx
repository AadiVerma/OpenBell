import { useEffect, useState } from 'react'
import { api } from '../api'

const S = {
  page:    { maxWidth: 720, margin: '0 auto', padding: '32px 16px' },
  card:    { background: '#161616', border: '1px solid #222', borderRadius: 12, padding: 24, marginBottom: 20 },
  heading: { fontSize: 13, fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 16 },
  label:   { fontSize: 12, color: '#6b7280', marginBottom: 6, display: 'block' },
  input:   {
    width: '100%', background: '#0d0d0d', border: '1px solid #333', borderRadius: 8,
    color: '#e5e7eb', fontSize: 13, padding: '9px 12px', outline: 'none', boxSizing: 'border-box',
    fontFamily: 'JetBrains Mono, monospace',
  },
  row:     { display: 'flex', gap: 12, marginBottom: 14 },
  col:     { flex: 1 },
  btn:     (variant = 'primary') => ({
    padding: '9px 18px', borderRadius: 8, fontSize: 13, fontWeight: 600,
    cursor: 'pointer', border: 'none', transition: 'opacity 0.15s',
    background: variant === 'primary' ? '#22c55e' : variant === 'danger' ? '#ef4444' : '#333',
    color: variant === 'ghost' ? '#9ca3af' : '#fff',
  }),
  toggle:  (on) => ({
    width: 44, height: 24, borderRadius: 12, border: 'none', cursor: 'pointer',
    background: on ? '#22c55e' : '#333', position: 'relative', transition: 'background 0.2s',
    flexShrink: 0,
  }),
  dot:     (on) => ({
    position: 'absolute', top: 3, left: on ? 23 : 3, width: 18, height: 18,
    borderRadius: '50%', background: '#fff', transition: 'left 0.2s',
  }),
  note:    { fontSize: 11, color: '#4b5563', marginTop: 6, lineHeight: 1.5 },
  success: { color: '#22c55e', fontSize: 12, marginTop: 8 },
  error:   { color: '#ef4444', fontSize: 12, marginTop: 8 },
  divider: { border: 'none', borderTop: '1px solid #222', margin: '16px 0' },
}

function Field({ label, note, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={S.label}>{label}</label>
      {children}
      {note && <p style={S.note}>{note}</p>}
    </div>
  )
}

export default function Settings() {
  const [form, setForm] = useState({
    whatsapp_enabled:   false,
    whatsapp_to:        '',
    budget:             '',
    twilio_account_sid: '',
    twilio_auth_token:  '',
    twilio_from:        '',
  })
  const [saving,   setSaving]   = useState(false)
  const [testing,  setTesting]  = useState(false)
  const [sending,  setSending]  = useState(false)
  const [msg,      setMsg]      = useState(null)   // { type: 'success'|'error', text }

  useEffect(() => {
    api.getSettings().then(data => {
      setForm(f => ({
        ...f,
        whatsapp_enabled:   data.whatsapp_enabled   ?? false,
        whatsapp_to:        data.whatsapp_to        ?? '',
        budget:             data.budget             ?? '',
        twilio_account_sid: data.twilio_account_sid ?? '',
        twilio_auth_token:  data.twilio_auth_token  ?? '',
        twilio_from:        data.twilio_from        ?? '',
      }))
    }).catch(() => {})
  }, [])

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handleSave = async () => {
    setSaving(true)
    setMsg(null)
    try {
      const payload = {
        whatsapp_enabled:   form.whatsapp_enabled,
        whatsapp_to:        form.whatsapp_to       || undefined,
        budget:             form.budget ? Number(form.budget) : undefined,
        twilio_account_sid: form.twilio_account_sid || undefined,
        twilio_auth_token:  form.twilio_auth_token  || undefined,
        twilio_from:        form.twilio_from        || undefined,
      }
      await api.updateSettings(payload)
      setMsg({ type: 'success', text: 'Settings saved.' })
    } catch (e) {
      setMsg({ type: 'error', text: e.message })
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setMsg(null)
    try {
      const res = await api.testWhatsApp()
      setMsg({ type: 'success', text: res.message })
    } catch (e) {
      setMsg({ type: 'error', text: e.message })
    } finally {
      setTesting(false)
    }
  }

  const handleSendNow = async () => {
    setSending(true)
    setMsg(null)
    try {
      const res = await api.sendReportNow()
      setMsg({ type: 'success', text: `${res.message} (${res.predictions} stocks)` })
    } catch (e) {
      setMsg({ type: 'error', text: e.message })
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={S.page}>
      <h1 style={{ color: '#fff', fontSize: 18, fontWeight: 700, marginBottom: 6 }}>Settings</h1>
      <p style={{ color: '#6b7280', fontSize: 13, marginBottom: 24 }}>
        Configure WhatsApp reports. After each analysis run, OpenBell will send you a full report with buy signals, targets, and position sizing.
      </p>

      {/* ── WhatsApp ─────────────────────────────────────────────────────── */}
      <div style={S.card}>
        <p style={S.heading}>WhatsApp Reports</p>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <button
            style={S.toggle(form.whatsapp_enabled)}
            onClick={() => set('whatsapp_enabled', !form.whatsapp_enabled)}
          >
            <span style={S.dot(form.whatsapp_enabled)} />
          </button>
          <span style={{ color: form.whatsapp_enabled ? '#22c55e' : '#6b7280', fontSize: 13 }}>
            {form.whatsapp_enabled ? 'Enabled — reports will be sent after each analysis' : 'Disabled'}
          </span>
        </div>

        <Field
          label="Your WhatsApp Number"
          note="Include country code, e.g. +919876543210. The number must join the Twilio sandbox (see below)."
        >
          <input
            style={S.input}
            type="tel"
            placeholder="+919876543210"
            value={form.whatsapp_to}
            onChange={e => set('whatsapp_to', e.target.value)}
          />
        </Field>

        <Field
          label="Portfolio Budget (₹)"
          note="Optional. If set, the report will calculate suggested quantity, capital, max profit, and max loss for each buy signal. Leave blank to skip position sizing."
        >
          <input
            style={S.input}
            type="number"
            placeholder="e.g. 50000"
            value={form.budget}
            onChange={e => set('budget', e.target.value)}
          />
        </Field>
      </div>

      {/* ── Twilio ───────────────────────────────────────────────────────── */}
      <div style={S.card}>
        <p style={S.heading}>Twilio Credentials</p>
        <p style={{ color: '#6b7280', fontSize: 12, marginBottom: 16, lineHeight: 1.6 }}>
          OpenBell uses Twilio to send WhatsApp messages. You can set these here or in your <code style={{ background: '#0d0d0d', padding: '1px 5px', borderRadius: 4, color: '#9ca3af' }}>.env</code> file as <code style={{ background: '#0d0d0d', padding: '1px 5px', borderRadius: 4, color: '#9ca3af' }}>TWILIO_ACCOUNT_SID</code>, <code style={{ background: '#0d0d0d', padding: '1px 5px', borderRadius: 4, color: '#9ca3af' }}>TWILIO_AUTH_TOKEN</code>, and <code style={{ background: '#0d0d0d', padding: '1px 5px', borderRadius: 4, color: '#9ca3af' }}>TWILIO_FROM_NUMBER</code>.
        </p>

        <Field label="Account SID" note="Starts with AC... — found in your Twilio Console dashboard.">
          <input
            style={S.input}
            type="text"
            placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            value={form.twilio_account_sid}
            onChange={e => set('twilio_account_sid', e.target.value)}
          />
        </Field>

        <Field label="Auth Token" note="Found next to the Account SID in Twilio Console.">
          <input
            style={S.input}
            type="password"
            placeholder="••••••••••••••••••••••••••••••••"
            value={form.twilio_auth_token}
            onChange={e => set('twilio_auth_token', e.target.value)}
          />
        </Field>

        <Field
          label="From Number (Twilio Sandbox)"
          note="The Twilio WhatsApp number. For sandbox, this is +14155238886. For production, use your approved Twilio number."
        >
          <input
            style={S.input}
            type="tel"
            placeholder="+14155238886"
            value={form.twilio_from}
            onChange={e => set('twilio_from', e.target.value)}
          />
        </Field>

        <hr style={S.divider} />

        {/* Sandbox setup instructions */}
        <p style={{ ...S.heading, marginBottom: 12 }}>Quick Setup — Twilio Sandbox</p>
        <ol style={{ color: '#6b7280', fontSize: 12, lineHeight: 2, paddingLeft: 18, margin: 0 }}>
          <li>Sign up free at <span style={{ color: '#9ca3af' }}>twilio.com</span></li>
          <li>Go to <strong style={{ color: '#9ca3af' }}>Messaging → Try it out → Send a WhatsApp message</strong></li>
          <li>Send <code style={{ background: '#0d0d0d', padding: '1px 5px', borderRadius: 4, color: '#22c55e' }}>join &lt;sandbox-word&gt;</code> from your WhatsApp to the Twilio number</li>
          <li>Copy your Account SID and Auth Token from the Console dashboard</li>
          <li>Paste them above, enter your number, and click <strong style={{ color: '#9ca3af' }}>Test WhatsApp</strong></li>
        </ol>
      </div>

      {/* ── Report preview ───────────────────────────────────────────────── */}
      <div style={S.card}>
        <p style={S.heading}>What the Report Includes</p>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {[
            ['Top Buy Signals', 'Up to 5 bullish stocks with confidence ≥ 60%'],
            ['Entry Price', 'Limit order price — slightly below current price'],
            ['Target Range', 'Predicted low and high targets with % upside'],
            ['Stop Loss', '5% below entry price to limit downside'],
            ['Position Sizing', 'Suggested qty, capital, max profit/loss (if budget set)'],
            ['All Signals', 'Full ranked list of every stock analysed'],
            ['Bearish Alerts', 'Stocks to avoid or watch carefully'],
            ['Risk:Reward', 'Ratio for each buy signal'],
          ].map(([title, desc]) => (
            <div key={title} style={{ background: '#0d0d0d', borderRadius: 8, padding: 12 }}>
              <p style={{ color: '#e5e7eb', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>{title}</p>
              <p style={{ color: '#6b7280', fontSize: 11, lineHeight: 1.5 }}>{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Actions ──────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <button style={S.btn('primary')} onClick={handleSave} disabled={saving}>
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
        <a
          href="/api/predictions/report.xlsx"
          download
          style={{
            padding: '9px 18px', borderRadius: 8, fontSize: 13, fontWeight: 600,
            background: '#16a34a', color: '#fff', textDecoration: 'none',
            display: 'inline-flex', alignItems: 'center', gap: 6,
          }}
        >
          ⬇ Download Report (Excel)
        </a>
        <button
          style={{ ...S.btn('ghost'), border: '1px solid #25d366', color: '#25d366' }}
          onClick={handleSendNow}
          disabled={sending}
          title="Send today's analysis to your WhatsApp number"
        >
          {sending ? 'Sending…' : '📲 Send to WhatsApp'}
        </button>
        <button style={S.btn('ghost')} onClick={handleTest} disabled={testing}>
          {testing ? 'Sending…' : 'Test WhatsApp'}
        </button>
      </div>
      <p style={{ color: '#4b5563', fontSize: 11, marginTop: 8 }}>
        <em>Download Report</em> saves an Excel file. <em>Send to WhatsApp</em> sends the text report to your configured number.
      </p>

      {msg && (
        <p style={msg.type === 'success' ? S.success : S.error}>
          {msg.type === 'success' ? '✓ ' : '✗ '}{msg.text}
        </p>
      )}
    </div>
  )
}
