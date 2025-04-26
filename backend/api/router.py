from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.core.orchestrator import SystemOrchestrator
from backend.utils.monitoring import SystemMonitor
from typing import List, Optional

router = APIRouter()
orchestrator = SystemOrchestrator()
system_monitor = SystemMonitor()

@router.get("/analyze/{symbol}")
async def analyze_stock(symbol: str, categories: Optional[List[str]] = None):
    try:
        return await orchestrator.analyze_symbol(symbol, categories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    metrics = system_monitor.get_health_metrics()
    return {
        "status": "healthy" if metrics["system"]["cpu_usage"] < 80 else "degraded",
        "metrics": metrics
    }

@router.post("/batch-analyze")
async def batch_analyze(symbols: List[str], background_tasks: BackgroundTasks):
    task_id = f"batch_{len(symbols)}_{int(time.time())}"
    background_tasks.add_task(orchestrator.analyze_symbols, symbols)
    return {"task_id": task_id, "status": "processing"}
