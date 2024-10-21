# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.12-slim-bullseye

# Allow statements and log messages to immediately appear in the Knative logs
ENV DEBIAN_FRONTEND=noninteractive \
        DEBCONF_NONINTERACTIVE_SEEN=true \
        LC_ALL=C.UTF-8 \
        LANG=C.UTF-8 \
        PIPENV_VENV_IN_PROJECT=1 \
        PYTHONUNBUFFERED=true

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN playwright install-deps
RUN playwright install chromium
COPY . ./

ENV PORT 8080

# we need the following expose for the test_image job service in .gitlab-ci.yml
EXPOSE 8080

CMD exec fastapi run app.py --port $PORT

