import inspect
import logging
import os
import random
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
            logger.debug("# %s ==> OK", cmd)
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


def get_command_output(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, universal_newlines=True)
        if result.returncode == 0:
            logger.debug("# %s ==> OK", cmd)
        else:
            logger.warning("# %s ==> %s", cmd, result.stdout)
            logger.debug(result.stderr)

        if result.stdout != "":
            return result.stdout
        if result.stderr != "":
            if "Failed to connect to IPv6" not in result.stderr:
                logger.debug(result)
            else:
                logger.debug("ignoring IPv6 errors...")

    except Exception as error:
        logger.warning(error)


# def switch_cluster_to(dest: str):
#     """
#     Bring the selected cluster to the first line in /opt/mapr/conf/mapr-clusters.conf, so hadoop and streams commands will use that cluster.
#     This is a dirty hack to overcome the lack of cluster selection of certain APIs.
#     """

#     command= f"""selected=$(grep {dest} /opt/mapr/conf/mapr-clusters.conf); others=$(grep -v {dest} /opt/mapr/conf/mapr-clusters.conf); echo "$selected\n$others" > /opt/mapr/conf/mapr-clusters.conf"""
#     run_command(command)

async def prepare_core():
    app.storage.user["busy"] = True
    # HQ resources
    await run.io_bound(run_command, f"maprcli volume create -name {HQ_VOLUME_NAME} -cluster {os.environ['MAPR_CLUSTER']} -path {HQ_VOLUME_PATH} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1")
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
    await run.io_bound(run_command, f"maprcli volume create -name {EDGE_VOLUME_NAME} -cluster {os.environ['EDGE_CLUSTER']} -path {EDGE_VOLUME_PATH} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1")
    await run.io_bound(run_command, f"maprcli volume create -type mirror -name {EDGE_MISSION_FILES} -cluster {os.environ['EDGE_CLUSTER']} -path {EDGE_VOLUME_PATH}/{EDGE_MISSION_FILES} -source {HQ_MISSION_FILES}@{os.environ['MAPR_CLUSTER']} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1")
    app.storage.user["busy"] = False


def toggle_service(prop: str):
    app.storage.general["services"][prop] = not app.storage.general["services"].get(prop, False)


def toggle_debug(val: bool):
    if val:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


def service_status(service: tuple):
    name, _ = service
    prop = name.lower().replace(" ", "")

    if prop not in app.storage.general["services"]:
        app.storage.general["services"][prop] = False

    with ui.item(on_click=lambda n=prop: toggle_service(n)).bind_enabled_from(app.storage.general["services"], prop).classes("text-xs m-1 p-1 border"):
        with ui.item_section():
            ui.item_label(name).classes("no-wrap")
        with ui.item_section().props('side'):
            ui.label().bind_text_from(app.storage.general["services"], prop, backward=lambda x: "Started" if x else "Stopped")


def service_counter(service: tuple):
    name, _ = service
    prop = name.lower().replace(" ", "")

    with ui.item().classes("text-xs m-1 p-1 border"):
        with ui.item_section():
            ui.item_label(f"{name.split(' ')[1]} processed").classes("no-wrap")
        with ui.item_section().props('side'):
            ui.badge().bind_text_from(app.storage.general, f"{prop}_count")


def service_settings(service: tuple):
    name, _ = service
    prop = name.lower().replace(" ", "")

    with ui.item().classes("text-xs m-1 p-1 border"):
        with ui.item_section():
            ui.item_label(f"{name.split(' ')[1]} delay (s):").classes("no-wrap")
            slider = ui.slider(min=2, max=10).bind_value(app.storage.general, f"{prop}_delay")
        with ui.item_section().props('side'):
            ui.label().bind_text_from(slider, 'value')


# return image to display on UI
def dashboard_tiles(host: str, source: str):
    """
    host: 
    source: string of key in app.storage.general, hq_dashboard | edge_dashboard, contains: list[DashboardTile]
    """

    BGCOLORS = {
        "NASA Feed Service": "bg-sky-300",
        "Image Download Service": "bg-red-300",
        "Asset Broadcast Service": "bg-green-300",
        "Asset Response Service": "bg-orange-300",
        "Upstream Comm Service": "bg-amber-300",
        "Broadcast Listener Service": "bg-emerald-300",
        "Asset Request Service": "bg-lime-300",
        "Asset Viewer Service": "bg-stone-300",
    }

    if source in app.storage.general and len(app.storage.general[source]) > 0:
        service, title, description, imageUrl = app.storage.general.get(source, []).pop()

        logger.debug("Process tile for service: %s, title: %s, description: %s, and imageurl: %s", service, title, description, imageUrl)

        if service == "Asset Viewer Service" or service == "Image Download Service":
            with ui.card().classes("h-80").props("bordered").tight() as img:
                with ui.card_section().classes(f"w-full text-sm {BGCOLORS[service]}"):
                    ui.label(service)
                # TODO: use /mapr mount
                ui.image(f"https://{os.environ['MAPR_USER']}:{os.environ['MAPR_PASS']}@{host}:8443/files{imageUrl}")
                ui.space()
                with ui.card_section():
                    ui.label(textwrap.shorten(title, 32)).classes("text-sm")

            img.on("click", lambda h=host,t=title,d=description,u=imageUrl: show_image(h,t,d,u))
            if service == "Image Download Service": # auto remove tiles if not asset viewer
                ui.timer(app.storage.general.get("tile_remove", 20), img.delete, once=True)

        else:
            with ui.card().classes("h-80").props("bordered") as img:
                with ui.card_section().classes(f"w-full text-sm {BGCOLORS[service]}"):
                    ui.label(service)
                with ui.card_section().classes("text-sm"):
                    ui.label(textwrap.shorten(description, 64))
                ui.space()
                with ui.card_section().classes("text-sm"):
                    ui.label(textwrap.shorten(title, 32))

            ui.timer(app.storage.general.get("tile_remove", 20), img.delete, once=True)

        return img


# create replica stream from HQ to Edge
async def stream_replica_setup():
    source_stream_path = f"{HQ_VOLUME_PATH}/{HQ_STREAM_REPLICATED}"
    target_stream_path = f"{EDGE_VOLUME_PATH}/{EDGE_STREAM_REPLICATED}"

    logger.debug("Starting replication to %s", target_stream_path)
    REST_URL = f"https://{os.environ['MAPR_IP']}:8443/rest/stream/replica/autosetup?path={source_stream_path}&replica=/mapr/{os.environ['EDGE_CLUSTER']}{target_stream_path}&multimaster=true"
    AUTH_CREDENTIALS = (os.environ["MAPR_USER"], os.environ["MAPR_PASS"])

    logger.debug("REST_URL: %s", REST_URL)
    try:
        response = await run.io_bound(requests.get, url=REST_URL, auth=AUTH_CREDENTIALS, verify=False)
        response.raise_for_status()

    except Exception as error:
        logger.warning(error)

    if response:
        obj = response.json()
        logger.info("Stream replica: %s", obj)
    else:
        logger.warning("Cannot get stream replica")


# Start volume mirror from edge
async def mirror_volume():
    await run.io_bound(run_command, f"maprcli volume mirror start -cluster {os.environ['EDGE_CLUSTER']} -name {EDGE_MISSION_FILES}")


async def toggle_replication():
    """ FIX: not working
    """
    toggle_action = "resume" if app.storage.general["stream_replication"] == "PAUSED" else "pause"
    AUTH_CREDENTIALS = (os.environ["MAPR_USER"], os.environ["MAPR_PASS"])
    REST_URL = f"https://{os.environ['EDGE_IP']}:8443/rest/stream/replica/{toggle_action}?path={EDGE_VOLUME_PATH}/{EDGE_STREAM_REPLICATED}&replica={HQ_VOLUME_PATH}/{HQ_STREAM_REPLICATED}"
 
    try:
        response = requests.get(url=REST_URL, auth=AUTH_CREDENTIALS, verify=False)
        response.raise_for_status()

        logger.debug(response.text)

    except Exception as error:
        logger.warning(error)

# Handle exceptions without UI failure
def gracefully_fail(exc: Exception):
    print("gracefully failing...")
    logger.exception(exc)
    app.storage.user["busy"] = False


def show_code(func):
    with ui.dialog().props("full-width") as show, ui.card().classes("grow"):
        ui.code(inspect.getsource(func)).classes("w-full text-wrap")

    show.on("close", show.clear)
    show.open()


def show_image(host: str, title: str, description: str, imageUrl: str):
    with ui.dialog().props("full-width") as show, ui.card().classes("grow"):
        ui.label(title).classes("w-full")
        ui.space()
        ui.label(description).classes("w-full text-wrap")
        ui.space()
        ui.image(f"https://{os.environ['MAPR_USER']}:{os.environ['MAPR_PASS']}@{host}:8443/files{imageUrl}")

    show.on("close", show.clear)
    show.open()


