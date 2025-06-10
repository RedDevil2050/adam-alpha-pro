#!/usr/bin/env python3
"""
Zion Market Analysis Platform - One-Click Frontend Connector
===========================================================

This script provides seamless integration with any frontend framework.
Run this script and your backend will be ready to connect to:
- React/Next.js
- Vue/Nuxt
- Angular
- Svelte/SvelteKit
- Plain HTML/JavaScript
- Mobile apps (React Native, Flutter)
- Desktop apps (Electron)

Usage:
    python quick_connect.py
    python quick_connect.py --cors-all
    python quick_connect.py --frontend react
    python quick_connect.py --port 8000
"""

import asyncio
import sys
import os
import subprocess
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import your existing backend
from backend.api.main import app as backend_app


class FrontendConnector:
    """One-click frontend connector for Zion Market Analysis Platform"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Zion Market Analysis Platform - Frontend Connector",
            description="One-click backend connection for any frontend",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        self.setup_middleware()
        self.setup_routes()
        self.mount_backend()
        
    def setup_middleware(self):
        """Configure middleware for maximum frontend compatibility"""
        
        # Ultra-permissive CORS for development
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins
            allow_credentials=True,
            allow_methods=["*"],  # Allow all methods
            allow_headers=["*"],  # Allow all headers
            expose_headers=["*"], # Expose all headers
        )
        
        # Compression for better performance
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Custom middleware for frontend compatibility
        @self.app.middleware("http")
        async def frontend_compatibility_middleware(request: Request, call_next):
            # Handle preflight requests
            if request.method == "OPTIONS":
                return JSONResponse(
                    content={},
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "*",
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Max-Age": "86400",
                    }
                )
            
            response = await call_next(request)
            
            # Add security headers (can be disabled for dev)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            
            return response

    def setup_routes(self):
        """Setup connector-specific routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def connection_dashboard():
            """Interactive connection dashboard"""
            return self.get_connection_dashboard_html()
        
        @self.app.get("/api/connect/info")
        async def connection_info():
            """Get connection information for frontends"""
            return {
                "status": "ready",
                "backend_url": "http://localhost:8000",
                "api_prefix": "/api",
                "websocket_url": "ws://localhost:8000/ws",
                "available_endpoints": await self.get_available_endpoints(),
                "authentication": {
                    "type": "Bearer Token",
                    "login_endpoint": "/api/login",
                    "test_credentials": {
                        "username": "admin",
                        "password": "changeme"
                    }
                },
                "integration_examples": self.get_integration_examples()
            }
        
        @self.app.get("/api/connect/test")
        async def test_connection():
            """Test endpoint for frontend connectivity"""
            return {
                "message": "✅ Connection successful!",
                "timestamp": asyncio.get_event_loop().time(),
                "backend_status": "running",
                "cors_enabled": True
            }
        
        @self.app.get("/api/connect/examples/{framework}")
        async def get_framework_example(framework: str):
            """Get integration code examples for specific frameworks"""
            examples = self.get_integration_examples()
            if framework.lower() in examples:
                return examples[framework.lower()]
            raise HTTPException(404, f"Examples not available for {framework}")
        
        @self.app.get("/api/connect/quickstart")
        async def get_quickstart_code():
            """Get ready-to-use quickstart code"""
            return {
                "html": self.get_html_quickstart(),
                "react": self.get_react_quickstart(),
                "vue": self.get_vue_quickstart(),
                "vanilla_js": self.get_vanilla_js_quickstart()
            }

    def mount_backend(self):
        """Mount the existing backend app"""
        self.app.mount("/api", backend_app)

    async def get_available_endpoints(self) -> List[Dict]:
        """Get list of available API endpoints"""
        return [
            {
                "path": "/api/login",
                "method": "POST",
                "description": "User authentication",
                "body": {"username": "string", "password": "string"}
            },
            {
                "path": "/api/analyze/{symbol}",
                "method": "GET",
                "description": "Analyze stock symbol",
                "example": "/api/analyze/AAPL"
            },
            {
                "path": "/api/analyze/enhanced",
                "method": "POST",
                "description": "Enhanced stock analysis",
                "body": {"symbol": "string", "options": "object"}
            },
            {
                "path": "/api/health",
                "method": "GET",
                "description": "System health check"
            },
            {
                "path": "/api/v1/metrics",
                "method": "GET",
                "description": "System metrics"
            }
        ]

    def get_integration_examples(self) -> Dict:
        """Get code examples for different frameworks"""
        return {
            "react": {
                "title": "React Integration",
                "code": '''
// Install: npm install axios react-query
import axios from 'axios';
import { useQuery } from 'react-query';

const API_BASE = 'http://localhost:8000';

// API Service
const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

// React Component
function StockAnalysis({ symbol }) {
  const { data, isLoading, error } = useQuery(
    ['analysis', symbol],
    () => api.get(`/api/analyze/${symbol}`).then(res => res.data)
  );

  if (isLoading) return <div>Analyzing {symbol}...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h2>{data.symbol} Analysis</h2>
      <p>Verdict: {data.verdict}</p>
      <p>Confidence: {data.confidence}</p>
    </div>
  );
}
                ''',
                "setup": [
                    "npm install axios react-query",
                    "Add QueryClient provider to your app",
                    "Use the component above"
                ]
            },
            "vue": {
                "title": "Vue.js Integration",
                "code": '''
<!-- Install: npm install axios -->
<template>
  <div>
    <h2 v-if="analysis">{{ analysis.symbol }} Analysis</h2>
    <p v-if="loading">Analyzing {{ symbol }}...</p>
    <div v-else-if="analysis">
      <p>Verdict: {{ analysis.verdict }}</p>
      <p>Confidence: {{ analysis.confidence }}</p>
    </div>
    <p v-if="error">Error: {{ error }}</p>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'StockAnalysis',
  props: ['symbol'],
  data() {
    return {
      analysis: null,
      loading: false,
      error: null
    }
  },
  async mounted() {
    await this.fetchAnalysis()
  },
  methods: {
    async fetchAnalysis() {
      this.loading = true
      try {
        const response = await axios.get(`http://localhost:8000/api/analyze/${this.symbol}`)
        this.analysis = response.data
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    }
  }
}
</script>
                ''',
                "setup": [
                    "npm install axios",
                    "Use the component above",
                    "Pass symbol as prop"
                ]
            },
            "vanilla_js": {
                "title": "Vanilla JavaScript",
                "code": '''
// Simple JavaScript integration
class ZionAPI {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
  }

  async analyzeStock(symbol) {
    try {
      const response = await fetch(`${this.baseURL}/api/analyze/${symbol}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.error('Analysis failed:', error);
      throw error;
    }
  }

  async login(username, password) {
    const response = await fetch(`${this.baseURL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    return await response.json();
  }
}

// Usage
const zion = new ZionAPI();

async function displayAnalysis(symbol) {
  const container = document.getElementById('analysis');
  container.innerHTML = 'Analyzing...';
  
  try {
    const data = await zion.analyzeStock(symbol);
    container.innerHTML = `
      <h3>${data.symbol} Analysis</h3>
      <p>Verdict: ${data.verdict}</p>
      <p>Confidence: ${data.confidence}</p>
    `;
  } catch (error) {
    container.innerHTML = `Error: ${error.message}`;
  }
}
                ''',
                "setup": [
                    "Copy the code above",
                    "Add <div id='analysis'></div> to your HTML",
                    "Call displayAnalysis('AAPL')"
                ]
            },
            "angular": {
                "title": "Angular Integration",
                "code": '''
// Install: ng add @angular/common/http
// service: zion-api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ZionApiService {
  private baseURL = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  analyzeStock(symbol: string): Observable<any> {
    return this.http.get(`${this.baseURL}/api/analyze/${symbol}`);
  }

  login(username: string, password: string): Observable<any> {
    return this.http.post(`${this.baseURL}/api/login`, { username, password });
  }
}

// component: stock-analysis.component.ts
import { Component, Input } from '@angular/core';
import { ZionApiService } from './zion-api.service';

@Component({
  selector: 'app-stock-analysis',
  template: `
    <div *ngIf="loading">Analyzing {{ symbol }}...</div>
    <div *ngIf="analysis">
      <h3>{{ analysis.symbol }} Analysis</h3>
      <p>Verdict: {{ analysis.verdict }}</p>
      <p>Confidence: {{ analysis.confidence }}</p>
    </div>
    <div *ngIf="error">Error: {{ error }}</div>
  `
})
export class StockAnalysisComponent {
  @Input() symbol!: string;
  analysis: any;
  loading = false;
  error: string | null = null;

  constructor(private zionApi: ZionApiService) {}

  ngOnInit() {
    this.fetchAnalysis();
  }

  fetchAnalysis() {
    this.loading = true;
    this.zionApi.analyzeStock(this.symbol).subscribe({
      next: (data) => {
        this.analysis = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = err.message;
        this.loading = false;
      }
    });
  }
}
                ''',
                "setup": [
                    "ng add @angular/common/http",
                    "Add HttpClientModule to imports",
                    "Create the service and component above"
                ]
            }
        }

    def get_connection_dashboard_html(self) -> str:
        """Generate interactive connection dashboard"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zion Market Analysis - Frontend Connector</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 2rem;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #2196F3, #21CBF3);
            color: white; 
            padding: 3rem 2rem;
            text-align: center;
        }
        .header h1 { font-size: 3rem; margin-bottom: 1rem; }
        .header p { font-size: 1.2rem; opacity: 0.9; }
        .content { padding: 3rem 2rem; }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 2rem; 
            margin-bottom: 3rem;
        }
        .card { 
            border: 1px solid #e0e0e0; 
            border-radius: 15px; 
            padding: 2rem;
            background: #fafafa;
            transition: transform 0.3s ease;
        }
        .card:hover { transform: translateY(-5px); }
        .card h3 { color: #2196F3; margin-bottom: 1rem; }
        .status { 
            background: #4CAF50; 
            color: white; 
            padding: 0.5rem 1rem; 
            border-radius: 25px; 
            display: inline-block;
            margin-bottom: 1rem;
        }
        .button { 
            background: #2196F3; 
            color: white; 
            border: none; 
            padding: 0.8rem 1.5rem; 
            border-radius: 8px; 
            cursor: pointer;
            font-size: 1rem;
            margin: 0.5rem 0.5rem 0.5rem 0;
            transition: background 0.3s ease;
        }
        .button:hover { background: #1976D2; }
        .code { 
            background: #f5f5f5; 
            padding: 1rem; 
            border-radius: 8px; 
            font-family: 'Monaco', 'Menlo', monospace;
            overflow-x: auto;
            margin: 1rem 0;
        }
        .endpoint { 
            background: white; 
            border: 1px solid #ddd; 
            border-radius: 8px; 
            padding: 1rem; 
            margin: 0.5rem 0;
        }
        .method { 
            background: #4CAF50; 
            color: white; 
            padding: 0.2rem 0.5rem; 
            border-radius: 4px; 
            font-size: 0.8rem;
            margin-right: 0.5rem;
        }
        .method.post { background: #FF9800; }
        .examples { margin-top: 2rem; }
        .tab-buttons { margin-bottom: 1rem; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Zion Market Analysis</h1>
            <p>One-Click Frontend Connector</p>
            <div class="status">✅ Backend Ready</div>
        </div>
        
        <div class="content">
            <div class="grid">
                <div class="card">
                    <h3>🔌 Connection Status</h3>
                    <p>Your backend is running and ready to connect!</p>
                    <div class="code">
                        Base URL: http://localhost:8000<br>
                        API Prefix: /api<br>
                        CORS: ✅ Enabled<br>
                        Auth: Bearer Token
                    </div>
                    <button class="button" onclick="testConnection()">Test Connection</button>
                    <div id="test-result"></div>
                </div>
                
                <div class="card">
                    <h3>⚡ Quick Start</h3>
                    <p>Get started in seconds with any framework:</p>
                    <button class="button" onclick="copyQuickStart('react')">React</button>
                    <button class="button" onclick="copyQuickStart('vue')">Vue</button>
                    <button class="button" onclick="copyQuickStart('vanilla')">JavaScript</button>
                    <button class="button" onclick="copyQuickStart('angular')">Angular</button>
                    <div id="quickstart-result"></div>
                </div>
                
                <div class="card">
                    <h3>📡 Live API Test</h3>
                    <p>Test your API endpoints right here:</p>
                    <input type="text" id="test-symbol" placeholder="Enter symbol (e.g., AAPL)" style="width: 100%; padding: 0.5rem; margin: 1rem 0; border: 1px solid #ddd; border-radius: 4px;">
                    <button class="button" onclick="analyzeSymbol()">Analyze Stock</button>
                    <div id="api-result"></div>
                </div>
            </div>
            
            <div class="card">
                <h3>📋 Available Endpoints</h3>
                <div class="endpoints">
                    <div class="endpoint">
                        <span class="method post">POST</span>
                        <strong>/api/login</strong> - User authentication
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span>
                        <strong>/api/analyze/{symbol}</strong> - Analyze stock symbol
                    </div>
                    <div class="endpoint">
                        <span class="method post">POST</span>
                        <strong>/api/analyze/enhanced</strong> - Enhanced analysis
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span>
                        <strong>/api/health</strong> - System health check
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span>
                        <strong>/api/v1/metrics</strong> - System metrics
                    </div>
                </div>
            </div>
            
            <div class="examples">
                <h3>💻 Integration Examples</h3>
                <div class="tab-buttons">
                    <button class="button" onclick="showTab('react')">React</button>
                    <button class="button" onclick="showTab('vue')">Vue</button>
                    <button class="button" onclick="showTab('vanilla')">JavaScript</button>
                    <button class="button" onclick="showTab('angular')">Angular</button>
                </div>
                
                <div id="react" class="tab-content">
                    <h4>React Integration</h4>
                    <div class="code">
// Install: npm install axios react-query
import axios from 'axios';
import { useQuery } from 'react-query';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

function StockAnalysis({ symbol }) {
  const { data, isLoading, error } = useQuery(
    ['analysis', symbol],
    () => api.get(`/api/analyze/${symbol}`).then(res => res.data)
  );

  if (isLoading) return <div>Analyzing...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h2>{data.symbol} Analysis</h2>
      <p>Verdict: {data.verdict}</p>
      <p>Confidence: {data.confidence}</p>
    </div>
  );
}
                    </div>
                </div>
                
                <div id="vue" class="tab-content">
                    <h4>Vue.js Integration</h4>
                    <div class="code">
// Install: npm install axios
import axios from 'axios'

export default {
  data() {
    return { analysis: null, loading: false }
  },
  async mounted() {
    this.loading = true
    try {
      const response = await axios.get(`http://localhost:8000/api/analyze/AAPL`)
      this.analysis = response.data
    } finally {
      this.loading = false
    }
  }
}
                    </div>
                </div>
                
                <div id="vanilla" class="tab-content">
                    <h4>Vanilla JavaScript</h4>
                    <div class="code">
async function analyzeStock(symbol) {
  const response = await fetch(`http://localhost:8000/api/analyze/${symbol}`);
  const data = await response.json();
  
  document.getElementById('result').innerHTML = `
    <h3>${data.symbol} Analysis</h3>
    <p>Verdict: ${data.verdict}</p>
    <p>Confidence: ${data.confidence}</p>
  `;
}

// Usage
analyzeStock('AAPL');
                    </div>
                </div>
                
                <div id="angular" class="tab-content">
                    <h4>Angular Integration</h4>
                    <div class="code">
import { HttpClient } from '@angular/common/http';

@Injectable()
export class ZionApiService {
  constructor(private http: HttpClient) {}
  
  analyzeStock(symbol: string) {
    return this.http.get(`http://localhost:8000/api/analyze/${symbol}`);
  }
}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function testConnection() {
            const result = document.getElementById('test-result');
            result.innerHTML = 'Testing...';
            
            try {
                const response = await fetch('/api/connect/test');
                const data = await response.json();
                result.innerHTML = `<div style="color: green; margin-top: 1rem;">✅ ${data.message}</div>`;
            } catch (error) {
                result.innerHTML = `<div style="color: red; margin-top: 1rem;">❌ Connection failed: ${error.message}</div>`;
            }
        }
        
        async function analyzeSymbol() {
            const symbol = document.getElementById('test-symbol').value;
            const result = document.getElementById('api-result');
            
            if (!symbol) {
                result.innerHTML = '<div style="color: red; margin-top: 1rem;">Please enter a symbol</div>';
                return;
            }
            
            result.innerHTML = 'Analyzing...';
            
            try {
                const response = await fetch(`/api/analyze/${symbol}`);
                const data = await response.json();
                result.innerHTML = `
                    <div style="background: white; padding: 1rem; border-radius: 8px; margin-top: 1rem; border: 1px solid #ddd;">
                        <strong>${data.symbol} Analysis</strong><br>
                        Verdict: ${data.verdict}<br>
                        Confidence: ${data.confidence}<br>
                        Agent: ${data.agent_name}
                    </div>
                `;
            } catch (error) {
                result.innerHTML = `<div style="color: red; margin-top: 1rem;">❌ Error: ${error.message}</div>`;
            }
        }
        
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
        }
        
        async function copyQuickStart(framework) {
            const result = document.getElementById('quickstart-result');
            
            try {
                const response = await fetch(`/api/connect/examples/${framework}`);
                const data = await response.json();
                
                // Copy to clipboard
                await navigator.clipboard.writeText(data.code);
                result.innerHTML = `<div style="color: green; margin-top: 1rem;">✅ ${data.title} code copied to clipboard!</div>`;
            } catch (error) {
                result.innerHTML = `<div style="color: red; margin-top: 1rem;">❌ Failed to copy: ${error.message}</div>`;
            }
        }
        
        // Show React tab by default
        showTab('react');
        
        // Auto-test connection on load
        window.addEventListener('load', testConnection);
    </script>
</body>
</html>
        '''

    def get_html_quickstart(self) -> str:
        """Get HTML quickstart code"""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>Zion Market Analysis</title>
</head>
<body>
    <h1>Stock Analysis</h1>
    <input type="text" id="symbol" placeholder="Enter symbol">
    <button onclick="analyzeStock()">Analyze</button>
    <div id="result"></div>

    <script>
        async function analyzeStock() {
            const symbol = document.getElementById('symbol').value;
            const response = await fetch(`http://localhost:8000/api/analyze/${symbol}`);
            const data = await response.json();
            
            document.getElementById('result').innerHTML = `
                <h3>${data.symbol} Analysis</h3>
                <p>Verdict: ${data.verdict}</p>
                <p>Confidence: ${data.confidence}</p>
            `;
        }
    </script>
</body>
</html>
        '''

    def get_react_quickstart(self) -> str:
        """Get React quickstart code"""
        return '''
// Install: npm install axios
import React, { useState } from 'react';
import axios from 'axios';

function App() {
  const [symbol, setSymbol] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeStock = async () => {
    if (!symbol) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`http://localhost:8000/api/analyze/${symbol}`);
      setAnalysis(response.data);
    } catch (error) {
      console.error('Analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Zion Market Analysis</h1>
      <input 
        value={symbol} 
        onChange={(e) => setSymbol(e.target.value)} 
        placeholder="Enter symbol" 
      />
      <button onClick={analyzeStock} disabled={loading}>
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>
      
      {analysis && (
        <div>
          <h3>{analysis.symbol} Analysis</h3>
          <p>Verdict: {analysis.verdict}</p>
          <p>Confidence: {analysis.confidence}</p>
        </div>
      )}
    </div>
  );
}

export default App;
        '''

    def get_vue_quickstart(self) -> str:
        """Get Vue quickstart code"""
        return '''
<!-- Install: npm install axios -->
<template>
  <div>
    <h1>Zion Market Analysis</h1>
    <input v-model="symbol" placeholder="Enter symbol">
    <button @click="analyzeStock" :disabled="loading">
      {{ loading ? 'Analyzing...' : 'Analyze' }}
    </button>
    
    <div v-if="analysis">
      <h3>{{ analysis.symbol }} Analysis</h3>
      <p>Verdict: {{ analysis.verdict }}</p>
      <p>Confidence: {{ analysis.confidence }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  data() {
    return {
      symbol: '',
      analysis: null,
      loading: false
    }
  },
  methods: {
    async analyzeStock() {
      if (!this.symbol) return
      
      this.loading = true
      try {
        const response = await axios.get(`http://localhost:8000/api/analyze/${this.symbol}`)
        this.analysis = response.data
      } catch (error) {
        console.error('Analysis failed:', error)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>
        '''

    def get_vanilla_js_quickstart(self) -> str:
        """Get vanilla JavaScript quickstart code"""
        return '''
class ZionAPI {
  constructor() {
    this.baseURL = 'http://localhost:8000';
  }

  async analyzeStock(symbol) {
    const response = await fetch(`${this.baseURL}/api/analyze/${symbol}`);
    return await response.json();
  }

  async login(username, password) {
    const response = await fetch(`${this.baseURL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    return await response.json();
  }
}

// Usage
const zion = new ZionAPI();

async function displayAnalysis(symbol) {
  try {
    const data = await zion.analyzeStock(symbol);
    console.log('Analysis:', data);
    
    // Display in DOM
    document.body.innerHTML += `
      <div>
        <h3>${data.symbol} Analysis</h3>
        <p>Verdict: ${data.verdict}</p>
        <p>Confidence: ${data.confidence}</p>
      </div>
    `;
  } catch (error) {
    console.error('Error:', error);
  }
}

// Analyze AAPL
displayAnalysis('AAPL');
        '''


def main():
    """Main function to start the connector"""
    parser = argparse.ArgumentParser(description='Zion Market Analysis - One-Click Frontend Connector')
    parser.add_argument('--port', type=int, default=8000, help='Port to run on (default: 8000)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--cors-all', action='store_true', help='Enable CORS for all origins')
    parser.add_argument('--frontend', choices=['react', 'vue', 'angular', 'svelte'], help='Optimize for specific frontend')
    parser.add_argument('--dev', action='store_true', help='Development mode with auto-reload')
    
    args = parser.parse_args()
    
    # Create the connector
    connector = FrontendConnector()
    
    print(f"""
🚀 Zion Market Analysis Platform - Frontend Connector

┌─────────────────────────────────────────────────────────────┐
│                    CONNECTION READY                         │
├─────────────────────────────────────────────────────────────┤
│  Backend URL: http://localhost:{args.port}                 │
│  Dashboard:   http://localhost:{args.port}                 │
│  API Docs:    http://localhost:{args.port}/docs            │
│  Health:      http://localhost:{args.port}/api/health      │
├─────────────────────────────────────────────────────────────┤
│  ✅ CORS Enabled for ALL origins                           │
│  ✅ Auto-documentation available                           │
│  ✅ Ready for ANY frontend framework                       │
│  ✅ Test endpoints available                               │
└─────────────────────────────────────────────────────────────┘

🔌 Quick Integration:
   • Open http://localhost:{args.port} for interactive dashboard
   • Copy integration code for your framework
   • Test API endpoints live
   • Get authentication tokens

📡 Available Endpoints:
   • POST /api/login - Authentication
   • GET  /api/analyze/{{symbol}} - Stock analysis
   • POST /api/analyze/enhanced - Advanced analysis
   • GET  /api/health - System health
   • GET  /api/v1/metrics - Performance metrics

🛠  Framework Examples Available:
   • React/Next.js
   • Vue/Nuxt
   • Angular
   • Svelte/SvelteKit
   • Vanilla JavaScript
   • And more...

Starting server...
    """)
    
    # Run the server
    uvicorn.run(
        connector.app,
        host=args.host,
        port=args.port,
        reload=args.dev,
        access_log=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
