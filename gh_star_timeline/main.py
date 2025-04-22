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
PARSER.add_argument('repo')
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
        print(str(STATS_DIR))
        return

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

    if args.fetch:
        logging.info("Getting stars for repo...")
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
            stars_for_repo = fetch_repo_stars(repo)

            if num_stars != stars_for_repo:
                # Some stars have been removed refetch
                logging.info('Stargazers and stars do not match for %r. Finding removed stars...')

                gazers = set(s["user"] for s in StarFetcher(repo).fetch())
                fetched_gazers = set(s["user"] for s in fetch_repo_stars(repo))
                for x in fetched_gazers - gazers:
                    remove_star(x)

                num_stars = sum(event_stars(e) for e in read_repo(repo))

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


def read_repo(repo):
    path = STATS_DIR / (repo.replace("/", "--") + ".json")
    if not path.exists():
        return []
    with path.open() as stream:
        for line in stream:
            yield dict(repo=repo, **json.loads(line))

def add_star(repo, star):
    path = STATS_DIR / (repo.replace("/", "--") + ".json")
    with path.open("a") as stream:
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

def fetch_repo_stars(repo):
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

def fetch_stargazers_page(repo, page):
    for i in range(5):
        user, repo_name = repo.split("/")
        command = ["gh",  "api", f'repos/{user}/{repo_name}/stargazers?per_page=10&direction=desc&page={page}', "-H", 'Accept: application/vnd.github.v3.star+json']
        try:
            raw = subprocess.check_output(command)
        except subprocess.CalledProcessError:
            if i == 4:
                raise
            time.sleep(1)
            continue
        return json.loads(raw)


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

    def fetch(self):
        for i in itertools.count(1):
            updates = fetch_stargazers_page(self.repo, i)
            self.num_pages = i
            if not updates:
                break

            for update in updates:
                star = {"timestamp": update["starred_at"], "user": update["user"]["login"], "event": "added"}
                yield star



def fetch_user_repos(user):
    for i in itertools.count(1):
        updates = fetch_user_repos_page(user, i)
        if not updates:
            break

        for x in updates:
            yield x["full_name"]


def fetch(repo):
    existing_keys = set(key(d) for d in read_repo(repo))
    stars_to_add = []

    fetcher = StarFetcher(repo)
    for star in fetcher.fetch():
        if key(star) in existing_keys:
            break

        stars_to_add.append(star)

    logging.debug('Got %r pages while fetching starts for %r', fetcher.num_pages, repo)

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
