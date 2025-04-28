from backend.agents.nlp.nlp_topic_agent import run as run_topic
from backend.agents.nlp.nlp_summary_agent import run as run_summary


def run_nlp_insights(symbol: str, agent_outputs: dict) -> dict:
    topic_output = run_topic(symbol, agent_outputs)
    summary_output = run_summary(symbol, agent_outputs)

    return {
        "symbol": symbol,
        "nlp": {
            "topics": topic_output.get("topics", []),
            "summary": summary_output.get("summary", ""),
            "errors": {
                "topic": topic_output.get("error"),
                "summary": summary_output.get("error"),
            },
        },
    }
