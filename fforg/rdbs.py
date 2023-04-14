from .redisdb import *

# Timers
r_timers = TimersDB(settings.REDIS_URL_TIMERS)
