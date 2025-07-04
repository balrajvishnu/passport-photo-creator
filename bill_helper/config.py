import os
import yaml

def get_config(path=None):
    # Default config path
    if path is None:
        path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    config = {}
    # Load from YAML if it exists
    if os.path.exists(path):
        with open(path, 'r') as f:
            config = yaml.safe_load(f) or {}
    # Override with environment variables if present
    config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', config.get('OPENAI_API_KEY'))
    config['AZURE_SPEECH_KEY'] = os.getenv('AZURE_SPEECH_KEY', config.get('AZURE_SPEECH_KEY'))
    config['AZURE_SPEECH_REGION'] = os.getenv('AZURE_SPEECH_REGION', config.get('AZURE_SPEECH_REGION'))
    return config 