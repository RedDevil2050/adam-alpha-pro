import json
import os

CHECKPOINT_FILE = os.getenv("CHECKPOINT_FILE", "checkpoint.json")


def load_checkpoint() -> dict:
    """
    Load the last saved checkpoint (symbol and agent).
    """
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {}


def save_checkpoint(data: dict):
    """
    Save the current checkpoint to disk.
    """
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f)
