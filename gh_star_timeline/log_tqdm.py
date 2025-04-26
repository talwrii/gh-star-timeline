import logging

def log_tqdm(xs):
    percent = 0

    for i, x in enumerate(xs):
        old_percent = percent
        percent = 100 * i // len(xs)

        if percent // 10 - old_percent // 10:
            logging.info("%s%% progress", percent)

        yield x
