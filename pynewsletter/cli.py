import asyncio
from functools import wraps
import sys

import click


def coroutine(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(f(*args, **kwargs))

    return wrapper


async def browse():
    print("ADS")


class SearchOption:
    BROWSE = "browse"


_AVAILABLE_OPTIONS = {SearchOption.BROWSE: browse}


@click.command()
@click.argument("option")
@coroutine
async def run(option):
    if option not in _AVAILABLE_OPTIONS:
        print(
            f'Invalid option: {option}. Available options: {",".join(_AVAILABLE_OPTIONS)}'
        )
        sys.exit(1)

    await _AVAILABLE_OPTIONS[option]()
