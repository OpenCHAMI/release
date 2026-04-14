#!/bin/bash

CLIENT="${1}"
SERVICE="smd"

TOKENSMITH_BOOTSTRAP_TOKEN=$(podman exec -e SERVICE=$SERVICE -e CLIENT=$CLIENT tokensmith /bin/sh -c "\
			/usr/local/bin/tokensmith mint-bootstrap-token \
			--key-file /tmp/tokensmith/keys/private.pem \
			--service-id ${CLIENT}-client \
			--target-service ${SERVICE}
			")
SECRET_NAME="${CLIENT}-bootstrap-token"
printf '%s' "$TOKENSMITH_BOOTSTRAP_TOKEN" | podman secret rm ${SECRET_NAME} 2>/dev/null || true
printf '%s' "$TOKENSMITH_BOOTSTRAP_TOKEN" | podman secret create ${SECRET_NAME} -