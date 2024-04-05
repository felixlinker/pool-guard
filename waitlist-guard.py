from argparse import ArgumentParser
from spond import spond
from datetime import datetime, timedelta
import asyncio

TCZ_ID = '3C7EBA9E0BB04B59A19784F1594EC57B'

parser = ArgumentParser()
parser.add_argument('-i', '--interval', default=300)
parser.add_argument('-p', '--password')
parser.add_argument('-u', '--user')

args = parser.parse_args()

def next_week_day(today_index, target_index):
  return (7 - (today_index - target_index)) % 7

def next_thursday(today_index):
  return next_week_day(today_index, 3)

async def main():
  s = spond.Spond(username=args.user, password=args.password)
  try:
    now = datetime.today()
    friday = now + timedelta(days=next_thursday(now.weekday()) + 1)
    tuesday = now + timedelta(days=next_thursday(now.weekday()) - 2)
    events = await s.get_events(
      group_id=TCZ_ID,
      include_scheduled=True,
      min_start=tuesday,
      max_end=friday
    )

    swim_trainings = list(map(lambda e: e['id'], filter(lambda e: e['heading'] == "TCZ Schwimtraining", events)))
  except Exception as e:
    print(e)
  finally:
    await s.clientsession.close()

asyncio.run(main())
