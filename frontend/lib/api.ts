// Klien fetch ke backend. Selalu lewat path relatif /api/* supaya
// ditangani rewrites di next.config.js -- jangan pernah hardcode
// http://backend:8000 di sini, itu tidak dikenal browser.
export const API_BASE = '/api'
