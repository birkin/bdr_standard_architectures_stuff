import argparse
import logging
from pathlib import Path

from lib.config import (
    DEFAULT_API_ROOT,
    DEFAULT_CACHE_DIR,
    DEFAULT_MAX_CHILDREN_PER_PARENT,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_MD,
    DEFAULT_SLEEP_SECONDS,
    DEFAULT_SPECIFICATIONS_DIR,
    DEFAULT_STATE_FILE,
    LOG_LEVEL,
    MAX_CHILDREN_PER_PARENT_CAP,
)
from lib.report import render_markdown_report
from lib.sampler import run_sampler
from lib.specifications import write_specification_files
from lib.utils import write_json, write_markdown


logging.basicConfig(
    level=LOG_LEVEL,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S',
)
log = logging.getLogger(__name__)


def positive_int(value: str) -> int:
    """
    Parses a positive integer argument.
    Called by: parse_args()
    """
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError('value must be an integer') from error
    if parsed_value < 1:
        raise argparse.ArgumentTypeError('value must be a positive integer')
    return parsed_value


def max_children_per_parent(value: str) -> int:
    """
    Parses the child sample limit argument.
    Called by: parse_args()
    """
    parsed_value = positive_int(value)
    if parsed_value > MAX_CHILDREN_PER_PARENT_CAP:
        raise argparse.ArgumentTypeError(f'value must be <= {MAX_CHILDREN_PER_PARENT_CAP}')
    return parsed_value


def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments.
    Called by: main()
    """
    parser = argparse.ArgumentParser(description='Determine common BDR object architectures.')
    parser.add_argument('--api-root', default=DEFAULT_API_ROOT)
    parser.add_argument('--max-collections', type=int, default=20)
    parser.add_argument('--max-items-per-collection', type=int, default=100)
    parser.add_argument('--max-children-per-parent', type=max_children_per_parent, default=DEFAULT_MAX_CHILDREN_PER_PARENT)
    parser.add_argument('--rows', type=int, default=100)
    parser.add_argument('--sleep-seconds', type=float, default=DEFAULT_SLEEP_SECONDS)
    parser.add_argument('--output-json', default=DEFAULT_OUTPUT_JSON)
    parser.add_argument('--output-md', default=DEFAULT_OUTPUT_MD)
    parser.add_argument('--output-specifications-dir', default=DEFAULT_SPECIFICATIONS_DIR)
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
    parser.add_argument(
        '--fetch-all-children-max-1000',
        action='store_true',
        help='Fetch direct children up to the 1,000-child safety cap instead of the normal child sample limit.',
    )
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
    write_specification_files(Path(args.output_specifications_dir), result)
    log.info('Wrote %s, %s, and specifications in %s', args.output_json, args.output_md, args.output_specifications_dir)


if __name__ == '__main__':
    main()
