import datetime

from gh_star_timeline import timeseries


def test_make_timeseries():
    repo_events = [
        {"repo": "talwrii/ffmpeg-cookbook", "timestamp": "2025-04-02T20:55:07Z", "user": "luciusmagn", "event": "added"},
        {"repo": "talwrii/ffmpeg-cookbook", "timestamp": "2025-04-06T18:36:29Z", "user": "nebunebu", "event": "added"},
        {"repo": "talwrii/ffmpeg-cookbook", "timestamp": "2025-04-12T07:15:59Z", "user": "entailz", "event": "added"},
        {"repo": "talwrii/ffmpeg-cookbook", "timestamp": "2025-04-12T15:48:40Z", "user": "Matt-Deacalion", "event": "added"},
        {"repo": "talwrii/ffmpeg-cookbook", "timestamp": "2025-04-13T20:24:20Z", "user": "surskitt", "event": "added"},
        {"repo": "talwrii/ffmpeg-cookbook", "timestamp": "2025-04-14T07:10:26Z", "user": "prismflasher", "event": "added"},
        ]


    # Normal
    series = list(timeseries.cumulative_star_count(repo_events))
    assert list(series) == [('2025-04-02', 1), ('2025-04-03', 1), ('2025-04-04', 1), ('2025-04-05', 1), ('2025-04-06', 2), ('2025-04-07', 2), ('2025-04-08', 2), ('2025-04-09', 2), ('2025-04-10', 2), ('2025-04-11', 2), ('2025-04-12', 4), ('2025-04-13', 5), ('2025-04-14', 6)]

    # Empty
    series = list(timeseries.cumulative_star_count(
        [],
        start=datetime.date(2025, 4, 1),
        end=datetime.date(2025, 4, 3),
    ))
    assert list(series) == [('2025-04-01', 0), ('2025-04-02', 0), ('2025-04-03', 0)]


    # start
    series = list(timeseries.cumulative_star_count(repo_events, start=datetime.date(2025, 4, 1)))
    assert list(series) == [('2025-04-01', 0), ('2025-04-02', 1), ('2025-04-03', 1), ('2025-04-04', 1), ('2025-04-05', 1), ('2025-04-06', 2), ('2025-04-07', 2), ('2025-04-08', 2), ('2025-04-09', 2), ('2025-04-10', 2), ('2025-04-11', 2), ('2025-04-12', 4), ('2025-04-13', 5), ('2025-04-14', 6)]

    # end date
    series = list(timeseries.cumulative_star_count(
        repo_events,
        start=datetime.date(2025, 4, 1),
        end=datetime.date(2025, 4, 15)))

    assert list(series) == [('2025-04-01', 0), ('2025-04-02', 1), ('2025-04-03', 1), ('2025-04-04', 1), ('2025-04-05', 1), ('2025-04-06', 2), ('2025-04-07', 2), ('2025-04-08', 2), ('2025-04-09', 2), ('2025-04-10', 2), ('2025-04-11', 2), ('2025-04-12', 4), ('2025-04-13', 5), ('2025-04-14', 6), ('2025-04-15', 6)]
