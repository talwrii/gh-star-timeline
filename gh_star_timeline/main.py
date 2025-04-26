import argparse
import datetime
import itertools
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

from . import timeseries

PARSER = argparse.ArgumentParser(description='Maintain a timeline of the number of stars for a repo')
PARSER.add_argument('repo', nargs="?")
PARSER.add_argument('--user', action='store_true', help="Get information about all repos for a user")
PARSER.add_argument('-n', '--no-fetch', action='store_false', help="Get information about all repos for a user", default=True, dest="fetch")
PARSER.add_argument('--path', action='store_true', default=False, help='Print the path the data directory')
PARSER.add_argument('-t', '--timeseries', action='store_true', default=False, help="Output a timeseries")
mx = PARSER.add_mutually_exclusive_group()
mx.add_argument('--debug', action='store_true', default=False)
mx.add_argument('--silent', action='store_true', default=False, help="No debug output")
mx2 = PARSER.add_mutually_exclusive_group()
mx2.add_argument('-T', '--total', action='store_true', default=False, help="Sum number of stars across all repos")
mx2.add_argument('--stars', action='store_true', default=False, help="Output all star events")


args = PARSER.parse_args()

STATS_DIR = Path.home() / ".local" / "state" / "gh-star-timeline"

def main():
    STATS_DIR.mkdir(exist_ok=True)


    if args.debug:
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    elif args.silent:
        pass
    else:
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)


    if args.path:
        if args.repo:
            print(repo_path(args.repo))
        else:
            print(str(STATS_DIR))
        return

    if args.repo is None:
        print("Must provide a repository")

    if args.user:
        user = args.repo
        if args.fetch:
            logging.info("Getting repos for %r...", user)
            repos = list(fetch_user_repos(user))
            write_repos(user, repos)
            logging.info("Got repos.")

        repos = read_repos(user)
    else:
        repos = [args.repo]


    percent = 0
    repo_stars = {}
    all_stars = []
    for i, repo in enumerate(repos):

        old_percent = percent
        percent = 100 * i // len(repos)

        if percent // 10 - old_percent // 10:
            if args.fetch:
                logging.info("%s%% progress", percent)

        if args.fetch:
            logging.debug("Getting stargazers for repo %r", repo)
            fetch(repo)

        stars = list(read_repo(repo))
        all_stars.extend(stars)

        num_stars = sum(event_stars(e) for e in stars)
        if args.fetch:
            star_count = github_star_count(repo)

            if num_stars != star_count:
                # Some stars have been removed refetch
                logging.info('Stargazers counts (%s) and stars (%s) do not match for %r. Finding removed stars...', num_stars, star_count, repo)

                new_gazers = set(s["user"] for s in StarFetcher(repo).fetch())
                current_gazers = set(gazers_from_events(read_repo(repo)))
                for x in current_gazers - new_gazers:
                    logging.info("%r removed star from %r", x, repo)
                    remove_star(x)

                num_stars = sum(event_stars(e) for e in read_repo(repo))


            if num_stars != star_count:
                raise Exception("Stars still do not match after removing stars")

        repo_stars[repo] = num_stars


    if not args.user:
        if args.timeseries:
            for d in timeseries.star_timeseries(all_stars):
                print(d[0], d[1])
        elif args.stars:
            for x in sorted(all_stars, key=lambda x: x["timestamp"]):
                print(json.dumps(x))
        else:
            print(list(repo_stars.values())[0])
    else:
        if args.timeseries:
            start = ts_date(min(s["timestamp"] for s in all_stars))
            end = ts_date(max(s["timestamp"] for s in all_stars))


            if args.total:
                for d, t in timeseries.star_timeseries(all_stars):
                    print(d, t)
            else:
                series = [list(timeseries.star_timeseries([x for x in all_stars if x["repo"] == r], start, end)) for r in repos]
                print(" ".join(["date"] + repos))
                for date, *values in zip_timeseries(series):
                    print(date, " ".join(map(str, values)))
                return
        elif args.total:
            print(sum(repo_stars.values()))
        elif args.stars:
            for x in sorted(all_stars, key=lambda x: x["timestamp"]):
                print(json.dumps(x))
        else:
            for k, v in repo_stars.items():
                print(k, v)

def repo_path(repo):
    return STATS_DIR / (repo.replace("/", "--") + ".json")

def read_repo(repo):
    path = repo_path(repo)
    if not path.exists():
        return []
    with path.open() as stream:
        for line in stream:
            yield dict(repo=repo, **json.loads(line))

def add_star(repo, star):
    with repo_path(repo).open("a") as stream:
        stream.write(json.dumps(star) + "\n")

def remove_star(user):
    path = STATS_DIR / (repo.replace("/", "--") + ".json")
    timestamp = datetime.datetime.now(datetime.UTC).replace(tz_info=None).isoformat() + "Z"
    with path.open("a") as stream:
        stream.write(json.dumps({"user": user, "timestamp": timestamp, "event": "removed" }))

def key(d):
    return (d["timestamp"], d["user"])


def event_stars(e):
    if e["event"] == "added":
        return 1
    elif e["event"] == "removed":
        return -1
    else:
        raise Exception(e["type"])

def github_star_count(repo):
    for attempt in range(5):
        user, repo_name = repo.split("/")
        command = ["gh",  "api", f'repos/{user}/{repo_name}']
        try:
            data = json.loads(subprocess.check_output(command))
        except subprocess.CalledProcessError:
            if attempt == 4:
                raise
            else:
                logging.info('Getting stars for %r failed. Retrying', repo)
                time.sleep(0.5)
                continue

        return data["stargazers_count"]

def fetch_stargazers_page(repo:str, page:int, page_size:int) -> list:
    if page < 1:
        raise Exception('Pages must be 1 or larger (indexing starts at 1)')
    for i in range(5):
        user, repo_name = repo.split("/")
        command = ["gh",  "api", f'repos/{user}/{repo_name}/stargazers?per_page={page_size}&page={page}', "-H", 'Accept: application/vnd.github.v3.star+json']

        try:
            raw = subprocess.check_output(command)
        except subprocess.CalledProcessError:
            if i == 4:
                raise
            time.sleep(1)
            continue

        result = json.loads(raw)
        logging.debug('Fetched page: %r, size: %r, stars:%s', page, page_size, len(result))
        return result


def fetch_user_repos_page(user, i):
    for attempt in range(5):
        command = ["gh",  "api", f'users/{user}/repos?per_page=100&page={i}']
        try:
            raw = subprocess.check_output(command)
        except subprocess.CalledProcessError:
            if attempt == 4:
                raise
            logging.info("Failed to get repos user:%r page:%r. Retrying...", user, i)
            time.sleep(0.5)
            continue

        return json.loads(raw)

class StarFetcher:
    def __init__(self, repo):
        self.num_pages = 0
        self.repo = repo
        self.page_size = 10

    def fetch(self):
        for i in itertools.count(1):
            updates = fetch_stargazers_page(self.repo, i, page_size=self.page_size)
            self.num_pages = i
            if not updates:
                break

            for update in updates:
                star = parse_star(update)

                yield star

    def fetch_page(self, page):
        updates = fetch_stargazers_page(self.repo, page, self.page_size)
        return list(map(parse_star, updates))

    def cursor(self, page=None, index=None):
        if page is None:
            page = index // self.page_size + 1
        else:
            assert index is None

        return Cursor(self, page)

class Cursor:
    def __init__(self, fetcher, page):
        self.fetcher = fetcher
        self.page = page

    def fetch(self):
        return self.fetcher.fetch_page(page=self.page)

    def prev(self):
        if self.page <= 1:
            return None
        return Cursor(self.fetcher, self.page - 1)

    def next(self):
        return Cursor(self.fetcher, self.page + 1)


def fetch_user_repos(user):
    for i in itertools.count(1):
        updates = fetch_user_repos_page(user, i)
        if not updates:
            break

        for x in updates:
            yield x["full_name"]

def fetch(repo):
    star_count = 0
    existing_keys = set()
    timestamp = None
    for d in read_repo(repo):
        star_count += 1
        existing_keys.add(key(d))
        timestamp = d["timestamp"]

    stars_to_add = []

    # guess at page with current stars
    #  search up and down until existing match

    fetcher = StarFetcher(repo)

    guess_cursor = fetcher.cursor(index=star_count)

    pages_fetched = 0

    cursor = guess_cursor
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

    cursor = guess_cursor.next()
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

    print(len(stars_to_add))

    for star in reversed(stars_to_add):
        add_star(repo, star)


def write_repos(user, repos):
    path = repos_path(user)
    with open(path, 'w') as stream:
        stream.write(json.dumps(repos))

def read_repos(user):
    path = repos_path(user)
    with open(path) as stream:
        return json.loads(stream.read())

def repos_path(user):
    return STATS_DIR / ("repos-" + user + ".json")

def ts_date(s):
    return datetime.date.fromisoformat(s.split("T")[0])

def zip_timeseries(series):
    for xs in zip(*series):
        if len(set([t for (t, _) in xs])) != 1:
            raise Exception(f'Timestamps do not match in {xs}')
        yield (xs[0][0],) + tuple(x[1] for x in xs)


def gazers_from_events(events):
    user_stars = {}
    for x in events:
        user_stars.setdefault(x["user"], 0)
        match x["event"]:
            case "added":
                user_stars[x["user"]] += 1
            case "removed":
                user_stars[x["user"]] -= 1

    for k, count in user_stars.items():
        if count not in (0, 1):
            raise Exception(f"{k} has a strange number of stars {count}")

    return [x for x, count in user_stars.items() if count == 1]


def parse_star(update):
    return {"timestamp": update["starred_at"], "user": update["user"]["login"], "event": "added"}
