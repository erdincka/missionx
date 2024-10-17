# Edge to Core end-to-end data pipeline using Ezmeral Data Fabric

## Summary

In a partially connected world of field teams, seamless communication and data sharing may be critical for the success or failure of a mission, or even resulting in fatal casualties.

In this demo, we are building a data pipeline using 2 Ezmeral Data Fabric cluster that are using microservices to communicate with each other (via message streaming) and providing on-demand access to data relevant to the field team utilising their limited bandwidth by only exchanging messages and files that they requested.

You can install the app on Ezmeral Unified Analytics platform with "Import Framework" option by using [provided helm chart](./helm-package/demoapp-0.0.6.tgz) and [provided image](./helm-package/logoX.png) as its icon. Don't forget to change the "demo" name to 'missionx' (and probably the "endpoint" hostname from demoapp to something you want, ie, missionx) in the values.yaml while importing the app.

If needed, follow the instructions from [Ezmeral documentation](https://docs.ezmeral.hpe.com/unified-analytics/15/ManageClusters/importing-applications.html).


## Prerequisites

Setup Data Fabric clusters with Cross Cluster (Global Namespace) enabled. Refer to [this](./XCLUSTER.md) for details. Optionally create a user with volume, table and stream creation rights. For isolated/standalone demo environments, you can simply use the cluster admin `mapr` user.

Data Fabric core cluster should have following packages installed and configured:

```bash
# mapr-hivemetastore
mapr-kafka
mapr-nfs4server # or mapr-nfs ### Global Namespace with external NFS mount will work only with mapr-nfs4server
mapr-data-access-gateway # used for REST API access
mapr-gateway # used for stream replication
# mapr-hbase
```

You will need to enable cluster and data auditing in the cluster to be able to monitor stream replication status. If you use the cluster admin 'mapr' user, these will be configured automatically with the Initial configuration step below.

Additionally, you need to [Configure Gateways for Table and Stream Replication](https://docs.ezmeral.hpe.com/datafabric-customer-managed/78/Gateways/ConfiguringMapRGatewaysForTRAndI.html#task_clg_ywy_5t).

### Initial configuration

Use the disconnected link icon to complete initial setup. This will require you to provide the host details to connect to the Data Fabric node where Data Access Gateway service is running. It will update the app configuration, and create the required (/apps/missionX and /apps/missionX/files) volumes and streams on the Data Fabric cluster.

## Demo Flow

### HQ Services

First step of our data flow is the ingest data from simulated IMAGE Feed service. This service will select a few random messages on each run (every few seconds) from the pre-integrated set of files (which is taken from real IMAGE feed from 2014), and publishes them into the Pipeline stream as an available asset information. This message contains limited information (metadata) regarding the asset and provides a link to download the actual data (image/video).

Next service, Image Download Service, automatically picks up messages from the Pipeline stream, and attempts to download the actual asset data from the link in the message. This file will then be copied into the Ezmeral Data Fabric volume for persistence. Image Download Service will then update the message with a status code that indicates asset is ready to be broadcasted.

The Asset Broadcast Service will monitor the pipeline to see the assets that are ready to be broadcasted to the field teams. Once Image Download Service marks an asset as downloaded, Asset Broadcast Service will publish that asset information into a replicated stream, which will make the message available to all the replicas (every edge cluster, or field team) so they can see updated information as they become available.

Final HQ service, Asset Response Service is waiting for a specific topic (ASSET_REQUEST) that has messages for the assets requested from the field teams, and responds to these requests by copying the actual asset data into a mirrored volume. So once the response is complete, field teams can re-initiate the mirroring to get the asset data on their cluster.

### Edge Services

Edge teams first need to ensure Upstream Communication is enabled, meaning the replicated stream is receiving message, and Volume can start mirroring when they made a request for an asset.

Stream replication happens continuously as long as connectivity between clusters is established.

When the Broadcast Listener Service is started, it will monitor the replica stream for any broadcasted asset, and will place the information into the table for the team to monitor/select.

Asset Request Service will wait for any message that is marked as "Requesting..." from the table, which in turn will publish a message to the "ASSET_REQUEST" topic. Since the Data Fabric Streams are bi-directional (multi-master), we can have "ASSET_BROADCAST" topic to publish messages from HQ to all field teams, and "ASSET_REQUEST" topic to publish messages from the field teams back to the HQ. Once the request is published, you will see the asset being marked as "Requested" on the table.

At that point, you would monitor the tiles on HQ side, which should show an "Asset Response" for the requested asset, which means the data is copied and available on the mirrored volume. This may take a few minutes due to delays introduced in the app (so not everything flows very fast) and also for the fact that stream replication is not synchronous.

Once the asset request is responded, then the field team can start Asset Viewer Service and then re-initiate the volume mirror to get the asset data files to be sent. This process also can take from few seconds to a minute, but then you should see the tile being displayed with the actual asset data (image) copied from the HQ volume. We keep volume mirror as a manual process to give full control to the field team on when they would like to use their bandwidth for data transfers.

## Demo Highlights

TBD

## NOTES

You may stop running apps by clicking on their names at the left hand side list. This may be useful if there are too many messages and/or tiles flowing and you have troubles finding the ones that you are interested.

It is also useful, since at times services may fail silently, but UI is not updated with that. In those cases, just stop the services and restart them.

You can also enable debug logging to see the details of the flow using the switch at the top-right corner.
