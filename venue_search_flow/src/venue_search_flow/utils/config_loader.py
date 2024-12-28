import yaml
from typing import Dict, Any

def load_yaml_config(path: str) -> Dict[str, Any]:
    """Load and parse a YAML configuration file"""
    with open(path, 'r') as file:
        return yaml.safe_load(file) 