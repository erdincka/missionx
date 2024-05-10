import json
import os
import socket

import requests

from functions import get_command_output
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

    logger.debug("started...")

    while True:
        # skip if service is disabled by user
        if not app.storage.general["services"].get("auditlistener", False):
            logger.debug("disabled")
            break

        logger.debug("running...")

        host_fqdn = socket.getfqdn(os.environ["EDGE_IP"])
        
        for msg in consume(
            cluster=os.environ["EDGE_CLUSTER"],
            stream=audit_stream_path,
            topic=f"{os.environ['EDGE_CLUSTER']}_db_{host_fqdn}",
        ):
            record = json.loads(msg)
            logger.debug("Received: %s", record)

            if (
                record["operation"] == "DB_UPSTREAMADD"
                and record["upstreamPath"] == upstreamSource
            ):
                app.storage.general["stream_replication_established"] = True
                logger.info("REPLICATION ESTABLISHED")
                # app.storage.general["services"]["upstreamcomm"] = True

            else:
                logger.debug("Uninterested operation %s", record['operation'])

            app.storage.general["auditlistener_count"] = (
                app.storage.general.get("auditlistener_count", 0) + 1
            )

        # add delay to publishing
        sleep(app.storage.general.get("auditlistener_delay", 1.0))


@fire_and_forget
def upstream_comm_service():
    app.storage.general["services"]["upstreamcomm"] = True

    logger.debug("started...")

    while True:
        # skip if service is disabled by user
        if not app.storage.general["services"].get("upstreamcomm", False):
            logger.debug("disabled")
            break

        logger.debug("running...")

        AUTH_CREDENTIALS = (os.environ["MAPR_USER"], os.environ["MAPR_PASS"])

        # check volume replication
        REST_URL = f"https://{os.environ['EDGE_IP']}:8443/rest/volume/info?name={EDGE_MISSION_FILES}"

        try:
            vol_response = requests.get(url=REST_URL, auth=AUTH_CREDENTIALS, verify=False)
            vol_response.raise_for_status()

        except Exception as error:
            logger.debug(error)

        if vol_response:
            result = vol_response.json()
            logger.debug("volume info: %s", result)
            lastUpdatedSeconds = int((result["timestamp"] - result["data"][0]["lastSuccessfulMirrorTime"]) / 1000)
            app.storage.general["volume_replication"] = f"{lastUpdatedSeconds}s ago"

        else:
            logger.warning("Cannot get volume info")

        # check stream replication
        REST_URL = f"https://{os.environ['EDGE_IP']}:8443/rest/stream/replica/list?path={EDGE_VOLUME_PATH}/{EDGE_STREAM_REPLICATED}"

        try:
            stream_response = requests.get(url=REST_URL, auth=AUTH_CREDENTIALS, verify=False)
            stream_response.raise_for_status()

        except Exception as error:
            logger.debug(error)

        if stream_response:
            result = stream_response.json()
            logger.debug("stream info: %s", result)

            if result['status'] == "ERROR":
                app.storage.general["stream_replication"] = "ERROR"
                # sanity check
                for error in result['errors']:
                    if f"{EDGE_STREAM_REPLICATED} is not a valid stream" in error["desc"]:
                        app.storage.general["stream_replication"] = "NO STREAM"

            elif result['status'] == "OK":
                app.storage.general["stream_replication"] = "OK"
                # if result["data"][0].get('replicaState', "") == "REPLICA_STATE_REPLICATING":
                #     app.storage.general["stream_replication"] = "REPLICATING"
                if result["data"][0].get("paused", False) == True:
                    # sleep(0.1)
                    app.storage.general["stream_replication"] = "PAUSED"
                if result["data"][0].get("isUptodate", False) == True:
                    # sleep(0.1)
                    app.storage.general["stream_replication"] = "IN SYNC"

            # update dashboard with a tile
            app.storage.general["dashboard_edge"].append(
                tuple(["Upstream Comm Service", f"Stream replication: {EDGE_STREAM_REPLICATED}", app.storage.general['stream_replication'], None])
            )

        else:
            logger.warning("Cannot get stream replica")

        # increase counter for each processing
        app.storage.general["upstreamcomm_count"] = (
            app.storage.general.get("upstreamcomm_count", 0) + 1
        )
        # add delay to publishing
        sleep(app.storage.general.get("upstreamcomm_delay", 1.0))


@fire_and_forget
def broadcast_listener_service():
    """
    Process messages in ASSET_BROADCAST topic
    """

    stream_path = f"/mapr/{os.environ['EDGE_CLUSTER']}/{EDGE_VOLUME_PATH}/{EDGE_STREAM_REPLICATED}"

    input_topic = TOPIC_ASSET_BROADCAST

    app.storage.general["services"]["broadcastlistener"] = True
    app.storage.general["broadcastreceived"] = []

    logger.debug("started...")

    while True:
        # skip if service is disabled by user
        if not app.storage.general["services"].get("broadcastlistener", False):
            logger.debug("disabled")
            break

        logger.debug("running...")

        try:
            for msg in consume(cluster=os.environ["EDGE_CLUSTER"], stream=stream_path, topic=input_topic):
                record = json.loads(msg)
                logger.debug("Received: %s", record)

                record['status'] = "broadcasted"
                app.storage.general["broadcastreceived"].append(record)

                app.storage.general["broadcastlistener_count"] = (
                    app.storage.general.get("broadcastlistener_count", 0) + 1
                )
                # update dashboard with a tile
                app.storage.general["dashboard_edge"].append(
                    tuple(["Broadcast Listener Service", f"Broadcast Received: {record['title']}", record["description"], None])
                )

        except Exception as error:
            logger.debug(error)

        # add delay to publishing
        sleep(app.storage.general.get("broadcastlistener_delay", 1.0))


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
            logger.debug("disabled")
            break

        logger.debug("running...")

        awaiting_processing = [a for a in app.storage.general.get("broadcastreceived", []) if a["status"] == "requesting..."]

        try:
            while len(awaiting_processing) > 0:
                asset = awaiting_processing.pop()
                # Publish to request topic on the replicated stream
                if produce(cluster=os.environ['EDGE_CLUSTER'], stream=stream_path, topic=output_topic, record=json.dumps(asset)
                ):
                    logger.info("Requested: %s", asset['title'])
                    # notify ui that we have new message
                    app.storage.general["assetrequest_count"] = (
                        app.storage.general.get("assetrequest_count", 0) + 1
                    )
                    # update status in the broadcast list
                    for a in app.storage.general["broadcastreceived"]:
                        if asset['assetID'] == a['assetID']:
                            a["status"] = "requested"

                    # update dashboard with a tile
                    app.storage.general["dashboard_edge"].append(
                        tuple(["Asset Request Service", f"Request sent: {asset['assetID']}", asset["title"], None])
                    )

                else:
                    logger.warning("Publish to %s failed for %s", f"{stream_path}:{output_topic}", asset)

        except Exception as error:
            logger.debug(error)

        # add delay to publishing
        sleep(app.storage.general.get("assetrequest_delay", 1.0))


# put the request into queue
def make_asset_request(asset: dict):
    # find and update the requested asset in the broadcast list
    for a in app.storage.general.get("broadcastreceived", []):
        if a['assetID'] == asset['assetID']:
            a["status"] = "requesting..."


@fire_and_forget
def asset_viewer_service():
    app.storage.general["services"]["assetviewer"] = True

    logger.debug("started...")

    while True:
        # skip if service is disabled by user
        if not app.storage.general["services"].get("assetviewer", False):
            logger.debug("disabled")
            break

        logger.debug("running...")

        try:
            # FIX: workaround to select the correct cluster
            # switch_cluster_to(os.environ['EDGE_CLUSTER'])
            lines = get_command_output(f"hadoop fs -ls {EDGE_VOLUME_PATH}/{EDGE_MISSION_FILES} | grep {EDGE_VOLUME_PATH}/{EDGE_MISSION_FILES} | awk '{{ print $8 }}'")
            if not lines: continue

            files = lines.split("\n")
            # logger.debug("Files in volume: %s", files)

            for file in files:
                # skip empty line
                if file == "": continue

                # if file is in requested assets
                for asset in [a for a in app.storage.general.get("broadcastreceived", []) if a["status"] == "requested" and a["filename"] in file]:
                    logger.debug("Found file for: %s", asset)
                    asset["status"] = "received"
                    # notify ui that we processed a request
                    app.storage.general["assetviewer_count"] = app.storage.general.get("assetviewer_count", 0) + 1
                    # update dashboard with a tile
                    app.storage.general["dashboard_edge"].append(
                        tuple(["Asset Viewer Service", f"Received: {asset['title']}", None, file])
                    )

        except Exception as error:
            logger.debug(error)

        # add delay to publishing
        sleep(app.storage.general.get("assetviewer_delay", 1.0))