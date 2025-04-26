import json
import subprocess
import time
import logging

def repos(user, page):
    for attempt in range(5):
        command = ["gh",  "api", f'users/{user}/repos?per_page=100&page={page}']
        try:
            raw = subprocess.check_output(command)
        except subprocess.CalledProcessError:
            if attempt == 4:
                raise
            logging.info("Failed to get repos user:%r page:%r. Retrying...", user, page)
            time.sleep(0.5)
            continue

        return json.loads(raw)


def stargazers(repo:str, page:int, page_size:int) -> list:
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

def star_count(repo):
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
