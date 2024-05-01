import json
import os
import socket

from helpers import *
from nicegui import app
from time import sleep

# from sparking import spark_kafka_consumer
from streams import consume, produce

logger = logging.getLogger()


@fire_and_forget
def audit_listener_service():
    """
    Listens the auditlogstream to see if upstream replication is established.
    """

    audit_stream_path = f"/var/mapr/auditstream/auditlogstream"
    upstreamSource = f"{HQ_VOLUME_PATH}/{HQ_STREAM_REPLICATED}"

    app.storage.general["services"]["auditlistener"] = True

    logger.setLevel(logging.DEBUG)
    logger.debug("started...")

    while True:
        # skip if service is disabled by user
        if not app.storage.general["services"].get("auditlistener", False):
            logger.debug("sleeping...")
            sleep(AUDIT_LISTENER_DELAY)
            continue

        logger.debug("running...")

        host_fqdn = socket.getfqdn(os.environ["MAPR_IP"])
        
        for msg in consume(
            stream=audit_stream_path,
            topic=f"{os.environ['MAPR_CLUSTER']}_db_{host_fqdn}",
        ):
            record = json.loads(msg)
            logger.debug("Received: %s", record)

            if (
                record["operation"] == "DB_UPSTREAMADD"
                and record["upstreamPath"] == upstreamSource
            ):
                app.storage.general["stream_replication_established"] = True
                logger.info("REPLICATION ESTABLISHED")
                # if replication is on, subscribe to messages from upstream
                logger.info("TODO: read replicated messages from edge")
                # app.storage.general["services"]["upstreamcomm"] = True
                # upstream_comm_service()

            else:
                logger.debug("Uninterested operation %s", record['operation'])

            app.storage.general["auditlistener_count"] = (
                app.storage.general.get("auditlistener_count", 0) + 1
            )

        # add delay to publishing
        sleep(AUDIT_LISTENER_DELAY)


@fire_and_forget
def broadcast_listener_service():
    """
    Process messages in ASSET_BROADCAST topic
    """

    stream_path = f"/mapr/{os.environ['EDGE_CLUSTER']}/{EDGE_VOLUME_PATH}/{EDGE_STREAM_REPLICATED}"

    input_topic = TOPIC_ASSET_BROADCAST

    app.storage.general["services"]["broadcastlistener"] = True
    app.storage.general["edge_broadcastreceived"] = []

    logger.debug("started...")

    while True:
        # skip if service is disabled by user
        if not app.storage.general["services"].get("broadcastlistener", False):
            logger.debug("sleeping...")
            sleep(BROADCAST_LISTENER_DELAY)
            continue

        logger.debug("running...")

        try:
            for msg in consume(stream=stream_path, topic=input_topic):
                record = json.loads(msg)
                logger.debug("Received: %s", record)

                record['status'] = "received"
                app.storage.general["edge_broadcastreceived"].append(record)

                app.storage.general["broadcastlistener_count"] = (
                    app.storage.general.get("broadcastlistener_count", 0) + 1
                )
        except Exception as error:
            logger.debug(error)

        # add delay to publishing
        sleep(BROADCAST_LISTENER_DELAY)


@fire_and_forget
def asset_request_service():
    """
    Request assets by reading from queue and putting them to the replicated stream on ASSET_REQUEST topic
    """

    stream_path = f"/mapr/{os.environ['EDGE_CLUSTER']}/{EDGE_VOLUME_PATH}/{EDGE_STREAM_REPLICATED}"

    output_topic = TOPIC_ASSET_REQUEST

    app.storage.general["services"]["assetrequest"] = True

    logger.debug("started...")

    while True:
        # skip if service is disabled by user
        if not app.storage.general["services"].get("assetrequest", False):
            logger.debug("sleeping...")
            sleep(ASSET_REQUEST_DELAY)
            continue

        logger.debug("running...")

        try:
            while len(app.storage.general.get("requested_assets", [])) > 0:
                asset = app.storage.general["requested_assets"].pop()
                # Publish to request topic on the replicated stream
                if produce(stream=stream_path, topic=output_topic, messages=[json.dumps(asset)]
                ):
                    logger.info("Requested: %s", asset['title'])
                    # notify ui that we have new message
                    app.storage.general["assetrequest_count"] = (
                        app.storage.general.get("assetrequest_count", 0) + 1
                    )
                    # update status in the broadcast list (just for UI feedback)
                    for a in app.storage.general["edge_broadcastreceived"]:
                        if asset['assetID'] == a['assetID']:
                            a["status"] = "requested"

                else:
                    logger.warning("Publish to %s failed for %s", f"{stream_path}:{output_topic}", asset)

        except Exception as error:
            logger.debug(error)

        # add delay to publishing
        sleep(ASSET_REQUEST_DELAY)
