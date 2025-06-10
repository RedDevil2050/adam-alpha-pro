#!/usr/bin/env python3
"""
Zion Market Analysis Platform - Universal Frontend Connector
One-click solution to connect any frontend to the Zion backend
"""

import asyncio
import json
import os
import sys
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import psutil

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

try:
    from backend.api.main import app as backend_app
    from backend.config.settings import get_settings
    from backend.utils.cache_utils import get_redis_client
except ImportError as e:
    print(f"Backend import error: {e}")
    print("Please ensure backend dependencies are installed")
    sys.exit(1)

class ZionConnector:
    def __init__(self):
        self.backend_port = 8000
        self.frontend_port = 3000
        self.connector_port = 8080
        self.settings = get_settings()
        self.processes = {}
        
    def create_connector_app(self):
        """Create the universal connector FastAPI app"""
        app = FastAPI(
            title="Zion Frontend Connector",
            description="Universal connector for any frontend to Zion backend",
            version="1.0.0"
        )
        
        # Enable CORS for all origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @app.get("/")
        async def connector_home():
            return HTMLResponse(self.get_connector_homepage())
        
        @app.get("/api/connector/status")
        async def connector_status():
            """Get status of all services"""
            return {
                "connector": {"status": "running", "port": self.connector_port},
                "backend": await self.check_backend_status(),
                "frontend": await self.check_frontend_status(),
                "timestamp": datetime.now().isoformat()
            }
        
        @app.get("/api/connector/integration-guide")
        async def integration_guide():
            """Get integration guide for different frontend frameworks"""
            return {
                "react": self.get_react_integration(),
                "vue": self.get_vue_integration(),
                "angular": self.get_angular_integration(),
                "vanilla": self.get_vanilla_integration(),
                "nextjs": self.get_nextjs_integration()
            }
        
        @app.post("/api/connector/test-connection")
        async def test_connection(request: Request):
            """Test connection from frontend"""
            client_host = request.client.host
            return {
                "success": True,
                "message": "Connection successful!",
                "client_ip": client_host,
                "backend_url": f"http://localhost:{self.backend_port}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Proxy all /api requests to backend
        @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def proxy_to_backend(request: Request, path: str):
            """Proxy API requests to backend"""
            import httpx
            
            backend_url = f"http://localhost:{self.backend_port}/api/{path}"
            
            async with httpx.AsyncClient() as client:
                try:
                    # Forward the request to backend
                    response = await client.request(
                        method=request.method,
                        url=backend_url,
                        headers=dict(request.headers),
                        content=await request.body(),
                        params=request.query_params
                    )
                    
                    return Response(
                        content=response.content,
                        status_code=response.status_code,
                        headers=dict(response.headers)
                    )
                except Exception as e:
                    return JSONResponse(
                        status_code=500,
                        content={"error": f"Backend connection failed: {str(e)}"}
                    )
        
        return app
    
    def get_connector_homepage(self):
        """Generate the connector homepage HTML"""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Zion Frontend Connector</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: white;
                }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
                .header {{ text-align: center; margin-bottom: 3rem; }}
                .logo {{ font-size: 3rem; font-weight: bold; margin-bottom: 1rem; }}
                .subtitle {{ font-size: 1.2rem; opacity: 0.9; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 2rem; }}
                .card {{ 
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 1rem;
                    padding: 2rem;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }}
                .card h3 {{ margin-bottom: 1rem; color: #ffd700; }}
                .status {{ padding: 0.5rem 1rem; border-radius: 0.5rem; display: inline-block; margin: 0.5rem 0; }}
                .status.running {{ background: #4ade80; color: #000; }}
                .status.stopped {{ background: #ef4444; }}
                .btn {{ 
                    background: #ffd700;
                    color: #000;
                    border: none;
                    padding: 0.75rem 1.5rem;
                    border-radius: 0.5rem;
                    cursor: pointer;
                    font-weight: bold;
                    margin: 0.5rem 0.5rem 0.5rem 0;
                    text-decoration: none;
                    display: inline-block;
                }}
                .btn:hover {{ background: #fbbf24; }}
                .code {{ 
                    background: rgba(0, 0, 0, 0.3);
                    padding: 1rem;
                    border-radius: 0.5rem;
                    font-family: 'Courier New', monospace;
                    font-size: 0.9rem;
                    overflow-x: auto;
                    margin: 1rem 0;
                }}
                .endpoints {{ margin-top: 2rem; }}
                .endpoint {{ 
                    background: rgba(0, 0, 0, 0.2);
                    padding: 0.75rem;
                    margin: 0.5rem 0;
                    border-radius: 0.5rem;
                    font-family: monospace;
                }}
                .method {{ 
                    background: #10b981;
                    color: white;
                    padding: 0.25rem 0.5rem;
                    border-radius: 0.25rem;
                    font-size: 0.8rem;
                    margin-right: 0.5rem;
                }}
                .method.post {{ background: #f59e0b; }}
                .method.put {{ background: #8b5cf6; }}
                .method.delete {{ background: #ef4444; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🚀 Zion Frontend Connector</div>
                    <div class="subtitle">Universal connector for any frontend framework</div>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h3>🔗 Connection Status</h3>
                        <div>
                            <div id="backend-status" class="status">Backend: Checking...</div>
                            <div id="frontend-status" class="status">Frontend: Checking...</div>
                            <div class="status running">Connector: Running on :{self.connector_port}</div>
                        </div>
                        <button class="btn" onclick="checkStatus()">Refresh Status</button>
                        <a href="http://localhost:{self.backend_port}/docs" class="btn" target="_blank">API Docs</a>
                    </div>
                    
                    <div class="card">
                        <h3>⚡ Quick Start</h3>
                        <p>Your backend is ready! Connect any frontend:</p>
                        <div class="code">
                            // Base API URL
                            const API_URL = "http://localhost:{self.connector_port}";
                            
                            // Test connection
                            fetch(API_URL + "/api/connector/test-connection")
                        </div>
                        <a href="/api/connector/integration-guide" class="btn" target="_blank">Integration Guide</a>
                    </div>
                    
                    <div class="card">
                        <h3>🎯 Key Features</h3>
                        <ul style="list-style: none; padding-left: 0;">
                            <li>✅ 20+ AI Market Analysis Agents</li>
                            <li>✅ Real-time Stock Analysis</li>
                            <li>✅ Portfolio Optimization</li>
                            <li>✅ Risk Assessment</li>
                            <li>✅ Technical Indicators</li>
                            <li>✅ Sentiment Analysis</li>
                            <li>✅ Corporate Actions</li>
                            <li>✅ ESG Scoring</li>
                        </ul>
                    </div>
                    
                    <div class="card">
                        <h3>🛠️ Framework Examples</h3>
                        <button class="btn" onclick="showReactExample()">React</button>
                        <button class="btn" onclick="showVueExample()">Vue.js</button>
                        <button class="btn" onclick="showAngularExample()">Angular</button>
                        <button class="btn" onclick="showVanillaExample()">Vanilla JS</button>
                        
                        <div id="example-code" class="code" style="display: none;"></div>
                    </div>
                </div>
                
                <div class="endpoints">
                    <h3>🔌 Available Endpoints</h3>
                    <div class="endpoint">
                        <span class="method">GET</span>
                        <code>/api/analyze/{{symbol}}</code> - Analyze stock symbol
                    </div>
                    <div class="endpoint">
                        <span class="method post">POST</span>
                        <code>/api/analyze/enhanced</code> - Enhanced analysis with options
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span>
                        <code>/api/health</code> - System health check
                    </div>
                    <div class="endpoint">
                        <span class="method">GET</span>
                        <code>/api/v1/metrics</code> - System metrics
                    </div>
                    <div class="endpoint">
                        <span class="method post">POST</span>
                        <code>/api/login</code> - User authentication
                    </div>
                </div>
            </div>
            
            <script>
                async function checkStatus() {{
                    try {{
                        const response = await fetch('/api/connector/status');
                        const status = await response.json();
                        
                        document.getElementById('backend-status').textContent = 
                            `Backend: ${{status.backend.status}}`;
                        document.getElementById('backend-status').className = 
                            `status ${{status.backend.status === 'running' ? 'running' : 'stopped'}}`;
                            
                        document.getElementById('frontend-status').textContent = 
                            `Frontend: ${{status.frontend.status}}`;
                        document.getElementById('frontend-status').className = 
                            `status ${{status.frontend.status === 'running' ? 'running' : 'stopped'}}`;
                    }} catch (error) {{
                        console.error('Status check failed:', error);
                    }}
                }}
                
                function showReactExample() {{
                    document.getElementById('example-code').style.display = 'block';
                    document.getElementById('example-code').innerHTML = `
// React Integration Example
import React, {{ useState, useEffect }} from 'react';

const API_URL = 'http://localhost:{self.connector_port}';

function StockAnalysis() {{
  const [analysis, setAnalysis] = useState(null);
  
  const analyzeStock = async (symbol) => {{
    const response = await fetch(\`\${{API_URL}}/api/analyze/\${{symbol}}\`);
    const data = await response.json();
    setAnalysis(data);
  }};
  
  return (
    <div>
      <button onClick={{() => analyzeStock('AAPL')}}>
        Analyze AAPL
      </button>
      {{analysis && <pre>{{JSON.stringify(analysis, null, 2)}}</pre>}}
    </div>
  );
}}`;
                }}
                
                function showVueExample() {{
                    document.getElementById('example-code').style.display = 'block';
                    document.getElementById('example-code').innerHTML = `
<!-- Vue.js Integration Example -->
<template>
  <div>
    <button @click="analyzeStock('AAPL')">Analyze AAPL</button>
    <pre v-if="analysis">{{{{ JSON.stringify(analysis, null, 2) }}}}</pre>
  </div>
</template>

<script>
export default {{
  data() {{
    return {{
      analysis: null
    }}
  }},
  methods: {{
    async analyzeStock(symbol) {{
      const response = await fetch(\`http://localhost:{self.connector_port}/api/analyze/\${{symbol}}\`);
      this.analysis = await response.json();
    }}
  }}
}}
</script>`;
                }}
                
                function showAngularExample() {{
                    document.getElementById('example-code').style.display = 'block';
                    document.getElementById('example-code').innerHTML = `
// Angular Integration Example
import {{ Component, OnInit }} from '@angular/core';
import {{ HttpClient }} from '@angular/common/http';

@Component({{
  selector: 'app-stock-analysis',
  template: \`
    <button (click)="analyzeStock('AAPL')">Analyze AAPL</button>
    <pre *ngIf="analysis">{{{{ analysis | json }}}}</pre>
  \`
}})
export class StockAnalysisComponent {{
  analysis: any = null;
  
  constructor(private http: HttpClient) {{}}
  
  analyzeStock(symbol: string) {{
    this.http.get(\`http://localhost:{self.connector_port}/api/analyze/\${{symbol}}\`)
      .subscribe(data => this.analysis = data);
  }}
}}`;
                }}
                
                function showVanillaExample() {{
                    document.getElementById('example-code').style.display = 'block';
                    document.getElementById('example-code').innerHTML = `
// Vanilla JavaScript Integration Example
const API_URL = 'http://localhost:{self.connector_port}';

async function analyzeStock(symbol) {{
  try {{
    const response = await fetch(\`\${{API_URL}}/api/analyze/\${{symbol}}\`);
    const analysis = await response.json();
    
    document.getElementById('results').innerHTML = 
      \`<pre>\${{JSON.stringify(analysis, null, 2)}}</pre>\`;
  }} catch (error) {{
    console.error('Analysis failed:', error);
  }}
}}

// HTML
// <button onclick="analyzeStock('AAPL')">Analyze AAPL</button>
// <div id="results"></div>`;
                }}
                
                // Check status on page load
                checkStatus();
                setInterval(checkStatus, 30000); // Refresh every 30 seconds
            </script>
        </body>
        </html>
        """
    
    async def check_backend_status(self):
        """Check if backend is running"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{self.backend_port}/api/health", timeout=5)
                return {"status": "running", "port": self.backend_port}
        except:
            return {"status": "stopped", "port": self.backend_port}
    
    async def check_frontend_status(self):
        """Check if frontend is running"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{self.frontend_port}", timeout=5)
                return {"status": "running", "port": self.frontend_port}
        except:
            return {"status": "stopped", "port": self.frontend_port}
    
    def get_react_integration(self):
        """Get React integration code and setup"""
        return {
            "setup": [
                "npm create react-app my-zion-app",
                "cd my-zion-app",
                "npm install axios react-query"
            ],
            "api_service": """
// services/api.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export const analyzeStock = async (symbol) => {
  const response = await api.get(`/api/analyze/${symbol}`);
  return response.data;
};

export const getMarketHealth = async () => {
  const response = await api.get('/api/health');
  return response.data;
};

export default api;
            """,
            "component_example": """
// components/StockAnalyzer.js
import React, { useState } from 'react';
import { analyzeStock } from '../services/api';

function StockAnalyzer() {
  const [symbol, setSymbol] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const result = await analyzeStock(symbol);
      setAnalysis(result);
    } catch (error) {
      console.error('Analysis failed:', error);
    }
    setLoading(false);
  };

  return (
    <div>
      <input 
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        placeholder="Enter stock symbol"
      />
      <button onClick={handleAnalyze} disabled={loading}>
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>
      {analysis && (
        <div>
          <h3>Analysis Results</h3>
          <pre>{JSON.stringify(analysis, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default StockAnalyzer;
            """
        }
    
    def get_vue_integration(self):
        """Get Vue.js integration code and setup"""
        return {
            "setup": [
                "npm create vue@latest my-zion-app",
                "cd my-zion-app",
                "npm install axios"
            ],
            "composable": """
// composables/useZionApi.js
import { ref } from 'vue'
import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8080',
  timeout: 30000
})

export function useZionApi() {
  const loading = ref(false)
  const error = ref(null)

  const analyzeStock = async (symbol) => {
    loading.value = true
    error.value = null
    try {
      const response = await api.get(`/api/analyze/${symbol}`)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    analyzeStock
  }
}
            """,
            "component_example": """
<!-- components/StockAnalyzer.vue -->
<template>
  <div>
    <input v-model="symbol" placeholder="Enter stock symbol" />
    <button @click="analyze" :disabled="loading">
      {{ loading ? 'Analyzing...' : 'Analyze' }}
    </button>
    <div v-if="analysis">
      <h3>Analysis Results</h3>
      <pre>{{ JSON.stringify(analysis, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useZionApi } from '../composables/useZionApi'

const symbol = ref('')
const analysis = ref(null)
const { loading, analyzeStock } = useZionApi()

const analyze = async () => {
  if (!symbol.value) return
  try {
    analysis.value = await analyzeStock(symbol.value)
  } catch (error) {
    console.error('Analysis failed:', error)
  }
}
</script>
            """
        }
    
    def get_angular_integration(self):
        """Get Angular integration code and setup"""
        return {
            "setup": [
                "ng new my-zion-app",
                "cd my-zion-app",
                "ng add @angular/material"
            ],
            "service": """
// services/zion-api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ZionApiService {
  private baseUrl = 'http://localhost:8080';

  constructor(private http: HttpClient) { }

  analyzeStock(symbol: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/analyze/${symbol}`);
  }

  getMarketHealth(): Observable<any> {
    return this.http.get(`${this.baseUrl}/api/health`);
  }
}
            """,
            "component_example": """
// components/stock-analyzer.component.ts
import { Component } from '@angular/core';
import { ZionApiService } from '../services/zion-api.service';

@Component({
  selector: 'app-stock-analyzer',
  template: `
    <div>
      <mat-form-field>
        <input matInput [(ngModel)]="symbol" placeholder="Stock Symbol">
      </mat-form-field>
      <button mat-button (click)="analyze()" [disabled]="loading">
        {{ loading ? 'Analyzing...' : 'Analyze' }}
      </button>
      <div *ngIf="analysis">
        <h3>Analysis Results</h3>
        <pre>{{ analysis | json }}</pre>
      </div>
    </div>
  `
})
export class StockAnalyzerComponent {
  symbol = '';
  analysis: any = null;
  loading = false;

  constructor(private zionApi: ZionApiService) {}

  analyze() {
    if (!this.symbol) return;
    
    this.loading = true;
    this.zionApi.analyzeStock(this.symbol).subscribe({
      next: (result) => {
        this.analysis = result;
        this.loading = false;
      },
      error: (error) => {
        console.error('Analysis failed:', error);
        this.loading = false;
      }
    });
  }
}
            """
        }
    
    def get_vanilla_integration(self):
        """Get vanilla JavaScript integration"""
        return {
            "html": """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zion Market Analysis</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        input, button { padding: 10px; margin: 5px; }
        .results { background: #f5f5f5; padding: 20px; margin-top: 20px; }
        pre { white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Zion Market Analysis</h1>
        <input type="text" id="symbolInput" placeholder="Enter stock symbol">
        <button onclick="analyzeStock()">Analyze</button>
        <div id="results" class="results" style="display: none;"></div>
    </div>

    <script src="app.js"></script>
</body>
</html>
            """,
            "javascript": """
// app.js
const API_URL = 'http://localhost:8080';

async function analyzeStock() {
    const symbol = document.getElementById('symbolInput').value;
    if (!symbol) return;

    const resultsDiv = document.getElementById('results');
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = '<p>Analyzing...</p>';

    try {
        const response = await fetch(`${API_URL}/api/analyze/${symbol}`);
        const analysis = await response.json();
        
        resultsDiv.innerHTML = `
            <h3>Analysis Results for ${symbol}</h3>
            <pre>${JSON.stringify(analysis, null, 2)}</pre>
        `;
    } catch (error) {
        resultsDiv.innerHTML = `<p>Error: ${error.message}</p>`;
    }
}

// Test connection on page load
async function testConnection() {
    try {
        const response = await fetch(`${API_URL}/api/connector/test-connection`, {
            method: 'POST'
        });
        const result = await response.json();
        console.log('Connection test:', result);
    } catch (error) {
        console.error('Connection failed:', error);
    }
}

window.onload = testConnection;
            """
        }
    
    def get_nextjs_integration(self):
        """Get Next.js integration code and setup"""
        return {
            "setup": [
                "npx create-next-app@latest my-zion-app",
                "cd my-zion-app",
                "npm install axios swr"
            ],
            "api_client": """
// lib/zion-api.js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8080',
  timeout: 30000,
});

export const zionApi = {
  analyzeStock: async (symbol) => {
    const response = await api.get(`/api/analyze/${symbol}`);
    return response.data;
  },
  
  getMarketHealth: async () => {
    const response = await api.get('/api/health');
    return response.data;
  },
  
  enhancedAnalysis: async (symbol, options = {}) => {
    const response = await api.post('/api/analyze/enhanced', {
      symbol,
      ...options
    });
    return response.data;
  }
};

export default api;
            """,
            "page_example": """
// pages/analysis.js
import { useState } from 'react';
import useSWR from 'swr';
import { zionApi } from '../lib/zion-api';

export default function Analysis() {
  const [symbol, setSymbol] = useState('');
  const [analysisSymbol, setAnalysisSymbol] = useState(null);

  const { data: analysis, error, isLoading } = useSWR(
    analysisSymbol ? `/api/analyze/${analysisSymbol}` : null,
    () => zionApi.analyzeStock(analysisSymbol)
  );

  const handleAnalyze = () => {
    if (symbol) {
      setAnalysisSymbol(symbol.toUpperCase());
    }
  };

  return (
    <div>
      <h1>Stock Analysis</h1>
      <div>
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Enter stock symbol"
        />
        <button onClick={handleAnalyze}>Analyze</button>
      </div>
      
      {isLoading && <p>Analyzing...</p>}
      {error && <p>Error: {error.message}</p>}
      {analysis && (
        <div>
          <h2>Results for {analysisSymbol}</h2>
          <pre>{JSON.stringify(analysis, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
            """
        }
    
    def start_backend(self):
        """Start the backend server"""
        print("🚀 Starting Zion Backend...")
        
        backend_cmd = [
            sys.executable, "-m", "uvicorn",
            "backend.api.main:app",
            "--host", "0.0.0.0",
            "--port", str(self.backend_port),
            "--reload"
        ]
        
        try:
            process = subprocess.Popen(
                backend_cmd,
                cwd=Path(__file__).parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes['backend'] = process
            print(f"✅ Backend started on http://localhost:{self.backend_port}")
            return True
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return False
    
    def start_frontend(self):
        """Start the React frontend if available"""
        frontend_path = Path(__file__).parent / "frontend"
        
        if not frontend_path.exists():
            print("ℹ️  No React frontend found. You can connect any frontend using the connector.")
            return False
            
        print("🎨 Starting React Frontend...")
        
        try:
            # Install dependencies if node_modules doesn't exist
            if not (frontend_path / "node_modules").exists():
                print("📦 Installing frontend dependencies...")
                subprocess.run(["npm", "install"], cwd=frontend_path, check=True)
            
            # Start the frontend
            process = subprocess.Popen(
                ["npm", "start"],
                cwd=frontend_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes['frontend'] = process
            print(f"✅ Frontend started on http://localhost:{self.frontend_port}")
            return True
        except Exception as e:
            print(f"❌ Failed to start frontend: {e}")
            return False
    
    def start_connector(self):
        """Start the connector server"""
        print("🔗 Starting Universal Frontend Connector...")
        
        app = self.create_connector_app()
        
        try:
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=self.connector_port,
                log_level="info"
            )
        except Exception as e:
            print(f"❌ Failed to start connector: {e}")
    
    def cleanup(self):
        """Cleanup all processes"""
        print("\n🛑 Shutting down all services...")
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {name} stopped")
            except:
                try:
                    process.kill()
                    print(f"🔥 {name} forcefully stopped")
                except:
                    pass
    
    async def run(self):
        """Run the complete connector system"""
        print("🌟 Zion Market Analysis Platform - Frontend Connector")
        print("=" * 60)
        
        # Start backend
        if not self.start_backend():
            return
        
        # Wait a moment for backend to initialize
        await asyncio.sleep(3)
        
        # Start frontend (optional)
        self.start_frontend()
        
        # Wait a moment for frontend to initialize
        await asyncio.sleep(2)
        
        # Open the connector in browser
        connector_url = f"http://localhost:{self.connector_port}"
        print(f"\n🌐 Opening connector at {connector_url}")
        webbrowser.open(connector_url)
        
        # Start connector (this will block)
        try:
            self.start_connector()
        except KeyboardInterrupt:
            self.cleanup()
        except Exception as e:
            print(f"❌ Connector error: {e}")
            self.cleanup()

def main():
    """Main entry point"""
    connector = ZionConnector()
    
    try:
        asyncio.run(connector.run())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
