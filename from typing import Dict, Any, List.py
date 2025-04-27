from typing import Dict, Any, List
from .monitoring.metrics import metrics_collector
from .config.settings import get_settings
from datetime import datetime

class Brain:
    def __init__(self):
        self.settings = get_settings()
        self.metrics = metrics_collector
        self.weights = {
            'technical': 0.3,
            'fundamental': 0.3,
            'sentiment': 0.2,
            'market': 0.1,
            'news': 0.1
        }
        
    async def analyze_results(self, agent_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        try:
            start_time = datetime.utcnow()
            
            # Calculate scores per category with confidence
            category_scores = {}
            confidence_levels = {}
            
            for category, results in agent_results.items():
                score, confidence = self._process_category(category, results)
                category_scores[category] = score
                confidence_levels[category] = confidence
                
                # Record metrics
                self.metrics.record_category_score(category, score, confidence)
            
            # Calculate final weighted score
            final_score = self._calculate_weighted_score(category_scores, confidence_levels)
            
            # Record processing metrics
            self.metrics.record_brain_processing_time(
                (datetime.utcnow() - start_time).total_seconds()
            )
            
            return {
                "score": final_score,
                "category_scores": category_scores,
                "confidence_levels": confidence_levels,
                "weights": self.weights,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            self.metrics.record_brain_error(str(e))
            raise

    def _process_category(self, category: str, results: List[Dict[str, Any]]) -> tuple:
        valid_results = [r for r in results if self._is_valid_result(r)]
        if not valid_results:
            return 0.0, 0.0
            
        total_score = 0
        total_confidence = 0
        
        for result in valid_results:
            score = result.get('score', 0)
            confidence = result.get('confidence', 0.5)
            total_score += score * confidence
            total_confidence += confidence
            
        if total_confidence > 0:
            return (total_score / total_confidence, 
                   total_confidence / len(valid_results))
        return 0.0, 0.0

    def _calculate_weighted_score(self, 
                                scores: Dict[str, float], 
                                confidences: Dict[str, float]) -> float:
        weighted_sum = 0
        total_weight = 0
        
        for category in scores:
            weight = self.weights.get(category, 0)
            confidence = confidences[category]
            score = scores[category]
            
            weighted_sum += score * weight * confidence
            total_weight += weight * confidence
        
        return weighted_sum / total_weight if total_weight > 0 else 0

    def _is_valid_result(self, result: Dict[str, Any]) -> bool:
        return (
            isinstance(result.get('score'), (int, float)) and
            isinstance(result.get('confidence'), (int, float)) and
            0 <= result['score'] <= 100 and
            0 <= result['confidence'] <= 1
        )
