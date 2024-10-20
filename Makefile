AUTO_FIX_IMPORTS ?= 1
RELEASE = 1.0.1
APP_NAME = spa-renderer
DOCKER_CONTAINER_NAME = $(APP_NAME)
DOCKER_CONTAINER_PORT = 8080
DOCKER_REPOSITORY =
DOCKER_IMG_TAG = $(DOCKER_REPOSITORY)$(APP_NAME)
PORT ?= 8080
GCLOUD_PROJECT = chefworks-1214
export PIPENV_DONT_LOAD_ENV = 1

ifneq ($(AUTO_FIX_IMPORTS), 1)
  autofix = --check-only
endif

test: static unit

init: init-python

ifdef PIPENV_SYNC_DEV
init-python: PIPENV_DEV = --dev
endif
init-python:
	pip3 install --upgrade pip
	pip install pipenv
	pipenv sync $(PIPENV_DEV)

unit:
	pipenv run python -m pytest

static: imports flake8 pylint

flake8:
	pipenv run flake8 $(shell find -name '*\.py')

pylint:
	pipenv run pylint -E $(shell find -name '*\.py')

imports:
	pipenv run isort $(autofix) $(shell find -name '*\.py')

run dev:
	pipenv run fastapi $@ app.py --port $(PORT)

################################## docker ########################
# Freezes all packages, and then returns all strings that don't match "en-core-web-",
# Before saving them to requirements.txt.
requirements.txt:
	pipenv requirements > $@

docker: requirements.txt
	docker build -t $(DOCKER_IMG_TAG):$(RELEASE) .
ifeq ($(DOCKER_PUSH),1)
	docker push $(DOCKER_IMG_TAG):$(RELEASE)
endif

########################################## deploy/gcloud #########################
git-tag:
	@git diff --quiet HEAD || (echo uncommitted changes && false)
	git tag -f $(RELEASE)
	git push -f origin $(RELEASE)

deploy: docker docker-test git-tag gcloud

gcloud: gcloud-config \
	gcloud-build \
	gcloud-svc

gcloud-config:
	gcloud config set project $(GCLOUD_PROJECT)

gcloud-build: requirements.txt
	gcloud builds submit --tag gcr.io/$(GCLOUD_PROJECT)/$(APP_NAME)

gcloud-svc: gcloud-svc-$(APP_NAME)

gcloud-svc-$(APP_NAME):
	. ./.env.local; gcloud run deploy $(APP_NAME) \
		--image=gcr.io/$(GCLOUD_PROJECT)/$(APP_NAME) \
		--allow-unauthenticated \
		--concurrency=1 \
		--cpu=2 \
		--memory=4Gi \
		--max-instances=10 \
		--set-env-vars=STORE_PAGES=$$STORE_PAGES,S3_ENDPOINT=$$S3_ENDPOINT,S3_BUCKET_NAME=$$S3_BUCKET_NAME,S3_ACCESS_KEY=$$S3_ACCESS_KEY,READY_CONDITIONS=$$READY_CONDITIONS,REMOVE_ELEMENTS=$$REMOVE_ELEMENTS,S3_SECRET_KEY=$$S3_SECRET_KEY \
		--execution-environment=gen2 \
		--region=northamerica-northeast1 \
		--project=$(GCLOUD_PROJECT)

install-gcloud-sdk:
	echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
	sudo apt-get install -y apt-transport-https ca-certificates gnupg
	curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
	sudo apt-get update && sudo apt-get install -y google-cloud-sdk

#####################################################################################

clean:
	-$(TELEPRESENCE) quit
	rm -rf .state
	find -name .pytest_cache -o -name __pycache__ | xargs rm -rf
	find -name '*~' | xargs rm

.PHONY: requirements.txt test_api.html
