import { CopilotKit } from '@copilotkit/react-core-next'
import './App.css'
import { HomePage } from './components/HomePage'

function App() {
  return (
    <CopilotKit 
      runtimeUrl="/api/copilotkit"
      showDevConsole={true}
    >
      <div className="copilotkit-container">
        <HomePage />
      </div>
    </CopilotKit>
  )
}

export default App 