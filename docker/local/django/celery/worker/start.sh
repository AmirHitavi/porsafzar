#!/bin/bash
set -o errexit
set -o nounset

#cd /src/core
exec celery -A config.celery worker -l info