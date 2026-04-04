/* Horizontal bar chart — confidence overview of all today's signals */
import {
  BarChart, Bar, XAxis, YAxis, Cell, Tooltip, ResponsiveContainer, LabelList,
} from 'recharts'

const SIGNAL_COLOR = { bullish: '#10b981', bearish: '#ef4444', neutral: '#eab308' }

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 text-sm shadow-xl">
      <p className="font-mono font-semibold text-white">{d.ticker}</p>
      <p className="text-gray-400">
        {d.signal} · <span className="text-white font-semibold">{d.confidence}%</span>
      </p>
      <p className="text-sky-400 text-xs">Limit ₹{d.limit_price?.toLocaleString('en-IN')}</p>
    </div>
  )
}

export default function ConfidenceChart({ signals }) {
  if (!signals?.length) return null

  const data = [...signals]
    .sort((a, b) => b.confidence - a.confidence)
    .map(s => ({ ...s, ticker: s.ticker.replace('.NS', '').replace('.BO', '') }))

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-wider">
        Confidence Overview
      </h2>
      <ResponsiveContainer width="100%" height={data.length * 44 + 16}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 48, bottom: 0, left: 0 }}
          barSize={14}
        >
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis
            type="category"
            dataKey="ticker"
            width={80}
            tick={{ fill: '#9ca3af', fontSize: 13, fontFamily: 'JetBrains Mono' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <Bar dataKey="confidence" radius={[0, 4, 4, 0]} background={{ fill: 'rgba(255,255,255,0.04)', radius: 4 }}>
            {data.map((entry, i) => (
              <Cell key={i} fill={SIGNAL_COLOR[entry.signal] || '#eab308'} />
            ))}
            <LabelList
              dataKey="confidence"
              position="right"
              formatter={v => `${v}%`}
              style={{ fill: '#9ca3af', fontSize: 12, fontFamily: 'JetBrains Mono' }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
