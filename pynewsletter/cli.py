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


def display_link(link):
    if link["title"].startswith("⋅"):
        title = link["title"].replace("⋅", "").strip()
        print(
            Fore.RED
            + "[EVENT]"
            + Fore.BLUE
            + f" {title} "
            + Fore.GREEN
            + f'{link["url"]}'
        )
    else:
        print(Fore.BLUE + f'{link["title"]} ' + Fore.GREEN + f'{link["url"]}')


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


async def get_issue(session, issue, args):
    kind = args[0] if args else None
    section_map = {
        "projects": re.compile(".*[pP]roject.*"),
        "articles": re.compile(".*[aA]rticle.*"),
        "discussions": re.compile(".*[dD]iscussion.*"),
        "jobs": re.compile(".*[jJ]ob.*"),
    }
    print(Fore.YELLOW + f"Fetching issue: #{issue}")
    html = await fetch(session, f"{BASE_URL}issues/{issue}")
    soup = BeautifulSoup(html, "html.parser")

    if not kind:
        section = soup.find(id="templateBody").find_all("h2")[0]
        links_iter = section.find_all_previous("a", href=re.compile(".*link.*"))
    else:
        section = soup.find("h2", string=section_map[kind])
        links_iter = section.find_all_next("a", href=re.compile(".*link.*"))

    links = []
    for link in links_iter:
        next_section = link.find_previous("h2")

        if kind and next_section is not None and next_section.text != section.text:
            break

        if "3399CC" not in link.attrs.get("style", ""):
            continue

        links.append({"title": link.text, "url": link.attrs.get("href")})

    for link in links:
        display_link(link)


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
            await asyncio.sleep(3)
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

    if len(args) > 1:
        print("Invalid number of arguments")
        sys.exit(1)

    await _AVAILABLE_OPTIONS[option](args)
