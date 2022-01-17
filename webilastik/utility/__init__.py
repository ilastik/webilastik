# pyright: reportUnusedImport=false
from .flatten import flatten, unflatten, listify
import datetime

def get_now_string() -> str:
    now = datetime.datetime.now()
    return f"{now.year:02}y{now.month:02}m{now.day:02}d__{now.hour:02}h{now.minute:02}m{now.second:02}s"
