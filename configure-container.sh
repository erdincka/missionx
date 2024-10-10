#!/usr/bin/env bash

set -euo pipefail

## Ensure user
export MAPR_GROUP=mapr \
    MAPR_HOME=/opt/mapr \
    MAPR_UID=5000
id mapr || useradd -u ${MAPR_UID} -U -m -d /home/${MAPR_USER} -s /bin/bash -G sudo ${MAPR_USER}

[ -f ~/.ssh/id_rsa ] || ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -q -N ""

# Enable passwordless login
sshpass -p "${MAPR_PASS}" ssh-copy-id -o StrictHostKeyChecking=no "${MAPR_USER}@${CLUSTER_IP}"
