#!/bin/bash
NAME="$1"
NID_OFFSET="$2"
BMC_IP="$3"
BMC_MAC=$(echo $FQDN|md5sum|sed 's/^\(..\)\(..\)\(..\)\(..\)\(..\).*$/02:\1:\2:\3:\4:\5/')
MAC="$4"
IP_ADDR="$5"
NID=$((NID_OFFSET + 1))
XNAME="x1000c0s0b${NID}"
cat >> /opt/ohpc/admin//nodes/nodes.yaml <<EOT
- name: ${NAME}
  nid: ${NID}
  xname: ${XNAME}
  bmc_ip: ${BMC_IP}
  bmc_mac: ${BMC_MAC}
  group: compute
  interfaces:
  - mac_adr: ${MAC}
    ip_addrs:
    - name: management
      ip_addr: ${IP_ADDR}
EOT