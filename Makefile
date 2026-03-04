IMAGE  := ghcr.io/hellothisisflo/sketchpad
SHA    := $(shell git rev-parse --short HEAD)
TAG    := sha-$(SHA)
NS     := sketchpad

.PHONY: build push deploy all status

build:
	docker build -t $(IMAGE):$(TAG) -t $(IMAGE):latest .

push:
	docker push $(IMAGE):$(TAG)
	docker push $(IMAGE):latest

deploy:
	kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -n $(NS)
	kubectl rollout status deployment/sketchpad -n $(NS) --timeout=120s

all: build push deploy

status:
	kubectl get pods -n $(NS)
	kubectl get svc -n $(NS)
