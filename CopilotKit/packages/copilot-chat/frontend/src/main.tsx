import React from 'react'
import { render } from 'react-dom'
import App from './App.tsx'
import './index.css'

const rootElement = document.getElementById('root')
if (rootElement) {
  render(<App />, rootElement)
}