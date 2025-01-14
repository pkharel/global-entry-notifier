import argparse
import discord_webhook
import json
import logging
import requests
import sched
import sys
import twilio
import time
import urllib
import yaml

from twilio.rest import Client

class GlobalEntryApiClient:
    GLOBAL_ENTRY_BASE_URL = "https://ttp.cbp.dhs.gov"
    SLOTS = "schedulerapi/slots"
    SLOTS_DEFAULT_PARAMS = {
        "orderBy": "soonest",
        "limit": "1",
        "minimum": "1"
    }
    LOCATIONS = "schedulerapi/locations"

    def __init__(self):
        pass

    def get_locations(self):
        return requests.get(f"{self.GLOBAL_ENTRY_BASE_URL}/{self.LOCATIONS}/")

    def get_slots(self, location_id):
        params = self.SLOTS_DEFAULT_PARAMS
        params["locationId"] = location_id
        return requests.get(f"{self.GLOBAL_ENTRY_BASE_URL}/{self.SLOTS}", params=params)

class GlobalEntryNotifier:
    def __init__(self, global_entry_client, locations, discord_webhook_url, twilio_config):
        self.global_entry_client = global_entry_client
        self.locations = locations
        self.discord_webhook_url = discord_webhook_url
        self.twilio_config = twilio_config
        # Create client if twilio info provided
        if self.twilio_config:
            self.twilio_config = twilio_config
            # Find your Account SID and Auth Token at twilio.com/console and set the
            # environment variables. See http://twil.io/secure
            self.twilio_client = Client(self.twilio_config["account_sid"], self.twilio_config["auth_token"])

    def send_voice_call(self):
        if self.twilio_client:
            execution = self.twilio_client.studio.v2.flows(
                self.twilio["studio_flow"]
            ).executions.create(to=self.twilio_config["to"], from_=self.twilio_config["from"])

    def send_notification(self, message):
        if self.discord_webhook_url:
            logging.info(f"Sending notification: {message}")
            webhook = discord_webhook.DiscordWebhook(url=self.discord_webhook_url, content=message)
            webhook.execute()

    def check_location(self, location):
        logging.info(f"Location: {location}")
        # Add location id to query params
        r = self.global_entry_client.get_slots(location)
        r.raise_for_status()
        slots = r.json()
        return slots

    def check_locations(self):
        found_appointment = False
        for location in self.locations:
            try:
                slots = self.check_location(location)
            except requests.exceptions.HTTPError as err:
                msg = str(err)
                logging.error(str(err))
                self.send_notification(msg)
                if err.response.headers.get('Content-Type') and err.response.headers.get('Content-Type').startswith('application/json'):
                    msg = json.dumps(err.response.json(), indent=4)
                self.send_notification(msg)
                continue
            if len(slots) == 0:
                logging.info(f"No appointments found for {location}")
            else:
                msg = f"Appointments found for {location}!"
                logging.info(msg)
                self.send_notification(msg)
                self.send_notification(json.dumps(slots, indent=4))
                found_appointment = True
        # Only send out one voice call for any appointment found
        if found_appointment:
            self.send_voice_call()


parser = argparse.ArgumentParser()

parser.add_argument("config", nargs='?', default="config.yaml", help="Config file")
parser.add_argument("-d", "--debug", action="store_true", help="Debug mode")
parser.add_argument("-f", "--file", help="Store log in file")
parser.add_argument("-l", "--locations", action="store_true", help="Print locations")

args = parser.parse_args()

# Set up better formatting for logger
FORMAT = "%(asctime)s %(levelname)-8s %(message)s"
logging.basicConfig(
    level=logging.DEBUG,
    format=FORMAT,
    handlers=[
        logging.FileHandler("global_entry_notifier.log"),
        logging.StreamHandler(),
    ],
)

global_entry_client = GlobalEntryApiClient()

if args.locations:
    locations = global_entry_client.get_locations().json()
    for location in locations:
        print(f"{location['id']} : {location['name']}")
    sys.exit()

# Parse config file
with open(args.config, "r") as stream:
    config_data = yaml.safe_load(stream)

twilio_config = config_data.get("twilio")

notifier = GlobalEntryNotifier(
    global_entry_client, config_data["locations"], config_data["webhook"], twilio_config
)

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