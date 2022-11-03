# WEBFLEET integration

## How to install

Copy the files to your `config` directy of homeassistant underneath `custom_components`.

e.g. `config/custom_components/webfleet/__init__.py`

## How to start

Add a custom device tracker called `webfleet` to your configuration e.g.

    device_tracker:
    - platform: webfleet
        url: !secret webfleet_url 
        at: !secret webfleet_account
        username: !secret webfleet_username
        password: !secret webfleet_pwd
        group: !secret webfleet_group
        api_key: !secret webfleet_apikey
        new_device_defaults:
        track_new_devices: true

## Work in progress

Currently a lot of values are hard-coded and not ready for more. 
Contributions appreciated.
