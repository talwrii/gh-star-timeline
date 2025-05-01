import argparse
import datetime
import itertools
import json
import logging
import sys
from pathlib import Path

from . import timeseries, api, parse_api, timestamps, events, display, log_tqdm, page_fetcher

STATS_DIR = Path.home() / ".local" / "state" / "gh-star-timeline"


PARSER = argparse.ArgumentParser(description='Maintain a timeline of the number of stars for a Gitbub repo or all repos for a user', epilog="BY @READWITHAI 📖 https://readwithai.substack.com/ ⚡️ MACHINE-AIDED READING 🖋️")
PARSER.add_argument('repo', nargs="?")
PARSER.add_argument('--user', action='store_true', help="Get information about all repos for a user")
PARSER.add_argument(
    '-n', '--no-fetch', action='store_false',
    help="Get information about all repos for a user", default=True, dest="fetch")
PARSER.add_argument('--path', action='store_true', default=False, help='Print the path the data directory')
PARSER.add_argument('-t', '--timeseries', action='store_true', default=False, help="Output a timeseries")
mx = PARSER.add_mutually_exclusive_group()
mx.add_argument('--debug', action='store_true', default=False)
mx.add_argument('--silent', action='store_true', default=False, help="No debug output")
mx2 = PARSER.add_mutually_exclusive_group()
mx2.add_argument('-T', '--total', action='store_true', default=False, help="Sum number of stars across all repos")
mx2.add_argument('--stars', action='store_true', default=False, help="Output all star events")



def init_debug(args):
    if args.debug:
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    elif args.silent:
        pass
    else:
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)


def handle_path(args):
    if args.path:
        if args.repo:
            print(Db.repo_path(args.repo))
        else:
            print(str(STATS_DIR))
        return True

    if args.repo is None:
        print("Must provide a repository")


def init_repos(args):
    if args.user:
        user = args.repo
        if args.fetch:
            logging.info("Getting list of repos for %r...", user)
            repos = list(fetch_user_repos(user))
            Db.write_repos(user, repos)
            logging.info("Got repos.")

        return Db.read_repos(user)
    else:
        return [args.repo]

def main():
    args = PARSER.parse_args()
    STATS_DIR.mkdir(exist_ok=True)

    init_debug(args)
    if handle_path(args):
        return
    repos = init_repos(args)

    repo_star_count = {}
    combined_events = []

    if args.fetch:
        logging.info("Fetching stars gazers...")
    for repo in (log_tqdm.log_tqdm if args.fetch else lambda x:x)(repos):

        if args.fetch:
            logging.debug("Getting stargazers for repo %r", repo)
            fetch(repo)

        repo_events = list(Db.events(repo))
        combined_events.extend(repo_events)
        num_stars = events.star_count(repo_events)

        if args.fetch:
            api_star_count = api.star_count(repo)
            if num_stars != api_star_count:
                # Some stars have been removed.
                # Fetch everything and work out what has been deleted
                logging.info('Stargazers counts (%s) and stars (%s) do not match for %r. Finding removed stars...', num_stars, api_star_count, repo)
                process_removed_stars(repo)
                num_stars = events.star_count(Db.events(repo))

                if num_stars != api_star_count:
                    raise Exception("Stars still do not match after removing stars")

        repo_star_count[repo] = num_stars

    display_data(args, repos, repo_star_count, combined_events)

def fetch_user_repos(user):
    for i in itertools.count(1):
        updates = api.repos(user, i)
        if not updates:
            break

        for x in updates:
            yield x["full_name"]

PAGE_SIZE = 10

def gazers_fetcher(repo):
    return page_fetcher.PageFetcher(
        lambda page: api.stargazers(repo, page, page_size=PAGE_SIZE),
        parse_api.parse_event
    )

def fetch(repo):
    existing_keys = set()
    timestamp = None

    star_count = 0

    def key(d):
        return (d["timestamp"], d["user"])

    for star_count, d in enumerate(Db.events(repo)):
        existing_keys.add(key(d))
        timestamp = d["timestamp"]

    stars_to_add = []

    # guess at page with current stars
    #  search up and down until existing match
    fetcher = gazers_fetcher(repo)

    pages_fetched = 0
    guessed_cursor = cursor = fetcher.page_cursor(page=star_count // PAGE_SIZE  + 1)
    while cursor:
        updates = cursor.fetch()
        pages_fetched += 1
        cursor =  cursor.prev()

        if not updates:
            break

        for x in reversed(updates):
            if timestamp and x["timestamp"] < timestamp:
                break

            if key(x) in existing_keys:
                break

            stars_to_add.append(x)
        else:
            continue
        break

    cursor = guessed_cursor.next()
    while cursor:
        updates = cursor.fetch()
        pages_fetched += 1
        cursor = cursor.next()
        if not updates:
            break

        for x in updates:
            if timestamp and x["timestamp"] < timestamp:
                continue
            stars_to_add.append(x)

    logging.debug('Got %r pages while fetching starts for %r', pages_fetched, repo)

    stars_to_add = sorted(stars_to_add, key=lambda x: x["timestamp"])

    for star in stars_to_add:
        Db.add_event(repo, star)

def process_removed_stars(repo):
    new_gazers = set(s["user"] for s in gazers_fetcher(repo).fetch_all())
    current_gazers = set(events.gazers(Db.events(repo)))
    for x in current_gazers - new_gazers:
        logging.info("%r removed star from %r", x, repo)
        Db.remove_gazer(repo, x)

class Db:
    @classmethod
    def write_repos(cls, user, repos):
        path = cls.repos_path(user)
        with open(path, 'w') as stream:
            stream.write(json.dumps(repos))

    @classmethod
    def read_repos(cls, user):
        path = cls.repos_path(user)
        with open(path) as stream:
            return json.loads(stream.read())

    @classmethod
    def repos_path(cls, user):
        return STATS_DIR / ("repos-" + user + ".json")


    @classmethod
    def add_event(cls, repo, event):
        with cls.repo_path(repo).open("a") as stream:
            stream.write(json.dumps(event) + "\n")

    @classmethod
    def remove_gazer(cls, repo, user):
        path = STATS_DIR / (repo.replace("/", "--") + ".json")
        timestamp = datetime.datetime.now(datetime.UTC).replace(tz_info=None).isoformat() + "Z"
        with path.open("a") as stream:
            stream.write(json.dumps({"user": user, "timestamp": timestamp, "event": "removed" }))

    @classmethod
    def repo_path(cls, repo):
        return STATS_DIR / (repo.replace("/", "--") + ".json")

    @classmethod
    def events(cls, repo):
        path = cls.repo_path(repo)
        if not path.exists():
            return
        with path.open() as stream:
            for line in stream:
                yield dict(repo=repo, **json.loads(line))


def display_data(args, repos, repo_star_count, combined_events):
    if not args.user:
        if args.timeseries:
            display.format_star_count(combined_events)
        elif args.stars:
            display.format_stars_json(combined_events)
        else:
            print(list(repo_star_count.values())[0])
    else:
        if args.timeseries:
            start = timestamps.date_string(min(s["timestamp"] for s in combined_events))
            end = timestamps.date_string(max(s["timestamp"] for s in combined_events))

            if args.total:
                display.format_star_count(combined_events)
            else:
                series = [list(timeseries.cumulative_star_count([x for x in combined_events if x["repo"] == r], start, end)) for r in repos]
                print(" ".join(["date"] + repos))
                for date, *values in timeseries.zip_timeseries(series):
                    print(date, " ".join(map(str, values)))
                return
        elif args.total:
            print(sum(repo_star_count.values()))
        elif args.stars:
            display.format_stars_json(combined_events)
        else:
            for k, v in repo_star_count.items():
                print(k, v)
