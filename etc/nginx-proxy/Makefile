S3_CACHE_HOST ?= cw-prerender-cache.sfo3.digitaloceanspaces.com
SPA_RENDER_HOST ?= spa-renderer-356378388264.northamerica-northeast1.run.app
UA_NEXUS5X ?= "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.89 Mobile Safari/537.36"
UA_DEFAULT ?= "Mozilla/5.0 (Linux) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.6668.89 Safari/537.36"

TEMPLATE_SUBST_ARGS = S3_CACHE_HOST SPA_RENDER_HOST UA_DEFAULT UA_NEXUS5X

define subst_template
sed $(foreach a,$(TEMPLATE_SUBST_ARGS),-e 's,@@$(a)@@,$($(a)),g') $1
endef

docker:
	docker build -t chefworks/spa-renderer:s3-nginx .

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
