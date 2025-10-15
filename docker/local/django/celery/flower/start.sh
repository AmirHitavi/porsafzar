#!/bin/bash
set -o errexit
set -o nounset

exec celery -A config.celery  -b "${CELERY_BROKER_URL}" flower --basic-auth="${CELERY_FLOWER_USER}":"${CELERY_FLOWER_PASSWORD}"