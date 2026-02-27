import json
import os

class LearningStore:
    FILE = "learning_store.json"

    def __init__(self):
        if not os.path.exists(self.FILE):
            with open(self.FILE, "w") as f:
                json.dump({}, f)

    def record(self, cause, success: bool):
        data = self._load()

        if cause not in data:
            data[cause] = {"hits": 0, "correct": 0}

        data[cause]["hits"] += 1
        if success:
            data[cause]["correct"] += 1

        self._save(data)

    def confidence(self, cause):
        data = self._load()
        if cause not in data or data[cause]["hits"] == 0:
            return 0.5   # neutral confidence

        return round(data[cause]["correct"] / data[cause]["hits"], 2)

    def _load(self):
        with open(self.FILE) as f:
            return json.load(f)

    def _save(self, data):
        with open(self.FILE, "w") as f:
            json.dump(data, f, indent=2)

