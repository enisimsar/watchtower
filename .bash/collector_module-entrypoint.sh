#!/bin/sh

pipenv install
pipenv run python3 ./collector_module/link_collector_for_redis.py
