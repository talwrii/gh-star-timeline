import datetime

def date_string(s):
    return datetime.date.fromisoformat(s.split("T")[0])
