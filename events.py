from datetime import datetime
from datetime import datetime, timedelta
from spond import spond
import logging
logger = logging.getLogger(__name__)

TCZ_ID = '3C7EBA9E0BB04B59A19784F1594EC57B'

class Event:
  def __init__(self, client: spond.Spond, uid: str, event_dict=None):
    self.client = client
    self.uid = uid

    self.accepted = dict()
    self.waiting_list = dict()
    self.unconfirmed = dict()
    self.starts_at = None
    self.name = None
    self.participant_names = dict()
    self.max_accepted = 25

    if event_dict is not None:
      self.__read_from(event_dict)
      self.participant_names = dict(map(
        lambda member: (member['id'], ' '.join([member.get('firstName', ''), member.get('lastName', '')])),
        event_dict['recipients']['group']['members']
      ))
      self.max_accepted = event_dict['maxAccepted']

  def __read_from(self, event_dict):
    self.name = event_dict['heading']
    self.starts_at = datetime.fromisoformat(event_dict['startTimestamp'])
    self.accepted = get_signup_times(event_dict['responses']['acceptedIds'], older=self.accepted)
    self.waiting_list = get_signup_times(event_dict['responses']['waitinglistIds'], older=self.waiting_list)
    self.unconfirmed = get_signup_times(event_dict['responses']['unconfirmedIds'], older=self.unconfirmed)

  def __str__(self) -> str:
    return f'{self.name} ({self.starts_at})'

  def has_started(self) -> bool:
    now = datetime.now(tz=self.starts_at.tzinfo)
    return self.starts_at <= now

  def get_registered(self) -> set[str]:
    return set(self.accepted.keys()).union(self.unconfirmed.keys())

  def signed_up_at(self, uid) -> datetime:
    return self.accepted[uid] or self.waiting_list[uid]

  def on_waitlist_since(self) -> list[tuple[str, datetime]]:
    now = datetime.now()
    return [ (a, now - dt) for (a, dt) in self.waiting_list.items()]

  def is_overbooked(self) -> bool:
    # Do this arithmetic because deregistering via my API does not cause a
    # refresh but deletes participants from all dicts. Here, I check whether
    # people _would have_ jumped into unconfirmed from the waiting_list.
    return 0 < len(self.waiting_list) + (len(self.accepted) + len(self.unconfirmed) - self.max_accepted)

  def get_participant_name(self, id) -> str:
    # Don't use .get default value for name not found because the API might not
    # return a name, which will result in storing an empty string in the dict.
    return self.participant_names.get(id, None) or '<name not found>'

  async def deregister(self, uid):
    self.accepted.pop(uid, None)
    self.waiting_list.pop(uid, None)
    self.unconfirmed.pop(uid, None)
    await self.client.update_response(self.uid, uid, False)

  async def refresh(self):
    # Do not update events that have started to discourage deregistering after
    # an event has ended.
    if self.has_started():
      return
    response = await self.client.get_event(self.uid)
    self.__read_from(response)

def next_week_day(today_index, target_index):
  return (7 - (today_index - target_index)) % 7

def next_thursday(today_index):
  return next_week_day(today_index, 3)

async def swim_trainings(client, parse=True) -> list[Event]:
  now = datetime.today()
  friday = now + timedelta(days=next_thursday(now.weekday()) + 1)
  tuesday = now + timedelta(days=next_thursday(now.weekday()) - 2)
  events = await client.get_events(
    group_id=TCZ_ID,
    include_scheduled=True,
    min_start=tuesday,
    max_end=friday
  )

  if not parse:
    return []

  return list(
    map(
      lambda e: Event(client, e['id'], e),
      filter(lambda e: e['heading'] == "TCZ Schwimtraining", events)
    )
  )

def get_signup_times(attendants: list[str], older=dict()) -> dict[str, datetime]:
  now = datetime.now()
  def to_entry(attendant):
    if older.get(attendant) is None:
      logger.debug(f'{attendant} signed-up just before f{now}')
    return (attendant, older.get(attendant, now))

  return dict(map(to_entry, attendants))
