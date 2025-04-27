from locust import HttpUser, task, between
from random import choice

class AnalysisUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login to get token
        response = self.client.post("/auth/token", 
            data={"username": "test", "password": "test"})
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(1)
    def analyze_symbol(self):
        symbol = choice(['AAPL', 'MSFT', 'GOOGL', 'AMZN'])
        self.client.post(
            "/analyze",
            headers=self.headers,
            json={"symbol": symbol, "analysis_type": "quick"}
        )
    
    @task(2)
    def get_market_data(self):
        symbol = choice(['AAPL', 'MSFT', 'GOOGL', 'AMZN'])
        self.client.get(f"/market-data/{symbol}", headers=self.headers)
