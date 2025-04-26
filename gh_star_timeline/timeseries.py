from typing import Iterator, Tuple
import datetime
import itertools

def cumulative_star_count(events, start:datetime.date=None, end:datetime.date=None) -> Iterator[tuple[str, float]]:
    def series():
        total = 0
        date = start or None

        for star in sorted(events, key=lambda x: x["timestamp"]):
            if date:
                while date < star_date(star):
                    yield date.isoformat(), total
                    date += datetime.timedelta(days=1)
            else:
                date = star_date(star)

            match star["event"]:
                case "added":
                    total += 1
                case "removed":
                    total -= 1

            yield date.isoformat(), total


        if date and end:
            while date <= end:
                yield date.isoformat(), total
                date += datetime.timedelta(days=1)

    for d, points in itertools.groupby(series(), key=lambda x: x[0]):
        point = None
        for point in points:
            pass

        assert point is not None
        yield point


def star_date(star):
    return datetime.datetime.fromisoformat(star["timestamp"]).date()


def zip_timeseries(series):
    for xs in zip(*series):
        if len(set([t for (t, _) in xs])) != 1:
            raise Exception(f'Timestamps do not match in {xs}')
        yield (xs[0][0],) + tuple(x[1] for x in xs)
