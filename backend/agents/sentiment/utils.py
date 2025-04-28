from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from backend.utils.progress_tracker import ProgressTracker

# Shared tracker instance
tracker = ProgressTracker(filepath="backend/utils/progress.json")

# Initialize VADER analyzer
analyzer = SentimentIntensityAnalyzer()


def normalize_compound(compound: float) -> float:
    """
    Normalize VADER compound score (-1 to 1) to (0 to 1).
    """
    return (compound + 1) / 2
