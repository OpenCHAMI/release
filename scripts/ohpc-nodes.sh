#!/bin/bash
NAME="$1"
NID_OFFSET="$2"
BMC_IP="$3"
MAC="$4"
IP_ADDR="$5"
NID=$((NID_OFFSET + 1))
XNAME="x1000c0s0b${NID}"
cat >> /opt/ohpc/admin//nodes/nodes.yaml <<EOT
- name: ${NAME}
  nid: ${NID}
  xname: ${XNAME}
  bmc_ip: ${BMC_IP}
  group: compute
  interfaces:
  - mac_adr: ${MAC}
    ip_addrs:
    - name: management
      ip_addr: ${IP_ADDR}
EOT