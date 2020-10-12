import asyncio
from functools import wraps
import re
import sys

import aiohttp
from bs4 import BeautifulSoup
import click
from colorama import init, Fore


init(autoreset=True)
BASE_URL = "https://pycoders.com/"


def coroutine(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(f(*args, **kwargs))

    return wrapper


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


async def get_issue(session, issue, args):
    print(Fore.YELLOW + f"Fetching issue: #{issue}")
    html = await fetch(session, f"{BASE_URL}issues/{issue}")
    soup = BeautifulSoup(html, "html.parser")
    projects = soup.find("h2", string=re.compile(".*[pP]roject.*"))
    links = [
        dict(title=link.text, url=link.attrs.get("href"))
        for link in projects.find_all_next("a", href=re.compile(".*link.*"))
    ]
    for link in links:
        print(Fore.BLUE + f'{link["title"]}' + "  " + Fore.GREEN + f'{link["url"]}')


async def get_latest_issue_number(session):
    html = await fetch(session, BASE_URL)
    soup = BeautifulSoup(html, "html.parser")
    anchor = soup.find("a", string=re.compile(r".*latest.*"))
    href = anchor.attrs.get("href")
    return int(href.split("/")[-1])


async def browse(args):
    async with aiohttp.ClientSession() as session:
        latest_issue_number = await get_latest_issue_number(session)
        print(Fore.YELLOW + f"Found latest issue: {latest_issue_number}")

        while True:
            await get_issue(session=session, issue=latest_issue_number, args=args)
            await asyncio.sleep(5)
            latest_issue_number -= 1


class SearchOption:
    BROWSE = "browse"


_AVAILABLE_OPTIONS = {SearchOption.BROWSE: browse}


@click.command()
@click.argument("option", nargs=1)
@click.argument("args", nargs=-1)
@coroutine
async def run(option, args):
    if option not in _AVAILABLE_OPTIONS:
        print(
            f'Invalid option: {option}. Available options: {",".join(_AVAILABLE_OPTIONS)}'
        )
        sys.exit(1)

    await _AVAILABLE_OPTIONS[option](args)
