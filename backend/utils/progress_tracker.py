import json
import os
import shutil
from datetime import datetime
from threading import Lock


class ProgressTracker:
    """
    Tracks progress of agent implementations and pipeline execution.
    Saves to a JSON file and maintains timestamped backups.
    """

    def __init__(
        self,
        filepath="backend/utils/progress.json",
        backup_dir="backend/utils/progress_backups",
    ):
        self.filepath = filepath
        self.backup_dir = backup_dir
        self._lock = Lock()
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        if not os.path.isfile(self.filepath):
            self._write({"categories": {}, "last_updated": None})

    def _read(self):
        with open(self.filepath, "r") as f:
            return json.load(f)

    def _write(self, data):
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2)

    def backup(self):
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        backup_path = os.path.join(self.backup_dir, f"progress_{timestamp}.json")
        shutil.copy2(self.filepath, backup_path)

    def update(self, category: str, agent: str, status: str):
        with self._lock:
            data = self._read()
            cats = data.setdefault("categories", {})
            agents = cats.setdefault(category, {})
            agents[agent] = status
            data["last_updated"] = datetime.utcnow().isoformat() + "Z"
            self.backup()
            self._write(data)

    def get_progress(self):
        return self._read()
