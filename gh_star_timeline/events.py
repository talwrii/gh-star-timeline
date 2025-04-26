
def gazers(events):
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

def star_count(events):
    return sum(event_star_incr(e) for e in events)

def event_star_incr(e):
    if e["event"] == "added":
        return 1
    elif e["event"] == "removed":
        return -1
    else:
        raise Exception(e["type"])
