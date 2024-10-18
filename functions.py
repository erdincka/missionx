import asyncio
import inspect
import logging
import os
import textwrap
import urllib.parse
import httpx
from nicegui import app, run
import requests
import urllib
from common import *
from helpers import *
from sites import HQSite, EdgeSite

logger = logging.getLogger(__name__)

async def run_command_with_dialog(command: str) -> None:
    """
    Run a command in the background and display the output in the pre-created dialog.
    """

    with ui.dialog().props("full-width") as dialog, ui.card().classes("grow relative"):
        ui.button(icon="close", on_click=dialog.close).props("flat round dense").classes("absolute right-2 top-2")
        ui.label(f"Running: {textwrap.shorten(command, width=80)}").classes("text-bold")
        result = ui.log().classes("w-full mt-2").style("white-space: pre-wrap")

    dialog.on("close", lambda d=dialog: d.delete())
    dialog.open()

    result.content = ''

    async for out in run_command(command): result.push(out)


async def run_command(command: str):
    """
    Run a command in the background and return the output.
    """

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    # NOTE we need to read the output in chunks, otherwise the process will block
    while True:
        new = await process.stdout.read(4096)
        if not new:
            break
        yield new.decode()

    yield "Done."
    logger.debug(f"Finished: {command}")


def get_cluster_name(key: str):
    """
    Get the name of the cluster from the settings.
    """

    if key in app.storage.user.keys() and "name" in app.storage.user[key].keys():
        return app.storage.user[key]["name"]
    else:
        return None


def get_volume_name(volume: str) -> str:
    """
    Get the name of a volume from its full path.
    """
    return os.path.basename(os.path.normpath(volume))
    # or return volume.split('/')[-1]


async def create_volumes(host: str, volumes: list):
    """
    Create an app folder and create volumes in it
    """

    auth = (app.storage.user["MAPR_USER"], app.storage.user["MAPR_PASS"])

    app.storage.user['busy'] = True

    for vol in volumes:
        volname = vol.split("/")[-1]

        URL = f"https://{host}:8443/rest/volume/create?name={volname}&path={vol}&replication=1&minreplication=1&nsreplication=1&nsminreplication=1"

        # logger.debug("REST call to: %s", URL)

        try:
            async with httpx.AsyncClient(verify=False, timeout=10) as client:
                response = await client.post(URL, auth=auth)

                if response is None or response.status_code != 200:
                    logger.warning("REST failed for create volume: %s on %s", vol, host)
                    logger.warning("Response: %s", response.text)

                else:
                    res = response.json()
                    if res['status'] == "OK":
                        ui.notify(f"{res['messages'][0]}", type='positive')
                    elif res['status'] == "ERROR":
                        ui.notify(f"{res['errors'][0]['desc']}", type='warning')
                        logger.warning("REST failed for create volume: %s on %s: %s", vol, host, res['errors'][0]['desc'])

        except Exception as error:
            logger.warning("Failed to connect %s!", URL)
            ui.notify(f"Failed to connect to REST.", type='negative')
            logger.debug(error)
            app.storage.user['busy'] = False
            return False

    app.storage.user['busy'] = False
    return True


async def create_mirror_volume(hqclustername: str, edgehost: str, source: str, dest: str) -> bool:
    """
    Create a volume on the edge cluster to replicate a volume on the HQ cluster.
    """

    auth = (app.storage.user["MAPR_USER"], app.storage.user["MAPR_PASS"])

    app.storage.user['busy'] = True

    volname = dest.split("/")[-1]

    URL = f"https://{edgehost}:8443/rest/volume/create?name={volname}&path={dest}&type=mirror&source={get_volume_name(source)}@{hqclustername}"

    # logger.debug("REST call to: %s", URL)

    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.post(URL, auth=auth)

            if response is None or response.status_code != 200:
                logger.warning("REST failed for create mirror volume %s on %s", dest, edgehost)
                logger.warning("Response: %s", response.text)

            else:
                res = response.json()
                if res['status'] == "OK":
                    ui.notify(f"{res['messages'][0]}", type='positive')
                elif res['status'] == "ERROR":
                    ui.notify(f"{res}", type='warning')
                    logger.warning("REST failed to create volume for URL %s: %s", URL, res)

    except Exception as error:
        logger.warning("Failed to connect %s", URL)
        ui.notify(f"Failed to connect to REST endpoint for mirror volume creation.", type='negative')
        logger.error(error, exc_info=True)
        app.storage.user['busy'] = False
        return False

    app.storage.user['busy'] = False
    return True


async def create_tables(host: str, tables: list):
    auth = (app.storage.user["MAPR_USER"], app.storage.user["MAPR_PASS"])

    app.storage.user['busy'] = True
    for table in tables:
        try:
            # Create table
            async with httpx.AsyncClient(verify=False) as client:
                URL = f"https://{host}:8443/rest/table/create?path={urllib.parse.quote_plus(table)}&tabletype=json&defaultreadperm=p&defaultwriteperm=p&defaulttraverseperm=p&defaultunmaskedreadperm=p"
                response = await client.post(
                    url=URL,
                    auth=auth
                )

                # logger.debug(response.json())

                if response is None or response.status_code != 200:
                    # possibly not an issue if table already exists
                    logger.warning("REST failed for create table: %s on %s", table, host)
                    logger.warning("Response: %s", response.text)

                else:
                    res = response.json()
                    if res['status'] == "OK":
                        ui.notify(f"Table \"{table}\" created", type='positive')
                    elif res['status'] == "ERROR":
                        ui.notify(f"Table: \"{table}\": {res['errors'][0]['desc']}", type='warning')
                        logger.warning("Error creating table %s: %s", table, res['errors'][0]['desc'])

        except Exception as error:
            logger.warning("Failed to connect %s: %s", URL, error)
            ui.notify(f"Failed to connect to REST: {type(error)}", type='negative')
            app.storage.user['busy'] = False
            return False

    app.storage.user['busy'] = False
    return True


async def create_streams(host: str, streams: list):
    auth = (app.storage.user["MAPR_USER"], app.storage.user["MAPR_PASS"])

    for stream in streams:
        URL = f"https://{host}:8443/rest/stream/create?path={stream}&ttl=38400&compression=lz4&produceperm=p&consumeperm=p&topicperm=p"

        app.storage.user['busy'] = True
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(URL, auth=auth)

                if response is None or response.status_code != 200:
                    # possibly not an issue if stream already exists
                    logger.warning("REST failed for create stream: %s on %s", stream, host)
                    logger.warning("Response: %s", response.text)

                else:
                    res = response.json()
                    if res['status'] == "OK":
                        ui.notify(f"Stream \"{stream}\" created", type='positive')
                    elif res['status'] == "ERROR":
                        ui.notify(f"Stream: \"{stream}\": {res['errors'][0]['desc']}", type='warning')

        except Exception as error:
            logger.warning("Failed to connect %s: %s", URL, type(error))
            ui.notify(f"Failed to connect to REST: {error}", type='negative')
            app.storage.user['busy'] = False
            return False

    app.storage.user['busy'] = False
    return True


async def delete_volumes():
    """
    Delete volumes for both clusters, removing the streams and tables in them.
    """

    app.storage.user['busy'] = True
    auth = (app.storage.user["MAPR_USER"], app.storage.user["MAPR_PASS"])

    # Remove Edge volumes first
    host = app.storage.user[EDGE]["ip"]
    volname = get_volume_name(EDGE_VOLUME_PATH)
    replicated_volname = get_volume_name(EDGE_MISSION_FILES)
    for volume in [replicated_volname, volname]:
        URL = f"https://{host}:8443/rest/volume/remove?name={volume}&force=true"
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(URL, auth=auth)

            if response is None or response.status_code != 200:
                logger.warning("REST failed for delete volume: %s", volume)
                logger.warning("Response: %s", response.text)
            else:
                res = response.json()
                if res['status'] == "OK":
                    ui.notify(f"Volume '{volume}' deleted", type='warning')
                elif res['status'] == "ERROR":
                    ui.notify(f"{volume}: {res['errors'][0]['desc']}", type='warning')
                    logger.warning("Error response for delete volume %s: %s", volume, res['errors'][0]['desc'])

    # Remove HQ volumes
    host = app.storage.user[HQ]["ip"]
    volname = get_volume_name(HQ_VOLUME_PATH)
    replicated_volname = get_volume_name(HQ_MISSION_FILES)
    for volume in [replicated_volname, volname]:

        URL = f"https://{host}:8443/rest/volume/remove?name={volume}&force=true"
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(URL, auth=auth)

            if response is None or response.status_code != 200:
                logger.warning("REST failed for delete volume: %s", volume)
                logger.warning("Response: %s", response.text)

            else:
                res = response.json()
                if res['status'] == "OK":
                    ui.notify(f"Volume '{volume}' deleted", type='warning')
                elif res['status'] == "ERROR":
                    ui.notify(f"{volume}: {res['errors'][0]['desc']}", type='warning')
                    logger.warning("Error response for delete volume %s: %s", volume, res['errors'][0]['desc'])


    app.storage.user['busy'] = False


def prepare_core():
    # These commands (or rather their REST API equivalents) are already run with the initial cluster configuration dialog. You can use them as reference.
    # HQ resources
    return f"""
    echo "maprcli volume create -cluster {HQSite['clusterName']} -name {get_volume_name(HQ_VOLUME_PATH)} -path {HQ_VOLUME_PATH} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1"
    echo "maprcli table create -path /mapr/{HQSite['clusterName']}{HQ_IMAGETABLE} -tabletype json"
    echo "maprcli stream create -path /mapr/{HQSite['clusterName']}{HQ_VOLUME_PATH}/{STREAM_PIPELINE} -ttl 86400 -compression lz4 -produceperm p -consumeperm p -topicperm p"
    echo "maprcli stream create -path /mapr/{HQSite['clusterName']}{HQ_STREAM_REPLICATED} -ttl 86400 -compression lz4 -produceperm p -consumeperm p -topicperm p"
    echo "maprcli volume create -cluster {HQSite['clusterName']} -name {get_volume_name(HQ_MISSION_FILES)} -path {HQ_MISSION_FILES} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1"
    """


def prepare_edge():
    # These commands (or rather their REST API equivalents) are already run with the initial cluster configuration dialog. You can use them as reference.
    # Edge resources
    # 1. Connect to the edge cluster from the client machine.
    # 2. Set authorisation ticket for the edge cluster
    # 3. Create a mirror volume on the edge cluster.
    return f"""
    echo "/opt/mapr/server/configure.sh -c -C {app.storage.user['EDGE_HOST']}:7222 -N {EdgeSite['clusterName']} -secure"
    echo "echo {app.storage.user['MAPR_PASS']} | maprlogin password -cluster {EdgeSite['clusterName']} -user {app.storage.user['MAPR_USER']}"
    echo "maprcli volume create -type mirror -name {get_volume_name(EDGE_MISSION_FILES)} -cluster {EdgeSite['clusterName']} -path {EDGE_MISSION_FILES} -source {HQ_MISSION_FILES}@{HQSite['clusterName']} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1"
    """


# def service_status(service: tuple):
#     # Add if services are not set up yet
#     name, _ = service
#     prop = name.lower().replace(" ", "")

#     if prop not in app.storage.general["services"]:
#         app.storage.general["services"][prop] = False

#     with ui.item(on_click=lambda n=prop: toggle_service(n)).classes("text-xs"): #.bind_enabled_from(app.storage.general["services"], prop)
#         with ui.item_section():
#             ui.item_label(name).classes("no-wrap")
#         with ui.item_section().props('side'):
#             ui.icon("fa-solid fa-circle-question fa-xs").bind_name_from(app.storage.general["services"], prop, backward=lambda x: "fa-solid fa-circle-check fa-xs" if x else "fa-solid fa-circle-xmark fa-xs")


def service_counter(service: tuple):
    _, svc = service

    with ui.item().classes("text-xs m-1 p-1 border"):
        with ui.item_section():
            ui.item_label(f"{svc.name.split(' ')[1]} processed").classes("no-wrap")
        with ui.item_section().props('side'):
            ui.badge().bind_text_from(svc, "count")


def service_settings(service: tuple):
    _, svc = service

    with ui.item().classes("text-xs m-1 p-1 border"):
        with ui.item_section():
            ui.item_label(f"{svc.name.split(' ')[1]} delay (s):").classes("no-wrap")
            slider = ui.slider(min=2, max=10).bind_value(svc, "delay")
        with ui.item_section().props('side'):
            ui.label().bind_text_from(slider, 'value')


# create replica stream from HQ to Edge
async def stream_replica_setup(hqhost: str, user: str, password: str):
    source_stream_path = f"/mapr/{HQSite['clusterName']}{HQ_STREAM_REPLICATED}"
    target_stream_path = f"/mapr/{EdgeSite['clusterName']}{EDGE_STREAM_REPLICATED}"

    logger.debug("Starting replication to %s", target_stream_path)
    URL = f"https://{hqhost}:8443/rest/stream/replica/autosetup?path={source_stream_path}&replica={target_stream_path}&multimaster=true"

    try:
        response = await run.io_bound(requests.get, url=URL, auth=(user, password), verify=False)
        response.raise_for_status()

    except Exception as error:
        logger.warning(error)

    if response:
        obj = response.json()
        logger.info("Stream replica: %s", obj)
    else:
        logger.warning("Cannot get stream replica")


# Start volume mirror from edge
async def start_volume_mirroring(edgehost: str, user: str, password: str):
    # await run.io_bound(run_command, f"maprcli volume mirror start -cluster {os.environ['EDGE_CLUSTER']} -name {EDGE_MISSION_FILES}")
    mirror_volume = get_volume_name(EDGE_MISSION_FILES)

    logger.debug("Starting volume mirror for %s", mirror_volume)
    URL = f"https://{edgehost}:8443/rest/volume/mirror/start?name={mirror_volume}"

    # logger.debug("REST_URL: %s", URL)
    try:
        response = await run.io_bound(requests.post, url=URL, auth=(user, password), verify=False)
        response.raise_for_status()

    except Exception as error:
        logger.warning(error)

    if response:
        obj = response.json()
        logger.info("Volume mirror response: %s", obj)
    else:
        logger.warning("Cannot start volume mirroring")



async def toggle_replication():
    """
    Pause/resume stream replication - EDGE to HQ
    """

    toggle_action = "resume" if app.storage.general.get("stream_replication", None) == "PAUSED" else "pause"

    REST_URL = f"https://{app.storage.user['EDGE_HOST']}:8443/rest/stream/replica/{toggle_action}?path=/mapr/{EdgeSite['clusterName']}{EDGE_STREAM_REPLICATED}&replica=/mapr/{HQSite['clusterName']}{HQ_STREAM_REPLICATED}"

    try:
        response = requests.get(url=REST_URL, auth=(app.storage.user["MAPR_USER"], app.storage.user["MAPR_PASS"]), verify=False)
        response.raise_for_status()

        logger.info(f"Toggle replication response: {response.text}")

    except Exception as error:
        logger.warning(error)


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
        ui.image(f"https://{app.storage.user['MAPR_USER']}:{app.storage.user['MAPR_PASS']}@{host}:8443/files{imageUrl}")

    show.on("close", show.clear)
    show.open()


# return image to display on UI
async def dashboard_tiles(host: str, messages: list):
    """
    host: <string> HQ_HOST | EDGE_HOST
    messages: <list[dict]>
    """

    if host is None: return
    # if source in app.storage.general and len(app.storage.general[source]) > 0:
    # Return an image card if available
    while len(messages) > 0:
        service, title, description, imageUrl = messages.pop()
        # logger.debug("Process tile for service: %s, title: %s, description: %s, and imageurl: %s", service, title, description, imageUrl)

        if service == "Asset Viewer Service" or service == "Image Download Service":
            with ui.card().classes("h-80 animate-fadeIn").props("bordered").tight() as img:
                with ui.card_section().classes(f"w-full text-sm {BGCOLORS[service]}"):
                    ui.label(service)
                # TODO: use /mapr mount
                ui.image(f"https://{app.storage.user['MAPR_USER']}:{app.storage.user['MAPR_PASS']}@{host}:8443/files{imageUrl}")
                ui.space()
                with ui.card_section():
                    ui.label(textwrap.shorten(title, 32)).classes("text-sm")

            img.on("click", lambda h=host,t=title,d=description,u=imageUrl: show_image(h,t,d,u))
            if service == "Image Download Service": # auto remove tiles if not asset viewer
                ui.timer(app.storage.general.get("tile_remove", 20), img.delete, once=True)

        else:
            with ui.card().classes("h-80 animate-fadeIn").props("bordered") as img:
                with ui.card_section().classes(f"w-full text-sm {BGCOLORS[service]}"):
                    ui.label(service)
                with ui.card_section().classes("text-sm"):
                    ui.label(textwrap.shorten(description, 64))
                ui.space()
                with ui.card_section().classes("text-sm"):
                    ui.label(textwrap.shorten(title, 32))

            ui.timer(app.storage.general.get("tile_remove", 20), img.delete, once=True)

        return img
