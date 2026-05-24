import logging
import os
from pathlib import Path


SCRIPT_VERSION = '0.2'
SIGNATURE_ARCHITECTURE_VERSION = 2
DEFAULT_API_ROOT = 'https://repository.library.brown.edu/api/'
DEFAULT_USER_AGENT = 'BDRArchitectureSampler/0.1 (Brown University Library internal planning)'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT.parent / 'bdr_standard_architectures_output'
DEFAULT_OUTPUT_JSON = str(DEFAULT_OUTPUT_ROOT / 'common_architectures.json')
DEFAULT_OUTPUT_MD = str(DEFAULT_OUTPUT_ROOT / 'common_architectures.md')
DEFAULT_SPECIFICATIONS_DIR = str(PROJECT_ROOT / 'specifications')
DEFAULT_CACHE_DIR = str(DEFAULT_OUTPUT_ROOT / 'architecture_cache')
DEFAULT_STATE_FILE = str(DEFAULT_OUTPUT_ROOT / 'architecture_cache' / 'run_state.json')
DEFAULT_SLEEP_SECONDS = 2.0
DEFAULT_MAX_CHILDREN_PER_PARENT = 100
MAX_CHILDREN_PER_PARENT_CAP = 1000
LOG_LEVEL = logging.DEBUG if os.getenv('LOG_LEVEL') == 'DEBUG' else logging.INFO
