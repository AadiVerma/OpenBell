import { NavLink } from 'react-router-dom'

const links = [
  { to: '/',          label: 'Signals'  },
  { to: '/watchlist', label: 'Watchlist'},
  { to: '/predict',   label: 'Predict'  },
  { to: '/history',   label: 'History'  },
  { to: '/accuracy',  label: 'Accuracy' },
]

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b" style={{ background: '#111', borderColor: '#222' }}>
      <div className="max-w-5xl mx-auto px-4 h-12 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-semibold text-white text-sm tracking-wide">OpenBell</span>
          <span className="text-xs text-gray-600 font-mono ml-1">AI signals</span>
        </div>

        {/* Nav */}
        <nav className="flex items-center gap-0.5">
          {links.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-white/10 text-white'
                    : 'text-gray-500 hover:text-white hover:bg-white/5'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
