import json

from . import timeseries


def format_star_count(events):
    for d in timeseries.cumulative_star_count(events):
        print(d[0], d[1])

def format_stars_json(events):
    for x in sorted(events, key=lambda x: x["timestamp"]):
        print(json.dumps(x))
