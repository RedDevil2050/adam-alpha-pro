from typing import Dict, List, Optional
from backend.agents.categories import CategoryManager, CategoryType
# Correct the import path for SystemMonitor
from backend.utils.system_monitor import SystemMonitor
from backend.utils.metrics_collector import MetricsCollector
from datetime import datetime
import asyncio
from loguru import logger


class SystemOrchestrator:
    def __init__(self, cache_client):
        self.category_manager = CategoryManager()
        self.cache = cache_client
        self.category_dependencies: Dict[str, List[str]] = {}

    async def initialize(self, monitor: SystemMonitor):
        """Initialize orchestrator components and update status."""
        component_name = "orchestrator"
        try:
            self.category_dependencies = self._build_dependency_graph()
            # Add any other orchestrator-specific async setup here
            # await some_orchestrator_setup()
            logger.info("System orchestrator initialized")
            monitor.update_component_status(component_name, "healthy")
        except Exception as e:
            logger.error(f"Orchestrator initialization failed: {e}")
            monitor.update_component_status(component_name, "failed")
            raise

    async def analyze_symbol(
        self,
        symbol: str,
        monitor: SystemMonitor,
        metrics_collector: MetricsCollector,
        categories: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> Dict:
        """Run full analysis with advanced caching and error recovery"""
        analysis_id = f"{symbol}_{datetime.now().timestamp()}"
        try:
            monitor.start_analysis(analysis_id)

            # Check cache if not forced refresh
            if not force_refresh:
                cached = await self._get_cached_analysis(symbol)
                if cached:
                    return cached

            # Execute categories with dependency resolution
            results = {}
            executed_categories = set()
            categories = categories or self._get_default_categories()

            for category_value in self._get_execution_order(categories): # Use category_value
                if category_value in executed_categories:
                    continue

                category_enum = CategoryType(category_value) # Get Enum member

                try:
                    # Execute category returns a List[Dict] of agent results
                    agent_results_list = await self._execute_category_with_retry(
                        category_enum, symbol, results # Pass Enum member
                    )

                    # Store the list of results directly
                    # Check if any agent within the list reported an error
                    category_had_errors = any(res.get("error") for res in agent_results_list)
                    num_results = len(agent_results_list)

                    # Store results in a standard dictionary format for the category
                    results[category_value] = {
                        "results": agent_results_list,
                        "error": "Category executed with internal agent errors." if category_had_errors else None,
                        "count": num_results
                    }
                    executed_categories.add(category_value)

                    # Collect metrics based on whether any agent failed
                    metrics_collector.record_category_execution(
                        category_value,
                        num_results,
                        category_had_errors, # True if any agent had an error
                    )

                except Exception as e:
                    logger.error(f"Category {category_value} failed during execution: {e}", exc_info=True) # Add traceback
                    # Store a category-level error
                    results[category_value] = {"error": f"Category execution failed: {str(e)}", "results": []}
                    executed_categories.add(category_value) # Mark as executed even if failed
                    metrics_collector.record_category_execution(category_value, 0, True) # Record failure

            # Generate final verdict
            final_verdict = self._generate_composite_verdict(results)
            system_health = monitor.get_health_metrics()

            # Cache results
            await self._cache_analysis(symbol, final_verdict)

            monitor.end_analysis(analysis_id, "success")
            return {
                "symbol": symbol,
                "analysis_id": analysis_id,
                "verdict": final_verdict,
                "category_results": results,
                "system_health": system_health,
                "execution_metrics": metrics_collector.get_metrics(),
            }

        except Exception as e:
            monitor.end_analysis(analysis_id, "error")
            logger.error(f"System analysis failed for {symbol}: {e}")
            return {
                "symbol": symbol,
                "analysis_id": analysis_id,
                "error": str(e),
                "system_health": monitor.get_health_metrics(),
            }

    async def _execute_category_with_retry(
        self, category: CategoryType, symbol: str, results: Dict, max_retries: int = 3 # Expect Enum member
    ) -> List[Dict]: # Return type is List[Dict]
        """Execute category with retry logic"""
        for attempt in range(max_retries):
            try:
                # Pass Enum member to execute_category
                return await self.category_manager.execute_category(
                    category, symbol, results
                )
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for category {category.value} on {symbol}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Category {category.value} failed after {max_retries} attempts for {symbol}.", exc_info=True)
                    raise # Re-raise the exception to be caught in analyze_symbol
                await asyncio.sleep(1 * (attempt + 1))
        # Should not be reached if max_retries > 0
        return []

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
        for category_enum_member in CategoryType:  # Iterate through Enum members
            # Get dependency names (e.g., ["MARKET", "TECHNICAL"])
            dep_names = self.category_manager.get_dependencies(category_enum_member)
            dep_values = []
            for name in dep_names:
                try:
                    # Look up Enum member by name (e.g., CategoryType["MARKET"])
                    dependency_enum_member = CategoryType[name]
                    # Get the value of the Enum member (e.g., "market")
                    dep_values.append(dependency_enum_member.value)
                except KeyError:
                    # Log error if a dependency name doesn't match an Enum member
                    logger.error(
                        f"Invalid category dependency name '{name}' found for {category_enum_member.name}. Skipping dependency."
                    )
                    # Decide how to handle: skip, raise, etc. Skipping for now.
                    continue
            # Map the *value* of the current category (e.g., "valuation")
            # to the list of dependency *values* (e.g., ["market", "technical"])
            dependencies[category_enum_member.value] = dep_values
        return dependencies

    async def _get_cached_analysis(self, symbol: str) -> Optional[Dict]:
        """Get cached analysis if available"""
        cache_key = f"analysis:{symbol}"
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            # Assuming data is stored as JSON string
            import json

            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to decode cached JSON for {symbol}")
                return None
        return None

    async def _cache_analysis(self, symbol: str, analysis: Dict):
        """Cache analysis results"""
        cache_key = f"analysis:{symbol}"
        import json

        try:
            await self.cache.set(cache_key, json.dumps(analysis), ex=3600)  # 1 hour expiry
        except Exception as e:
            logger.error(f"Failed to cache analysis for {symbol}: {e}")

    def _get_default_categories(self) -> List[str]:
        """Get default categories for analysis"""
        return [cat.value for cat in CategoryType]

    def _generate_composite_verdict(self, results: Dict) -> Dict:
        """Generate weighted composite verdict"""
        try:
            category_weights = self.category_manager.get_category_weights()
            scores = []
            weights = []
            contributing_categories = {}

            for category_value, category_data in results.items():
                # Check if the category itself had a top-level execution error
                if category_data.get("error") and not category_data.get("results"):
                    logger.warning(f"Skipping category {category_value} in composite verdict due to execution error: {category_data['error']}")
                    continue

                # Process individual agent results within the category
                agent_results = category_data.get("results", [])
                category_scores = []
                for agent_result in agent_results:
                    # Only include successful agent results with a confidence score
                    if not agent_result.get("error") and "confidence" in agent_result:
                        category_scores.append(agent_result["confidence"])

                if category_scores: # Only include category if it had successful agents
                    # Simple average confidence for the category
                    category_avg_score = sum(category_scores) / len(category_scores)
                    weight = category_weights.get(category_value, 0.0) # Default weight 0 if not found
                    if weight > 0:
                        scores.append(category_avg_score)
                        weights.append(weight)
                        contributing_categories[category_value] = round(category_avg_score, 4)
                    else:
                         logger.warning(f"Category {category_value} has zero weight, excluding from composite score.")
                else:
                    logger.warning(f"Category {category_value} had no successful agent results with confidence, excluding from composite score.")

            if not scores or sum(weights) == 0:
                logger.warning("No valid category scores or total weight is zero for composite verdict.")
                return {"verdict": "INSUFFICIENT_DATA", "confidence": 0, "details": {"reason": "No contributing categories or zero total weight"}}

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
                "details": {
                    "contributing_categories": contributing_categories,
                    "category_weights_used": {cat: w for cat, w in category_weights.items() if w > 0 and cat in contributing_categories}
                }
            }

        except AttributeError as ae:
             # Catch potential missing 'get_category_weights'
             logger.error(f"Composite verdict generation failed: Missing method 'get_category_weights' on CategoryManager? Error: {ae}", exc_info=True)
             return {"verdict": "ERROR", "confidence": 0, "details": {"reason": f"Internal error: {ae}"}}
        except Exception as e:
            logger.error(f"Composite verdict generation failed: {e}", exc_info=True)
            return {"verdict": "ERROR", "confidence": 0, "details": {"reason": f"Internal error: {e}"}}
