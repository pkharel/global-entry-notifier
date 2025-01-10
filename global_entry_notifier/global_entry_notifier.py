import argparse
import discord_webhook
import json
import logging
import requests
import sched
import twilio
import time
import yaml

from twilio.rest import Client

class GlobalEntryNotifier:
    def __init__(self, webhook, twilio, locations, test):
        self.twilio = twilio
        self.webhook = webhook
        self.locations = locations
        self.test = test

    def send_voice_call(self):
        # Download the helper library from https://www.twilio.com/docs/python/install
        # Find your Account SID and Auth Token at twilio.com/console
        # and set the environment variables. See http://twil.io/secure
        account_sid = self.twilio["account_sid"]
        studio_flow = self.twilio["studio_flow"]
        auth_token = self.twilio["auth_token"]
        from_num   = self.twilio["from"]
        to_num   = self.twilio["to"]
        client = Client(account_sid, auth_token)
        execution = client.studio.v2.flows(
            studio_flow
        ).executions.create(to=to_num, from_=from_num)
        logging.info(execution.sid)

    def send_notification(self, message):
        logging.info(f"Sending notification: {message}")
        webhook = discord_webhook.DiscordWebhook(url=self.webhook, content=message)
        webhook.execute()

    def check_location(self, location):
        logging.info(f"Location: {location}")
        r = requests.get(
            f"https://ttp.cbp.dhs.gov/schedulerapi/slots?orderBy=soonest&limit=1&locationId={location}&minimum=1"
        )
        r.raise_for_status()
        slots = r.json()
        return slots

    def check_locations(self):
        found_appointment = False
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
                found_appointment = True
        if found_appointment:
            self.send_voice_call()


parser = argparse.ArgumentParser()

parser.add_argument("config", default="config.yaml", help="Config file")
parser.add_argument("-d", "--debug", action="store_true", help="Debug mode")
parser.add_argument("-f", "--file", help="Store log in file")
parser.add_argument(
    "-t",
    "--test",
    action="store_true",
    help="Test mode to send notification even if no appointments",
)

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

# Parse config file
with open(args.config, "r") as stream:
    config_data = yaml.safe_load(stream)

twilio_config = config_data.get("twilio")

notifier = GlobalEntryNotifier(
    config_data["webhook"], twilio_config, config_data["locations"], args.test
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
