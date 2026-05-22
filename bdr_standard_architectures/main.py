import logging
import os


logging.basicConfig(
    level=logging.DEBUG if os.getenv('LOG_LEVEL') == 'DEBUG' else logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S',
)
log = logging.getLogger(__name__)


def sum_two_numbers(first_number: int, second_number: int) -> int:
    """
    Sums two numbers.
    Called by: main()
    """
    total = first_number + second_number
    return total


def main() -> None:
    """
    Runs a tiny summing example.
    Called by: module guard
    """
    total = sum_two_numbers(1, 2)
    log.info('sum: %s', total)
    print(total)


if __name__ == '__main__':
    main()
