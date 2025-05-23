from typing import Dict, List, Optional
from backend.agents.categories import CategoryManager, CategoryType
# Correct the import path for SystemMonitor
from backend.utils.system_monitor import SystemMonitor
from backend.utils.metrics_collector import MetricsCollector
from datetime import datetime
import asyncio
from loguru import logger
import time # Ensure time is imported
import json
from datetime import datetime # Ensure datetime is imported

# Helper function for JSON serialization
def json_serializer(obj):
    logger.debug(f"json_serializer attempting to serialize object of type: {type(obj)}") # Ensure logging is active
    if isinstance(obj, datetime):
        return obj.isoformat()
    try:
        # Attempt to import pandas and check for Timestamp type
        # This is to handle cases where pandas Timestamps might be in the data
        import pandas as pd
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
    except ImportError:
        pass # Pandas is not installed or used, so no need to handle its Timestamp

    # Let other types raise TypeError to be caught by the caller if not handled
    raise TypeError(f"Object of type {type(obj).__name__} (value: {str(obj)[:100]}) is not JSON serializable")


class SystemOrchestrator:
    def __init__(self, cache_client):
        self.category_manager = CategoryManager()
        self.cache = cache_client
        self.category_dependencies: Dict[str, List[str]] = {}
        # Initialize internal monitor and metrics collector
        # These are now imported at the module level
        self.system_monitor = SystemMonitor()
        self.metrics_collector = MetricsCollector()

    async def initialize(self, monitor: SystemMonitor):
        """Initialize orchestrator components and update status."""
        component_name = "orchestrator"
        try:
            # Register the component first on the passed-in monitor
            monitor.register_component(component_name)
            # Also register on the internal monitor
            self.system_monitor.register_component(component_name)

            self.category_dependencies = self._build_dependency_graph()
            # Add any other orchestrator-specific async setup here
            # await some_orchestrator_setup()
            logger.info("System orchestrator initialized")
            monitor.update_component_status(component_name, "healthy")
            self.system_monitor.update_component_status(component_name, "healthy") # Update internal monitor
        except Exception as e:
            logger.error(f"Orchestrator initialization failed: {e}")
            # Ensure component is registered before updating status to failed on passed-in monitor
            monitor.register_component(component_name) 
            monitor.update_component_status(component_name, "failed")
            # Ensure component is registered and updated on internal monitor in case of failure
            self.system_monitor.register_component(component_name)
            self.system_monitor.update_component_status(component_name, "failed")
            raise

    async def analyze_symbol(
        self,
        symbol: str,
        categories: Optional[List[str]] = None,
        force_refresh: bool = False,
        monitor: SystemMonitor = None,  # Accept monitor for compatibility
    ) -> Dict:
        """Run full analysis with advanced caching and error recovery"""
        analysis_id = f"{symbol}_{datetime.now().timestamp()}"
        start_time = time.perf_counter() # Record start time
        try:
            await self.system_monitor.start_analysis(analysis_id)

            # Check cache if not forced refresh
            if not force_refresh:
                cached = await self._get_cached_analysis(symbol)
                if cached:
                    return cached

            # Execute categories with dependency resolution
            results = {}
            executed_categories = set()
            categories_to_run = categories or self._get_default_categories() # Use a different variable name

            for category_value in self._get_execution_order(categories_to_run): # Use the correct variable
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
                    self.metrics_collector.record_category_execution(
                        category_value,
                        num_results,
                        category_had_errors,
                    )

                except Exception as e:
                    logger.error(f"Category {category_value} failed during execution: {e}", exc_info=True) # Add traceback
                    # Store a category-level error
                    results[category_value] = {"error": f"Category execution failed: {str(e)}", "results": []}
                    executed_categories.add(category_value) # Mark as executed even if failed
                    self.metrics_collector.record_category_execution(category_value, 0, True) # Record failure

            # Generate final verdict
            final_verdict = self._generate_composite_verdict(results)
            system_health = await self.system_monitor.get_health_metrics() # Use internal monitor

            # Record end time and duration BEFORE getting metrics
            end_time = time.perf_counter() 
            duration = end_time - start_time
            self.metrics_collector.record_response_time(duration)

            # Construct the full response before caching
            successful_response = {
                "symbol": symbol,
                "analysis_id": analysis_id,
                "verdict": final_verdict,
                "category_results": results,
                "system_health": system_health,
                "execution_metrics": self.metrics_collector.get_metrics(), # Now get_metrics will include current duration
            }

            # Cache the full successful response
            await self._cache_analysis(symbol, successful_response)

            await self.system_monitor.end_analysis(analysis_id, "success") # Use internal monitor
            return successful_response

        except Exception as e:
            # Record end time and duration BEFORE getting metrics in error path too
            end_time = time.perf_counter() 
            duration = end_time - start_time
            self.metrics_collector.record_response_time(duration) 

            await self.system_monitor.end_analysis(analysis_id, "error") # Use internal monitor
            logger.error(f"System analysis failed for {symbol}: {e}", exc_info=True) # Add traceback

            # Fetch health metrics even on error
            try:
                system_health_on_error = await self.system_monitor.get_health_metrics()
            except Exception as monitor_err:
                logger.error(f"Failed to get health metrics during error handling: {monitor_err}")
                system_health_on_error = {"error": "Failed to retrieve health metrics"}

            return {
                "symbol": symbol,
                "analysis_id": analysis_id,
                "error": str(e),
                "system_health": system_health_on_error, # Include health on error
                "execution_metrics": self.metrics_collector.get_metrics(), # Include metrics on error
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

    async def _cache_analysis(self, symbol: str, full_analysis_result: Dict):
        """Cache analysis results"""
        cache_key = f"analysis:{symbol}"
        # import json # Already imported at the top

        try:
            # Use the custom serializer for datetime objects
            await self.cache.set(cache_key, json.dumps(full_analysis_result, default=json_serializer), ex=3600)  # 1 hour expiry
        except Exception as e:
            logger.error(f"Failed to cache analysis for {symbol}: {e}")

    def _get_default_categories(self) -> List[str]:
        """Get default categories for analysis"""
        return [cat.value for cat in CategoryType]

    def _generate_composite_verdict(self, results: Dict) -> Dict:
        """Generate weighted composite verdict"""
        try:
            # Call get_category_weights as a class method
            category_weights = CategoryManager.get_category_weights()
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
