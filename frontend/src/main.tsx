import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource/jost/400.css';
import '@fontsource/jost/500.css';
import '@fontsource/jost/600.css';
import '@fontsource/public-sans/400.css';
import '@fontsource/public-sans/500.css';
import '@fontsource/public-sans/600.css';
import './styles/tokens.css';
import './styles/global.css';
import App from './App.tsx';

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error("Root element with id 'root' not found");

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
