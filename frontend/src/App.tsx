import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Landing } from './pages/Landing'
import { GamePage } from './pages/GamePage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/g/:code" element={<GamePage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
