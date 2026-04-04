import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import Watchlist from './pages/Watchlist'
import Predict from './pages/Predict'
import History from './pages/History'
import Accuracy from './pages/Accuracy'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-surface">
        <Navbar />
        <main>
          <Routes>
            <Route path="/"          element={<Dashboard />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/predict"   element={<Predict />} />
            <Route path="/history"   element={<History />} />
            <Route path="/accuracy" element={<Accuracy />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
