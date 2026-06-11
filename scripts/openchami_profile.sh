#!/bin bash
# /etc/profile.d/openchami.sh

CONTAINER_CMD=/usr/bin/podman
CURL_CONTAINER=cgr.dev/chainguard/curl
CURL_TAG=latest


get_eth0_ipv4() {
   local ipv4
    ipv4=$(ip -o -4 addr show eth0 | awk '{print $4}')
    echo "${ipv4%/*}"
}

get_ca_cert() {
    local ca_cert
    ${CONTAINER_CMD:-docker} exec -it step-ca step ca root
    echo "${ca_cert}"
}

container_curl() {
    local url=$1
    ${CONTAINER_CMD:-docker} run -it --rm "${CURL_CONTAINER}:${CURL_TAG}" -s $url
}

gen_access_token() {
    ${CONTAINER_CMD:-docker} exec tokensmith \
	    /bin/sh \
	    -c \
	    "/usr/local/bin/tokensmith \
		user-token \
		create \
		--audience smd \
		--key-file /tokensmith/data/keys/private.pem \
		--subject 'admin@example.com' \
		--scopes 'admin' \
		--enable-local-user-mint"
}


create_podman_secret() {
    local name=""
    local secret=""
    local force=false
    local random=false
    local length=16

    while [[ $# -gt 0 ]]; do
        case $1 in
            --name)
                name=$2
                shift 2
                ;;
            --secret)
                secret=$2
                shift 2
                ;;
            --force)
                force=true
                shift
                ;;
            --random)
                random=true
                shift
                ;;
            --length)
                length=$2
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                return 1
                ;;
        esac
    done

    if [[ -z $name ]]; then
        echo "Secret name is required"
        return 1
    fi

    if $random; then
        secret=$(tr -dc '[:alnum:]' < /dev/urandom | head -c $length)
    fi

    if [[ -z $secret ]]; then
        echo "Secret content is required"
        return 1
    fi

    if $force; then
        ${CONTAINER_CMD:-docker} secret rm $name 2>/dev/null
    fi

    echo -n $secret | ${CONTAINER_CMD:-docker} secret create $name -
}
