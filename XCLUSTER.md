# FOR REFERENCE ONLY

Refer to [Documentation](https://docs.ezmeral.hpe.com/datafabric-customer-managed/78/ReferenceGuide/configure-crosscluster.sh.html)


You can use the script below to configure cross cluster connectivity between two clusters.

!!! USE AT YOUR OWN RISK !!!

```bash
#!/usr/bin/env bash

set -euo pipefail

command -v pssh || { echo "pssh not found, please install it using 'sudo dnf install -y pssh'"; exit 1; }
command -v expect || { echo "expect not found, please install it using 'sudo dnf install -y expect'"; exit 1; }

# This script is used to configure cross cluster connectivity between two clusters.
# It requires the following environment variables:
corehost=""
edgehost=""
adminuser="mapr"
adminpassword=""

grepcmd="grep ssl.server.truststore /opt/mapr/conf/store-passwords.txt | cut -d'=' -f2"

# save for cross-cluster setup
for host in $corehost $edgehost; do
    ssh -o StrictHostKeyChecking=no $adminuser@$host "$grepcmd" > /tmp/${host}_truststore_pwd
done

local_truststore_password=$(</tmp/${corehost}_truststore_pwd)
remote_truststore_password=$(</tmp/${edgehost}_truststore_pwd)

cross_cluster_setup="""
/opt/mapr/server/configure-crosscluster.sh create all \
    -localcrossclusteruser ${adminuser} -remotecrossclusteruser ${adminuser} \
    -localtruststorepassword ${local_truststore_password} \
    -remotetruststorepassword ${remote_truststore_password} \
    -remoteip ${edgehost} -localuser ${adminuser} -remoteuser ${adminuser} << EOM
$adminpassword
$adminpassword
EOM
"""

echo "$cross_cluster_setup" | ssh -t -o StrictHostKeyChecking=no $adminuser@$corehost

# login as root on both clusters and generate tickets - following commands require passwordless sudo for adminuser

ssh -o StrictHostKeyChecking=no $adminuser@$corehost <<EOM
sudo maprlogin password -user $adminuser -cluster <core-cluster-name>
sudo maprlogin password -user $adminuser -cluster <edge-cluster-name>
EOM

ssh -o StrictHostKeyChecking=no $adminuser@$edgehost <<EOM
sudo maprlogin password -user $adminuser -cluster <core-cluster-name>
sudo maprlogin password -user $adminuser -cluster <edge-cluster-name>
EOM

# OPTIONAL - Set MCS for cross-cluster communication
ssh -o StrictHostKeyChecking=no $adminuser@$corehost <<EOM
maprlogin generateticket -type service -cluster <edge-cluster-name> -user $adminuser -duration 90:0:0 -out /tmp/maprservice_ticket
cat /tmp/maprservice_ticket >> /opt/mapr/conf/mapruserticket
EOM

ssh -o StrictHostKeyChecking=no $adminuser@$edgehost <<EOM
maprlogin generateticket -type service -cluster <core-cluster-name> -user $adminuser -duration 90:0:0 -out /tmp/maprservice_ticket
cat /tmp/maprservice_ticket >> /opt/mapr/conf/mapruserticket
EOM


```

~~ Add gateway TXT records in the DNS for cross-cluster replication and NFS to work ~~ follow the [documentation](https://docs.ezmeral.hpe.com/datafabric-customer-managed/78/ClusterAdministration/admin/cluster/GenerateGatewayDNS.html)
