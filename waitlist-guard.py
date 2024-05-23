from argparse import ArgumentParser
from spond import spond
import asyncio
import signal
from events import swim_trainings
from functools import reduce
import datetime
import logging
import sys
logger = logging.getLogger(__name__)

WAITLIST_CUT_OFF = datetime.timedelta(hours=1)

LOG_LEVELS = {
  'DEBUG': logging.DEBUG,
  'INFO': logging.INFO,
  'WARNING': logging.WARNING,
  'ERROR': logging.ERROR,
  'CRITICAL': logging.CRITICAL,
}

parser = ArgumentParser()
parser.add_argument('-i', '--interval', default=300, type=int)
parser.add_argument('-p', '--password')
parser.add_argument('-u', '--user')
parser.add_argument('-l', '--log-level', default='INFO', choices=LOG_LEVELS.keys())

args = parser.parse_args()
logging.basicConfig(
  filename=f'waitlist-{datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S')}.log',
  level=LOG_LEVELS[args.log_level],
)

if args.user is None or args.password is None:
  logger.critical('Please provide username and password')
  sys.exit(1)

async def main():
  client = spond.Spond(username=args.user, password=args.password)
  try:
    task = asyncio.create_task(waitlist_guard(client))
    signal.signal(signal.SIGINT, lambda s, f: task.cancel())
    print('Press Ctrl+C to exit')
    await task
  finally:
    await client.clientsession.close()

async def waitlist_guard(client):
  try:
    trainings = await swim_trainings(client)
    if len(trainings) == 0:
      raise Exception('No swim trainings found')

    logger.debug(f'Found {len(trainings)} trainings at {', '.join(map(lambda t: str(t.starts_at), trainings))}')
    while True:
      # Deregister people who go to all swim trainings from one training that
      # hasn't started and is full if some training that hasn't started yet is
      # full
      any_full = reduce(lambda s, t: s or (not t.has_started() and t.is_overbooked()), trainings)
      if any_full:
        registered = map(lambda tr: tr.get_registered(), trainings)
        go_to_all = reduce(lambda s, a: s.intersection(a), registered)
        for attendant in go_to_all:
          havent_started = filter(lambda tr: not tr.has_started(), trainings)
          are_full = filter(lambda tr: tr.is_overbooked(), havent_started)
          # Deregister participant from the event they signed up first, i.e.,
          # don't delete the newer sign-up.
          to_delete_from = min(are_full, key=lambda tr: tr.signed_up_at(attendant))
          logger.info(f'Deregistering {to_delete_from.get_participant_name(attendant)} (ID: {attendant}) at {to_delete_from} (max sign-ups)')
          await to_delete_from.deregister(attendant)

      # Deregister people who have been on the waitlist for too long
      for training in trainings:
        for (attendant, on_waitlist_since) in training.on_waitlist_since():
          if on_waitlist_since >= WAITLIST_CUT_OFF:
            logger.info(f'Deregistering {training.get_participant_name(attendant)} (ID: {attendant}) at {training} (waitlist cut off)')
            await training.deregister(attendant)

      await asyncio.sleep(args.interval)
      logger.debug('Refreshing')
      await swim_trainings(client, parse=False)  # API query to refresh events
      for training in trainings:
        await training.refresh()
  except asyncio.CancelledError:
    pass

asyncio.run(main())
