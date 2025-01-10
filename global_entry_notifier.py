import argparse
import discord_webhook
import json
import logging
import requests
import yaml

parser = argparse.ArgumentParser()

parser.add_argument('config', default="config.yaml", help="Config file")
parser.add_argument('-d', '--debug', action='store_true', help="Debug mode")
parser.add_argument('-t', '--test', action='store_true', help="Test mode to send notification even if no appointments")

args = parser.parse_args()

# Read YAML file
with open(args.config, 'r') as stream:
  config_data = yaml.safe_load(stream)

test = args.test

webhook_url = config_data["webhook"]

if args.debug:
  logging.basicConfig(level=logging.DEBUG)
else:
  logging.basicConfig(level=logging.INFO)

for location in config_data["locations"]:
  logging.info(f"Location: {location}")
  appointments_found = False
  r = requests.get(f"https://ttp.cbp.dhs.gov/schedulerapi/slots?orderBy=soonest&limit=1&locationId={location}&minimum=1")
  slots = r.json()
  if len(slots) == 0:
    message = f"No appointments available for: {location}"
  else:
    message = f"Appointments found for: {location}!\n"
    message += json.dumps(slots, indent=4)
    appointments_found = True

  logging.info(message)

  if test or appointments_found:
    logging.info("Sending notification")
    webhook = discord_webhook.DiscordWebhook(url=webhook_url, content=message)
    webhook.execute()