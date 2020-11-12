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
OLDEST_ISSUE = 339
LINK_COLOR = "3399CC"
STATUS_SUCCESS = 200
SLEEP_TIME = 3
CHUNK_SIZE = 10

SECTION_MAP = {
    "projects": re.compile(".*project.*", re.IGNORECASE),
    "articles": re.compile(".*article.*", re.IGNORECASE),
    "discussions": re.compile(".*discussion.*", re.IGNORECASE),
    "jobs": re.compile(".*job.*", re.IGNORECASE),
}


def chunks(source, n):
    for i in range(0, len(source), n):
        yield source[i : i + n]


def coroutine(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(f(*args, **kwargs))

    return wrapper


def display_link(link):
    title = link.text
    url = link.attrs.get("href")
    if title.startswith("⋅"):
        title = title.replace("⋅", "").strip()
        print(Fore.RED + "[EVENT]" + Fore.BLUE + f" {title} " + Fore.GREEN + f"{url}")
    else:
        print(Fore.BLUE + f"{title} " + Fore.GREEN + f"{url}")


async def fetch(session, url):
    async with session.get(url) as response:
        html = await response.text()
        return html, response.status


async def fetch_issue(session, issue):
    # print(Fore.YELLOW + f"Fetching issue: #{issue}")
    html, status_code = await fetch(session, f"{BASE_URL}issues/{issue}")
    return BeautifulSoup(html, "html.parser"), status_code


async def parse_issue(soup, args):
    kind = args[0] if args else "preview"
    section_regexp = SECTION_MAP.get(kind, None)
    section_name = kind.capitalize() if kind in SECTION_MAP else "Preview"

    if section_regexp is not None:
        section = soup.find("h2", string=section_regexp)
        links = (
            []
            if section is None
            else section.find_all_next("a", href=re.compile(".*link.*"))
        )
    else:
        section = soup.find(id="templateBody").find_all("h2")[0]
        links = (
            []
            if section is None
            else section.find_all_previous("a", href=re.compile(".*link.*"))
        )

    print(Fore.CYAN + f"[{section_name}]")
    results = []
    for link in links:
        next_section = link.find_previous("h2")

        if (
            section_regexp
            and next_section is not None
            and next_section.text != section.text
        ):
            break

        styles = link.attrs.get("style", "")
        if LINK_COLOR.lower() not in styles.lower():
            continue

        results.append(link)

    for link in results:
        display_link(link)


async def get_latest_issue_number(session):
    html, _ = await fetch(session, BASE_URL)
    soup = BeautifulSoup(html, "html.parser")
    anchor = soup.find("a", string=re.compile(r".*latest.*"))
    href = anchor.attrs.get("href")
    issue_number = int(href.split("/")[-1])
    print(Fore.YELLOW + f"Found latest issue: {issue_number}")
    return issue_number


async def browse(args):
    async with aiohttp.ClientSession() as session:
        issue_number = await get_latest_issue_number(session)

        while True:
            soup, status_code = await fetch_issue(session=session, issue=issue_number)
            if status_code == STATUS_SUCCESS:
                await parse_issue(soup=soup, args=args)
                await asyncio.sleep(SLEEP_TIME)

            issue_number -= 1


async def download_issue(args):
    if len(args) == 0:
        print(Fore.RED + "Please provide issue number")
        sys.exit(1)

    issue_number = args[0]
    if int(issue_number) < OLDEST_ISSUE:
        print(Fore.RED + f"Issue number starts at {OLDEST_ISSUE}.")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        soup, status_code = await fetch_issue(session=session, issue=issue_number)
        if status_code != STATUS_SUCCESS:
            print(Fore.RED + f"Could not download issue: {issue_number}")
            return

        await parse_issue(soup=soup, args=("preview",))
        await parse_issue(soup=soup, args=("projects",))
        await parse_issue(soup=soup, args=("articles",))
        await parse_issue(soup=soup, args=("jobs",))
        await parse_issue(soup=soup, args=("discussions",))


async def search_issue(session, issue_number, phrase):
    soup, status_code = await fetch_issue(session=session, issue=issue_number)
    if status_code != STATUS_SUCCESS:
        return
    links = soup.find_all(
        "a",
        href=re.compile(".*link.*"),
        text=re.compile(f".*{phrase}.*", re.IGNORECASE),
    )
    for link in links:
        display_link(link)


async def search(args):
    if len(args) == 0:
        print(Fore.RED + "Please provide phrase to search")
        sys.exit(1)

    phrase = args[0]

    async with aiohttp.ClientSession() as session:
        issue_number = await get_latest_issue_number(session)
        latest_issues = list(reversed(range(OLDEST_ISSUE, issue_number + 1)))
        for batch in chunks(latest_issues, CHUNK_SIZE):
            tasks = [
                search_issue(session=session, issue_number=i, phrase=phrase)
                for i in batch
            ]
            for f in asyncio.as_completed(tasks):
                await f


class SearchOption:
    BROWSE = "browse"
    ISSUE = "issue"
    SEARCH = "search"


_AVAILABLE_OPTIONS = {
    SearchOption.BROWSE: browse,
    SearchOption.ISSUE: download_issue,
    SearchOption.SEARCH: search,
}


@click.command()
@click.argument("option", nargs=1)
@click.argument("args", nargs=-1)
@coroutine
async def run(option, args):
    if option not in _AVAILABLE_OPTIONS:
        print(
            Fore.RED
            + f'Invalid option: {option}. Available options: {",".join(_AVAILABLE_OPTIONS)}'
        )
        sys.exit(1)

    if len(args) > 1:
        print(Fore.RED + "Invalid number of arguments")
        sys.exit(1)

    await _AVAILABLE_OPTIONS[option](args)
