FROM python:3.11.12-bullseye AS python

FROM python AS build-stage-python

ARG BUILD_ENVIRONMENT=local

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev

COPY ./requirements .

RUN pip wheel --wheel-dir /usr/src/app/wheels -r ${BUILD_ENVIRONMENT}.txt

FROM python AS run-stage-python

ARG BUILD_ENVIRONMENT=local
ARG APP_HOME=/src

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR ${APP_HOME}

RUN apt-get update && apt-get install --no-install-recommends -y \
    libpq-dev \
    gettext \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build-stage-python /usr/src/app/wheels /wheels/

RUN pip install --no-cache-dir --no-index --find-link=/wheels/ /wheels/*

COPY ./docker/local/django/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//g' /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY ./docker/local/django/start.sh /start.sh
RUN sed -i 's/\r$//g' /start.sh
RUN chmod +x /start.sh

COPY ./docker/local/django/celery/worker/start.sh /worker.sh
RUN sed -i 's/\r$//g' /worker.sh
RUN chmod +x /worker.sh

COPY ./docker/local/django/celery/flower/start.sh /flower.sh
RUN sed -i 's/\r$//g' /flower.sh
RUN chmod +x /flower.sh

COPY ./docker/local/django/celery/beat/start.sh /beat.sh
RUN sed -i 's/\r$//g' /beat.sh
RUN chmod +x /beat.sh

COPY . ${APP_HOME}

ENTRYPOINT ["/entrypoint.sh"]