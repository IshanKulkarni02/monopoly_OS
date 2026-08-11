import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Landing } from './pages/Landing'
import { GamePage } from './pages/GamePage'
import { BoardEditor } from './pages/BoardEditor'
import { AccountProvider } from './hooks/useAccount'

function App() {
  return (
    <AccountProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/g/:code" element={<GamePage />} />
          <Route path="/boards/:key/edit" element={<BoardEditor />} />
        </Routes>
      </BrowserRouter>
    </AccountProvider>
  )
}

export default App
