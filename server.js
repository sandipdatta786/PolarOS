/**
 * PolarOS Demo Server
 *
 * Simple Express server that:
 * 1. Serves the React UI modules
 * 2. Provides API endpoints for database queries
 * 3. Handles offline sync (Phase 4)
 *
 * Usage:
 *   npm install
 *   node server.js
 *   Open http://localhost:3000
 */

const express = require('express');
const cors = require('cors');
const path = require('path');
const burnrateHandler = require('./api/burnrate');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// API Routes
app.post('/api/burnrate', burnrateHandler);

// Serve index
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'ui', 'index.html'));
});

// Serve module as single-file demo
app.get('/demo/inventory', (req, res) => {
  res.sendFile(path.join(__dirname, 'ui', 'inventory-demo.html'));
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() });
});

// Start server
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════╗
║  PolarOS Demo Server Running           ║
╠════════════════════════════════════════╣
║  🌐 http://localhost:${PORT}                ║
║                                        ║
║  Routes:                               ║
║  • /              — Main UI             ║
║  • /demo/inventory — Inventory module  ║
║  • /api/burnrate  — Forecast data      ║
║  • /health        — Health check       ║
╚════════════════════════════════════════╝
  `);
});
