import itertools

class PageFetcher:
    def __init__(self, fetch, parse):
        self.fetch = fetch
        self.parse = parse

    def fetch_all(self):
        for _ in itertools.count(1):
            updates = self.fetch()
            if not updates:
                break

            for update in updates:
                yield self.parse(update)

    def page_cursor(self, page):
        return PageCursor(self, page)


class PageCursor:
    def __init__(self, fetcher, page):
        self.fetcher = fetcher
        self.page = page

    def fetch(self):
        # We probably want to merge these two classes
        return list(map(self.fetcher.parse, self.fetcher.fetch(self.page)))

    def prev(self):
        if self.page <= 1:
            return None
        return PageCursor(self.fetcher, self.page - 1)

    def next(self):
        return PageCursor(self.fetcher, self.page + 1)
