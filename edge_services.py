import json
import os
import socket

from helpers import *
from nicegui import app
from time import sleep

# from sparking import spark_kafka_consumer
from streams import consume

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

        for msg in consume(
            stream=audit_stream_path,
            topic=f"{os.environ['EDGE_CLUSTER']}_db_{socket.getfqdn(os.environ['EDGE_IP'])}",
        ):
            record = json.loads(msg)
            logger.debug("Received: %s", record)

            if (
                msg["operation"] == "DB_UPSTREAMADD"
                and msg["upstreamPath"] == upstreamSource
            ):
                app.storage.general["stream_replication_established"] = True
                logger.info("REPLICATION ESTABLISHED")
                # if replication is on, subscribe to messages from upstream
                logger.info("TODO: read replicated messages from edge")
                # app.storage.general["services"]["upstreamcomm"] = True
                # upstream_comm_service()

            app.storage.general["auditlistener_count"] = (
                app.storage.general.get("auditlistener_count", 0) + 1
            )

        # add delay to publishing
        sleep(AUDIT_LISTENER_DELAY)


@fire_and_forget
def broadcast_listener_service():
    """
    Process messages in ASSET_BROADCAST topic using pyspark
    """

    stream_path = f"/mapr/{os.environ['EDGE_CLUSTER']}/{EDGE_VOLUME_PATH}/{EDGE_STREAM_REPLICATED}"

    input_topic = TOPIC_ASSET_BROADCAST

    app.storage.general["services"]["broadcastlistener"] = True

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

                app.storage.general.get("edge_broadcastreceived", []).append(record)

                app.storage.general["broadcastlistener_count"] = (
                    app.storage.general.get("broadcastlistener_count", 0) + 1
                )
        except Exception as error:
            logger.debug(error)

        # add delay to publishing
        sleep(BROADCAST_LISTENER_DELAY)
