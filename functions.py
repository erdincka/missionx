import logging
import os
import subprocess
import textwrap
from nicegui import app, run
import requests
from helpers import *

logger = logging.getLogger()

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, universal_newlines=True)
        if result.returncode == 0:
            logger.info("# %s ==> OK", cmd)
        else:
            logger.warning("# %s ==> %s", cmd, result.stdout)
            logger.debug(result.stderr)

        if result.stdout != "":
            logger.debug(result.stdout)
        if result.stderr != "":
            if "Failed to connect to IPv6" not in result.stderr:
                logger.debug(result)
            else:
                logger.debug("ignoring IPv6 errors...")

    except Exception as error:
        logger.warning(error)


async def prepare_core():
    app.storage.user["busy"] = True
    # HQ resources
    # await run.io_bound(run_command, f"maprcli audit data -cluster {os.environ['MAPR_CLUSTER']} -enabled true -retention 1")
    # await run.io_bound(run_command, f"maprcli config save -cluster {os.environ['MAPR_CLUSTER']} -values \"{{ 'mfs.enable.audit.as.stream':'1' }}\" ")
    await run.io_bound(run_command, f"maprcli volume create -name {HQ_VOLUME_NAME} -cluster {os.environ['MAPR_CLUSTER']} -path {HQ_VOLUME_PATH} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1")
    # await run.io_bound(run_command, f"maprcli volume audit -name {HQ_VOLUME_NAME} -cluster {os.environ['MAPR_CLUSTER']} -dataauditops '+create,+delete,+tablecreate,-all' -forceenable true -enabled true")
    # await run.io_bound(run_command, f"hadoop mfs -setaudit on {HQ_VOLUME_PATH}")
    await run.io_bound(run_command, f"maprcli table create -path {HQ_VOLUME_PATH}/{HQ_IMAGETABLE} -tabletype json")
    await run.io_bound(run_command, f"maprcli stream create -path {HQ_VOLUME_PATH}/{STREAM_LOCAL} -ttl 86400 -compression lz4 -produceperm p -consumeperm p -topicperm p")
    await run.io_bound(run_command, f"maprcli stream create -path {HQ_VOLUME_PATH}/{HQ_STREAM_REPLICATED} -ttl 86400 -compression lz4 -produceperm p -consumeperm p -topicperm p")
    await run.io_bound(run_command, f"maprcli volume create -name {HQ_MISSION_FILES} -cluster {os.environ['MAPR_CLUSTER']} -path {HQ_VOLUME_PATH}/{HQ_MISSION_FILES} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1")
    app.storage.user["busy"] = False

async def prepare_edge():
    app.storage.user["busy"] = True
    # Edge resources
    await run.io_bound(run_command, f"/opt/mapr/server/configure.sh -c -C {os.environ['EDGE_IP']}:7222 -N {os.environ['EDGE_CLUSTER']}")
    await run.io_bound(run_command, f"echo {os.environ['MAPR_PASS']} | maprlogin password -cluster {os.environ['EDGE_CLUSTER']} -user {os.environ['MAPR_USER']}")
    # await run.io_bound(run_command, f"maprcli audit data -cluster {os.environ['EDGE_CLUSTER']} -enabled true -retention 1")
    # await run.io_bound(run_command, f"maprcli config save -cluster {os.environ['EDGE_CLUSTER']} -values \"{{ 'mfs.enable.audit.as.stream':'1' }}\" ")
    await run.io_bound(run_command, f"maprcli volume create -name {EDGE_VOLUME_NAME} -cluster {os.environ['EDGE_CLUSTER']} -path {EDGE_VOLUME_PATH} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1")
    # await run.io_bound(run_command, f"maprcli volume audit -name {EDGE_VOLUME_NAME} -cluster {os.environ['EDGE_CLUSTER']} -dataauditops '+create,+delete,+tablecreate,-all' -forceenable true -enabled true")
    await run.io_bound(run_command, f"maprcli volume create -type mirror -name {EDGE_MISSION_FILES} -cluster {os.environ['EDGE_CLUSTER']} -path {EDGE_VOLUME_PATH}/{EDGE_MISSION_FILES} -source {HQ_MISSION_FILES}@{os.environ['MAPR_CLUSTER']} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1")
    app.storage.user["busy"] = False


def toggle_service(prop: str):
    app.storage.general["services"][prop] = not app.storage.general["services"].get(prop, False)


def toggle_debug(val: bool):
    if val:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

# return buttons to show and control service status
def service_status(service: tuple):
    name, icon = service
    prop = name.lower().replace(" ", "")

    if prop not in app.storage.general["services"]:
        app.storage.general["services"][prop] = False

    with ui.button(on_click=lambda n=prop: toggle_service(n)).tooltip(name).props("round").bind_visibility_from(
        app.storage.general["services"], prop
    ).classes("size-auto"):
        ui.icon(icon, size="md")
        ui.badge().bind_text_from(app.storage.general, f"{prop}_count").props('floating')

    with ui.button(color="none", on_click=lambda n=prop: toggle_service(n)).tooltip(name).props("round").bind_visibility_from(
        app.storage.general["services"], prop, backward=lambda x: not x
    ).classes("size-auto"):
        ui.icon(icon, size="md")
        ui.badge().bind_text_from(app.storage.general, f"{prop}_count").props('floating')


# return image to display on UI
def imageshow(host: str, src: str):
    # TODO: delete old images
    if src in app.storage.general and len(app.storage.general[src]) > 0:
        title, location = app.storage.general[src].pop(0)
        # TODO: use /mapr mount
        img_url = f"https://{os.environ['MAPR_USER']}:{os.environ['MAPR_PASS']}@{host}:8443/files{location}"
        with ui.card().tooltip(title).classes("h-48") as img:
            ui.image(img_url)
            ui.space()
            with ui.card_section().classes("align-text-bottom text-sm"):
                ui.label(textwrap.shorten(title, 24))

        return img


# create replica stream from HQ to Edge
def stream_replica_setup():
    source_stream_path = f"{HQ_VOLUME_PATH}/{HQ_STREAM_REPLICATED}"
    target_stream_path = f"{EDGE_VOLUME_PATH}/{EDGE_STREAM_REPLICATED}"

    REST_URL = f"https://{os.environ['MAPR_IP']}:8443/rest/stream/replica/autosetup?path={source_stream_path}&replica=/mapr/{os.environ['EDGE_CLUSTER']}{target_stream_path}&multimaster=true"
    AUTH_CREDENTIALS = (os.environ["MAPR_USER"], os.environ["MAPR_PASS"])

    response = requests.get(url=REST_URL, auth=AUTH_CREDENTIALS, verify=False)
    response.raise_for_status()

    if response:
        obj = response.json()
        logger.info("Stream replica: %s", obj)
    else:
        logger.warning("Cannot get stream replica")


# Start volume mirror from edge
async def mirror_volume():
    await run.io_bound(run_command, f"maprcli volume mirror start -cluster {os.environ['EDGE_CLUSTER']} -name {EDGE_MISSION_FILES}")

# Handle exceptions without UI failure
def gracefully_fail(exc: Exception):
    print("gracefully failing...")
    logger.debug("Exception: %s", exc)
    app.storage.user["busy"] = False
