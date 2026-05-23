import logging
import os


SCRIPT_VERSION = '0.1'
DEFAULT_API_ROOT = 'https://repository.library.brown.edu/api/'
DEFAULT_USER_AGENT = 'BDRArchitectureSampler/0.1 (Brown University Library internal planning)'
LOG_LEVEL = logging.DEBUG if os.getenv('LOG_LEVEL') == 'DEBUG' else logging.INFO
