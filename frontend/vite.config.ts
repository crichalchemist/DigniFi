import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  // Heroku/whitenoise serves built assets under /static/frontend/, but the
  // dev server must stay at / — BrowserRouter has no basename, so a dev base
  // of /static/frontend/ makes every route render blank.
  base: command === 'build' ? '/static/frontend/' : '/',
}));
