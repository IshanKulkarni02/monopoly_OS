import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Landing } from './pages/Landing'
import { GamePage } from './pages/GamePage'
import { BoardEditor } from './pages/BoardEditor'
import { PublicDisplay } from './pages/PublicDisplay'
import { EconomyLab } from './pages/EconomyLab'
import { AccountProvider } from './hooks/useAccount'

function App() {
  return (
    <AccountProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/g/:code" element={<GamePage />} />
          <Route path="/g/:code/display" element={<PublicDisplay />} />
          <Route path="/boards/:key/edit" element={<BoardEditor />} />
          <Route path="/lab" element={<EconomyLab />} />
        </Routes>
      </BrowserRouter>
    </AccountProvider>
  )
}

export default App
