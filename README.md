# Global Entry Notifier
Notifications for Global Entry Interview slots

## Install 
```
git@github.com:pkharel/global-entry-notifier.git
python -m venv vevn
source venv/bin/activate
pip install -r requirements.txt
```

## Setup
Create a config file like the one below
```
webhook: https://<DISCORD_WEBHOOK>
# timer is optional
timer: 60
locations:
  # location ID
  - 12021
```

## Run
```
python global_entry_notifier config.yaml --debug
```
