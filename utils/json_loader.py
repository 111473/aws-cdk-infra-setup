import json
import os


class JsonLoader:
    @staticmethod
    def load_json(file_path: str) -> dict:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        with open(file_path, "r") as f:
            return json.load(f)
