from datetime import datetime
from datetime import datetime, timedelta

TCZ_ID = '3C7EBA9E0BB04B59A19784F1594EC57B'

class Event:
  def __init__(self, client, uid: str, event_dict=None):
    self.client = client
    self.uid = uid

    self.accepted = dict()
    self.waiting_list = dict()
    self.unconfirmed = dict()
    self.starts_at = None

    if event_dict is not None:
      self.__read_from(event_dict)

  def __read_from(self, event_dict):
    self.starts_at = datetime.fromisoformat(event_dict['startTimestamp'])
    self.accepted = get_signup_times(event_dict['responses']['acceptedIds'], older=self.accepted)
    self.waiting_list = get_signup_times(event_dict['responses']['waitinglistIds'], older=self.waiting_list)
    self.unconfirmed = get_signup_times(event_dict['responses']['unconfirmedIds'], older=self.unconfirmed)

  def has_started(self) -> bool:
    now = datetime.now(tz=self.starts_at.tzinfo)
    return self.starts_at <= now

  def get_registered(self) -> set[str]:
    return set(self.accepted.keys()).union(self.waiting_list.keys())

  def signed_up_at(self, uid) -> datetime:
    return self.accepted[uid] or self.waiting_list[uid]

  def on_waitlist_since(self) -> list[tuple[str, datetime]]:
    now = datetime.now(tz=self.starts_at.tzinfo)
    return [ (a, now - dt) for (a, dt) in self.waiting_list.items()]

  def is_overbooked(self) -> bool:
    return 0 < len(self.waiting_list)

  async def deregister(self, uid):
    await self.client.update_response(self.uid, uid, False)

  async def refresh(self):
    response = await self.client.get_event(self.uid)
    self.__read_from(response)

def next_week_day(today_index, target_index):
  return (7 - (today_index - target_index)) % 7

def next_thursday(today_index):
  return next_week_day(today_index, 3)

async def swim_trainings(client) -> list[Event]:
  now = datetime.today()
  friday = now + timedelta(days=next_thursday(now.weekday()) + 1)
  tuesday = now + timedelta(days=next_thursday(now.weekday()) - 2)
  events = await client.get_events(
    group_id=TCZ_ID,
    include_scheduled=True,
    min_start=tuesday,
    max_end=friday
  )

  return list(
    map(
      lambda e: Event(client, e['id'], e),
      filter(lambda e: e['heading'] == "TCZ Schwimtraining", events)
    )
  )

def get_signup_times(attendants: list[str], older=dict()) -> dict[str, datetime]:
  now = datetime.now()
  def to_entry(attendant):
    return (attendant, older.get(attendant, now))

  return dict(map(to_entry, attendants))
