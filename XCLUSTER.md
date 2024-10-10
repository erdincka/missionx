# FOR REFERENCE ONLY

Refer to [Documentation](https://docs.ezmeral.hpe.com/datafabric-customer-managed/78/ReferenceGuide/configure-crosscluster.sh.html)


```bash

#!/usr/bin/env bash

set -euo pipefail

corehost=""
edgehost=""
adminuser="mapr"
adminpassword=""

# save for cross-cluster setup
for CLUSTER_IP in $corehost $edgehost; do
    ssh -o StrictHostKeyChecking=no $MAPR_USER@$CLUSTER_IP "grep ssl.server.truststore /opt/mapr/conf/store-passwords.txt | cut -d'=' -f2" > /tmp/${CLUSTER_IP}_truststore_pwd
done

local_truststore_password=$(</tmp/${corehost}_truststore_pwd)
remote_truststore_password=$(</tmp/${edgehost}_truststore_pwd)

[[ -n "${local_truststore_password}" && "${remote_truststore_password}" ]] && echo "local:${local_truststore_password} remote:${remote_truststore_password}" || exit 1

cross_cluster_setup="""
#!/usr/bin/env bash
set -euo pipefail
sudo dnf install -y pssh
pip install expect
sudo rm -rf /tmp/mapr-xcs
sudo -i -u ${adminuser} /opt/mapr/server/configure-crosscluster.sh create all \
    -localcrossclusteruser ${adminuser} -remotecrossclusteruser ${adminuser} \
    -localtruststorepassword ${local_truststore_password} \
    -remotetruststorepassword ${remote_truststore_password} \
    -remoteip ${edgehost} -localuser ${adminuser} -remoteuser ${adminuser} << EOM
$adminpassword
$adminpassword
EOM
exit 0
"""

# This will fail if adminuser is not in sudoers file.
echo "$cross_cluster_setup" | ssh -t -o StrictHostKeyChecking=no $adminuser@$corehost

```