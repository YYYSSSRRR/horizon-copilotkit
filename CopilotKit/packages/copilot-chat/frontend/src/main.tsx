import React from 'react'
import { render } from 'react-dom'
import App from './App.tsx'
import './index.css'

let rootElement = document.getElementById('root')
if (!rootElement) {
  rootElement = document.createElement('div')
  rootElement.id = 'root'
  document.body.appendChild(rootElement)
}

render(<App />, rootElement)