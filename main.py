import argparse
import logging
from pathlib import Path

from lib.config import (
    DEFAULT_API_ROOT,
    DEFAULT_CACHE_DIR,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    DEFAULT_STATE_FILE,
    LOG_LEVEL,
)
from lib.report import render_markdown_report
from lib.sampler import run_sampler
from lib.utils import write_json, write_markdown


logging.basicConfig(
    level=LOG_LEVEL,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S',
)
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments.
    Called by: main()
    """
    parser = argparse.ArgumentParser(description='Determine common BDR object architectures.')
    parser.add_argument('--api-root', default=DEFAULT_API_ROOT)
    parser.add_argument('--max-collections', type=int, default=20)
    parser.add_argument('--max-items-per-collection', type=int, default=100)
    parser.add_argument('--rows', type=int, default=100)
    parser.add_argument('--sleep-seconds', type=float, default=0.25)
    parser.add_argument('--output-json', default=DEFAULT_OUTPUT_JSON)
    parser.add_argument('--output-md', default=DEFAULT_OUTPUT_MD)
    parser.add_argument('--cache-dir', default=DEFAULT_CACHE_DIR)
    parser.add_argument('--state-file', default=DEFAULT_STATE_FILE)
    parser.add_argument('--refresh-cache', action='store_true')
    parser.add_argument('--refresh-state', action='store_true')
    parser.add_argument('--no-resume', action='store_true')
    parser.add_argument('--include-private', action='store_true')
    parser.add_argument('--full-item-validation-sample', type=int, default=0)
    parser.add_argument('--collection-query-mode', default='public-top-level', choices=['public-top-level', 'search'])
    parser.add_argument('--collection-pids', default='')
    parser.add_argument('--skip-collections', default='')
    parser.add_argument('--min-consistency-percent', type=float, default=90.0)
    parser.add_argument('--top-architectures', type=int, default=25)
    parser.add_argument('--include-singletons', action='store_true')
    parser.add_argument('--include-mime-types', action='store_true')
    parser.add_argument('--fetch-all-children', action='store_true')
    parser.add_argument('--sample-strategy', default='first', choices=['first', 'evenly-spaced', 'random'])
    parser.add_argument('--random-seed', type=int, default=0)
    parser.add_argument('--min-sample-size', type=int, default=10)
    args = parser.parse_args()
    return args


def main() -> None:
    """
    Runs the architecture sampler CLI.
    Called by: module guard
    """
    args = parse_args()
    result = run_sampler(args)
    write_json(Path(args.output_json), result)
    write_markdown(Path(args.output_md), render_markdown_report(result))
    log.info('Wrote %s and %s', args.output_json, args.output_md)


if __name__ == '__main__':
    main()
