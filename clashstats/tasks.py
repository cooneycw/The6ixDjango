import os
import time
from The6ix.settings import REDIS_LOCK_KEY, REDIS_INSTANCE
from The6ix.celery import app
from .Tasks_Scoring.score import deck_analyzer


@app.task(name='clashstats.tasks.scoring')
def analyze_deck(game_df):
    results = None
    timeout = (60 * 10)
    have_lock = False
    my_lock = REDIS_INSTANCE.lock(REDIS_LOCK_KEY, timeout=timeout)
    while not have_lock:
        have_lock = my_lock.acquire(blocking=False)
        if have_lock:
            print('start deck analysis')
            results = deck_analyzer(game_df)
        else:
            print('waiting for lock to commence...')
            time.sleep(10)
    my_lock.release()
    return results
