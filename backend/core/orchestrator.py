from typing import Dict, List, Optional
from backend.agents.categories import CategoryManager, CategoryType
from backend.utils.monitoring import SystemMonitor
from backend.utils.cache_utils import redis_client
from backend.utils.metrics_collector import MetricsCollector
from datetime import datetime
import asyncio
from loguru import logger


class SystemOrchestrator:
    def __init__(self):
        self.category_manager = CategoryManager()
        self.system_monitor = SystemMonitor()
        self.metrics_collector = MetricsCollector()
        self.cache = redis_client
        self._initialize_system()

    def _initialize_system(self):
        """Initialize system components and verify connections"""
        self.system_monitor.register_component("orchestrator")
        self.category_dependencies = self._build_dependency_graph()
        logger.info("System orchestrator initialized")

    async def analyze_symbol(
        self,
        symbol: str,
        categories: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> Dict:
        """Run full analysis with advanced caching and error recovery"""
        analysis_id = f"{symbol}_{datetime.now().timestamp()}"
        try:
            self.system_monitor.start_analysis(analysis_id)

            # Check cache if not forced refresh
            if not force_refresh:
                cached = await self._get_cached_analysis(symbol)
                if cached:
                    return cached

            # Execute categories with dependency resolution
            results = {}
            executed_categories = set()
            categories = categories or self._get_default_categories()

            for category in self._get_execution_order(categories):
                if category in executed_categories:
                    continue

                try:
                    category_result = await self._execute_category_with_retry(
                        category, symbol, results
                    )
                    results[category] = category_result
                    executed_categories.add(category)

                    # Collect metrics
                    self.metrics_collector.record_category_execution(
                        category,
                        len(category_result),
                        bool(category_result.get("error")),
                    )

                except Exception as e:
                    logger.error(f"Category {category} failed: {e}")
                    results[category] = {"error": str(e)}

            # Generate final verdict
            final_verdict = self._generate_composite_verdict(results)
            system_health = self.system_monitor.get_health_metrics()

            # Cache results
            await self._cache_analysis(symbol, final_verdict)

            self.system_monitor.end_analysis(analysis_id, "success")
            return {
                "symbol": symbol,
                "analysis_id": analysis_id,
                "verdict": final_verdict,
                "category_results": results,
                "system_health": system_health,
                "execution_metrics": self.metrics_collector.get_metrics(),
            }

        except Exception as e:
            self.system_monitor.end_analysis(analysis_id, "error")
            logger.error(f"System analysis failed for {symbol}: {e}")
            return {
                "symbol": symbol,
                "analysis_id": analysis_id,
                "error": str(e),
                "system_health": self.system_monitor.get_health_metrics(),
            }

    async def _execute_category_with_retry(
        self, category: str, symbol: str, results: Dict, max_retries: int = 3
    ) -> Dict:
        """Execute category with retry logic"""
        for attempt in range(max_retries):
            try:
                return await self.category_manager.execute_category(
                    category, symbol, results
                )
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))

    def _get_execution_order(self, categories: List[str]) -> List[str]:
        """Get optimized execution order based on dependencies"""
        order = []
        visited = set()

        def visit(category):
            if category in visited:
                return
            visited.add(category)
            for dep in self.category_dependencies.get(category, []):
                visit(dep)
            order.append(category)

        for category in categories:
            visit(category)
        return order

    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build category dependency graph"""
        dependencies = {}
        for category in CategoryType:
            deps = self.category_manager.get_dependencies(category)
            # Convert dependency strings to CategoryType values
            dependencies[category.value] = [CategoryType[d].value for d in deps]
        return dependencies

    async def _get_cached_analysis(self, symbol: str) -> Optional[Dict]:
        """Get cached analysis if available"""
        cache_key = f"analysis:{symbol}"
        return await self.cache.get(cache_key)

    async def _cache_analysis(self, symbol: str, analysis: Dict):
        """Cache analysis results"""
        cache_key = f"analysis:{symbol}"
        await self.cache.set(cache_key, analysis, ex=3600)  # 1 hour expiry

    def _get_default_categories(self) -> List[str]:
        """Get default categories for analysis"""
        return [cat.value for cat in CategoryType]

    def _generate_composite_verdict(self, results: Dict) -> Dict:
        """Generate weighted composite verdict"""
        try:
            # Calculate weighted scores
            category_weights = self.category_manager.get_category_weights()
            scores = []
            weights = []

            for category, result in results.items():
                if "error" not in result:
                    score = result.get("confidence", 0)
                    weight = category_weights.get(category, 1.0)
                    scores.append(score)
                    weights.append(weight)

            if not scores:
                return {"verdict": "INSUFFICIENT_DATA", "confidence": 0}

            # Calculate weighted average
            composite_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)

            # Determine verdict
            if composite_score > 0.7:
                verdict = "STRONG_BUY"
            elif composite_score > 0.5:
                verdict = "BUY"
            elif composite_score > 0.3:
                verdict = "HOLD"
            else:
                verdict = "SELL"

            return {
                "verdict": verdict,
                "confidence": round(composite_score, 4),
                "category_weights": category_weights,
            }

        except Exception as e:
            logger.error(f"Composite verdict generation failed: {e}")
            return {"verdict": "ERROR", "confidence": 0}
