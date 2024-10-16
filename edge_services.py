import datetime
import json
import socket

import requests

from sites import *
from common import *
from files import getfile
from functions import get_volume_name
from helpers import *
from nicegui import app

from streams import consume, produce

logger = logging.getLogger(__name__)

services = EdgeSite['services']
tiles = EdgeSite['tiles']
assets = EdgeSite['assets']

def audit_listener_service(host: str, clustername: str):
    """
    Listens the auditlogstream to see if upstream replication is established.
    """

    service = services["auditlistener"]

    audit_stream_path = "/var/mapr/auditstream/auditlogstream"
    upstreamSource = HQ_STREAM_REPLICATED

    service["active"] = True

    # skip if service is disabled by user
    if not service["active"]:
        # logger.debug("is disabled")
        return

    host_fqdn = socket.getfqdn(host)
    # host_ipv4 = socket.gethostbyname(host_fqdn)

    # logger.debug(f"FQDN: {host_fqdn}")
    # logger.debug(f"IPv4: {host_ipv4}")

    for msg in consume(
        stream=audit_stream_path,
        topic=f"{clustername}_db_{host_fqdn}",
    ):
        record = json.loads(msg)
        # logger.debug("Received: %s", record)

        if (
            record["operation"] == "DB_UPSTREAMADD"
            and record["upstreamPath"] == upstreamSource
        ):
            app.storage.general["stream_replication"] = "ESTABLISHED"
            logger.info("REPLICATION ESTABLISHED")
            # service["upstreamcomm"] = True

        else:
            logger.debug("Uninterested operation %s", record['operation'])

        # update UI
        service["count"] += 1



def upstream_comm_service(host: str, user: str, password: str, messages: list):

    service = services["upstreamcomm"]

    service["active"] = True

    # skip if service is disabled by user
    if not service["active"]:
        # logger.debug("is disabled")
        return

    # check volume replication
    URL = f"https://{host}:8443/rest/volume/info?name={get_volume_name(EDGE_MISSION_FILES)}"

    try:
        vol_response = requests.get(url=URL, auth=(user, password), verify=False)
        # vol_response.raise_for_status()

    except Exception as error:
        logger.debug(error)

    if vol_response:
        result = vol_response.json()
        # logger.debug("volume info: %s", result)
        try:
            lastUpdatedSeconds = int((result.get("timestamp", 0) - result.get("data", [])[0].get("lastSuccessfulMirrorTime",0)) / 1000)
        except: # if failed to get expected data
            app.storage.general["volume_replication"] = "ERROR"

        app.storage.general["volume_replication"] = f"{str(datetime.timedelta(seconds=lastUpdatedSeconds))} ago"

    else:
        logger.warning("Cannot get volume info")

    # check stream replication
    URL = f"https://{host}:8443/rest/stream/replica/list?path={EDGE_STREAM_REPLICATED}&refreshnow=true"
    try:
        stream_response = requests.get(url=URL, auth=(user, password), verify=False)
        # stream_response.raise_for_status()

    except Exception as error:
        logger.debug(error)

    if stream_response:
        result = stream_response.json()
        # logger.debug("stream info: %s", result)

        if result['status'] == "ERROR":
            app.storage.general["stream_replication"] = "ERROR"
            # sanity check
            for error in result['errors']:
                if f"{EDGE_STREAM_REPLICATED} is not a valid stream" in error["desc"]:
                    app.storage.general["stream_replication"] = "NO STREAM"

        elif result['status'] == "OK":
            resultData = result.get("data", {}).pop()
            # logger.debug("%s target stream: %s", EDGE_STREAM_REPLICATED, resultData)

            # skip updates if same with previous state
            if resultData.get("replicaState", "ERROR") == app.storage.general["stream_replication"]:
                return
            else:
                # replicaState = resultData['replicaState'].replace("REPLICA_STATE_", "")
                replicaState = "UNKNOWN" # default state
                if resultData["paused"]:
                    replicaState = "PAUSED"
                elif resultData["isUptodate"]:
                    replicaState = "SYNCED"

                app.storage.general["stream_replication"] = replicaState
                # increase counter for each processing
                service["count"] += 1
                # update dashboard with a tile -- confusing for user, instead, we update replication status only
                # messages.append(
                #     tuple(["Upstream Comm Service", resultData['cluster'], replicaState, None])
                # )

    else:
        logger.warning("Cannot get stream replica")


def broadcast_listener_service(clustername: str):
    """
    Process messages in ASSET_BROADCAST topic
    """

    service = services["broadcastlistener"]

    stream_path = f"/mapr/{clustername}{EDGE_STREAM_REPLICATED}"

    input_topic = TOPIC_ASSET_BROADCAST

    service["active"] = True

    # skip if service is disabled by user
    if not service["active"]:
        # logger.debug("is disabled")
        return

    try:
        for msg in consume(stream=stream_path, topic=input_topic):
            record = json.loads(msg)
            logger.debug("Broadcast Received: %s", record['title'])

            record['status'] = "published"
            # update dashboard with the tiles
            assets.append(record)

            service["count"] += 1
            # update broadcast received
            tiles.append(
                tuple(["Broadcast Listener Service", f"Broadcast Received: {record['title']}", record["description"], None])
            )
            # logger.debug(f"Dashboard updated with messages: {json.dumps(messages)}")
            # logger.debug(f"Dashboard updated with tiles: {json.dumps(dashboard.tiles)}")

    except Exception as error:
        logger.debug(error)


def asset_request_service(clustername: str, assets: list):
    """
    Request assets by reading from queue and putting them to the replicated stream on ASSET_REQUEST topic
    """

    service = services["assetrequest"]

    stream_path = f"/mapr/{clustername}{EDGE_STREAM_REPLICATED}"

    output_topic = TOPIC_ASSET_REQUEST

    service["active"] = True

    try:
        for asset in [a for a in assets if a["status"] == "requesting..."]:
            # Publish to request topic on the replicated stream
            if produce(stream=stream_path, topic=output_topic, record=json.dumps(asset)
            ):
                logger.info("Requested: %s", asset['title'])
                asset["status"] = "requested"
                service["count"] += 1

            else:
                logger.warning("Publish to %s failed for %s", f"{stream_path}:{output_topic}", asset)

    except Exception as error:
        logger.debug(error)


# put the request into queue
def make_asset_request(assetID: str, tiles: list):
    # find and update the requested asset in the broadcast list
    logger.debug(f"Requesting asset: {assetID}")
    for a in tiles:
        if a['assetID'] == assetID:
            a["status"] = "requesting..."


def asset_viewer_service(host: str, user: str, password: str):
    service = services["assetviewer"]

    service["active"] = True

    for asset in [a for a in assets if a["status"] == "requested"]:
        # logger.debug("Search for asset: %s", asset)

        filepath = f"{EDGE_MISSION_FILES}/{asset['filename']}"

        response = getfile(
            host=host,
            user=user,
            password=password,
            filepath=filepath
        )

        if response and response.status_code == 200:
            # logger.debug("Found asset file: %s", asset['filename'])
            asset["status"] = "received"
            # notify ui that we processed a request
            service["count"] += 1
            # update dashboard with a tile
            tiles.append(
                tuple(["Asset Viewer Service", asset['title'], asset['description'], filepath])
            )
        else:
            logger.debug("File not found for asset: %s", asset["title"])
