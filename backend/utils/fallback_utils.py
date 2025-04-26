
def fallback_pipeline(data):
    try:
        # Main execution
        return data["result"]
    except KeyError:
        return "FALLBACK_RESULT"
