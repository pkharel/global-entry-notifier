import argparse
import discord_webhook
import json
import logging
import requests
import sched
import time
import yaml


class GlobalEntryNotifier:
  def __init__(self, webhook, locations, test):
    self.webhook = webhook
    self.locations = locations
    self.test = test

  def send_notification(self, message):
      logging.info(f"Sending notification: {message}")
      webhook = discord_webhook.DiscordWebhook(url=self.webhook, content=message)
      webhook.execute()

  def check_location(self, location):
    logging.info(f"Location: {location}")
    r = requests.get(f"https://ttp.cbp.dhs.gov/schedulerapi/slots?orderBy=soonest&limit=1&locationId={location}&minimum=1")
    #r = requests.get(f"https://ttp.cbp.dhs.gov/schedulerapi/slots?orderBy=soonest&limit=1&locationId=sadlfkjaslas&minimum=1")
    r.raise_for_status()
    slots = r.json()
    return slots

  def check_locations(self):
    for location in self.locations:
      # Send out test notification
      if self.test:
        self.send_notification(f"Test Notification for {location}")
        continue
      try:
        slots = self.check_location(location)
      except requests.exceptions.HTTPError as err:
        msg = f"HTTP error occurred"
        logging.error(msg)
        self.send_notification(msg)
        self.send_notification(json.dumps(err.response.json(), indent=4))
        continue
      if len(slots) == 0:
        logging.info(f"No appointments found for {location}")
      else:
        msg = f"Appointments found for {location}!"
        logging.info(msg)
        self.send_notification(msg)
        self.send_notification(json.dumps(slots, indent=4))

parser = argparse.ArgumentParser()

parser.add_argument('config', default="config.yaml", help="Config file")
parser.add_argument('-d', '--debug', action='store_true', help="Debug mode")
parser.add_argument('-f', '--file', help = "Store log in file")
parser.add_argument('-t', '--test', action='store_true', help="Test mode to send notification even if no appointments")

args = parser.parse_args()

# Set up better formatting for logger
FORMAT="%(asctime)s %(levelname)-8s %(message)s"
logging.basicConfig(level=logging.DEBUG, format=FORMAT, handlers=[
        logging.FileHandler("global_entry_notifier.log"),
        logging.StreamHandler()
    ]
)

# Parse config file
with open(args.config, 'r') as stream:
  config_data = yaml.safe_load(stream)

notifier = GlobalEntryNotifier(config_data["webhook"], config_data["locations"], args.test)

timer = config_data.get("timer")

# Function to check locations every timer seconds
def run_in_loop(scheduler, timer, notifier):
  scheduler.enter(timer, 1, run_in_loop, (scheduler, timer, notifier))
  notifier.check_locations()

if timer:
  logging.info(f"Will run every {timer} seconds")
  scheduler = sched.scheduler(time.time, time.sleep)
  scheduler.enter(0, 1, run_in_loop, (scheduler, timer, notifier))
  scheduler.run()
else:
  notifier.check_locations()