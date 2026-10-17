import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { QueryClientProvider } from '@tanstack/react-query'

import App from './App'
import { createQueryClient } from './api/queryClient'
import InterfaceLanguage from './components/InterfaceLanguage'
import './index.css'

const queryClient = createQueryClient()

const root = document.getElementById('root')
if (!root) throw new Error('index.html is missing #root')

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      {/*
        `basename` keeps the route table free of the mount path: App.tsx says
        '/sign-in' and the browser shows '/manager/sign-in'. Moving the client is
        then this one string plus Vite's `base` and the backend's SPA_MOUNT,
        rather than an edit to every route.
      */}
      <BrowserRouter basename="/manager">
        <InterfaceLanguage>
          <App />
        </InterfaceLanguage>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
