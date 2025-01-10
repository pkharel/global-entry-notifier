import argparse
import discord_webhook
import json
import logging
import requests
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
    if self.test:
      self.send_notification("Test Notification")
      return

    for location in self.locations:
      try:
        slots = self.check_location(location)
      except requests.exceptions.HTTPError as err:
        msg = f"HTTP error occurred"
        logging.error(msg)
        self.send_notification(msg)
        self.send_notification(json.dumps(err.response.json(), indent=4))
        continue
      #self.send_notification(f"No appointments found for {location}")
      if len(slots) != 0:
        self.send_notification(f"Appointments found for {location}!")
        self.send_notification(json.dumps(slots, indent=4))

parser = argparse.ArgumentParser()

parser.add_argument('config', default="config.yaml", help="Config file")
parser.add_argument('-d', '--debug', action='store_true', help="Debug mode")
parser.add_argument('-t', '--test', action='store_true', help="Test mode to send notification even if no appointments")

args = parser.parse_args()

if args.debug:
  logging.basicConfig(level=logging.DEBUG)
else:
  logging.basicConfig(level=logging.INFO)

# Parse config file
with open(args.config, 'r') as stream:
  config_data = yaml.safe_load(stream)

notifier = GlobalEntryNotifier(config_data["webhook"], config_data["locations"], args.test)
notifier.check_locations()