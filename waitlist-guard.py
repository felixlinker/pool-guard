from argparse import ArgumentParser
from spond import spond
import asyncio
import signal
from events import swim_trainings
from functools import reduce
import datetime

WAITLIST_CUT_OFF = datetime.timedelta(hours=1)

parser = ArgumentParser()
parser.add_argument('-i', '--interval', default=300)
parser.add_argument('-p', '--password')
parser.add_argument('-u', '--user')

args = parser.parse_args()

async def main():
  client = spond.Spond(username=args.user, password=args.password)
  try:
    t1 = asyncio.create_task(capture_sigint())
    t2 = asyncio.create_task(waitlist_guard(client))
    await asyncio.gather(t1, t2)
  except Terminate:
    print('\nShutting down...')
    t1.cancel()
    t2.cancel()
  finally:
    client.clientsession.close()

class Terminate(Exception):
  pass

async def capture_sigint():
  '''
  This function blocks until Ctrl+C is pressed, then raises the Terminate
  exception.
  '''
  print('Press Ctrl+C to stop bot')
  signal.sigwait([signal.SIGINT])
  raise Terminate()

async def waitlist_guard(client):
  try:
    trainings = await swim_trainings(client)
    if len(trainings) == 0:
      raise Exception('No swim trainings found')

    while True:
      # Deregister people who go to all swim trainings from one training that
      # hasn't started if all trainings are full
      all_full = reduce(lambda s, t: s and t.is_overbooked(), trainings)
      if all_full:
        registered = map(lambda tr: tr.get_registered(), trainings)
        go_to_all = reduce(lambda s, a: s.intersection(a), registered)
        for attendant in go_to_all:
          havent_started = filter(lambda tr: not tr.has_started(), trainings)
          to_delete_from = min(havent_started, key=lambda tr: tr.signed_up_at(attendant))
          print(f'Deregistering {attendant} (max sign-ups)')
          to_delete_from.deregister(attendant)

      # Deregister people who have been on the waitlist for too long
      for training in trainings:
        for (attendant, on_waitlist_since) in training.on_waitlist_since():
          if on_waitlist_since >= WAITLIST_CUT_OFF:
            print(f'Deregistering {attendant} (waitlist cut off)')
            training.deregister(attendant)

      await asyncio.sleep(180)
      for training in trainings:
        await training.refresh()
  except asyncio.CancelledError:
    pass
  except Exception as e:
    print(e)
    raise Terminate()

asyncio.run(main())
