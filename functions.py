import inspect
import logging
import os
import textwrap
import httpx
from nicegui import app, run
import requests
from common import *
from helpers import *

logger = logging.getLogger()

async def run_command_with_dialog(command: str) -> None:
    """
    Run a command in the background and display the output in the pre-created dialog.
    """

    with ui.dialog().props("full-width") as dialog, ui.card().classes("grow relative"):
        ui.button(icon="close", on_click=dialog.close).props("flat round dense").classes("absolute right-2 top-2")
        ui.label(f"Running: {command}").classes("text-bold")
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

    yield f"Finished: {command}"


def get_cluster_name(key: str):
    """
    Get the name of the cluster from the settings.
    """

    if key in app.storage.user.keys() and "name" in app.storage.user[key].keys():
        return app.storage.user[key]["name"]
    else:
        return None


async def delete_volumes_and_streams(cluster: str, volumes: list):
    """
    Delete all streams and volumes for a cluster.
    params:
    cluster - the name of the cluster to delete from, either "HQ" or "EDGE"
    volumes - a list of volume names to delete
    """

    host = app.storage.user[cluster]["ip"]
    auth = (app.storage.user[cluster + "_USER"], app.storage.user[cluster + "_PASS"])

    app.storage.user['busy'] = True

    for vol in volumes:

        URL = f"https://{app.storage.user[host]}:8443/rest/volume/remove?name={vol}"
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(URL, auth=auth)

            if response is None or response.status_code != 200:
                logger.warning("REST failed for delete volume: %s", vol)
                logger.warning("Response: %s", response.text)

            else:
                res = response.json()
                if res['status'] == "OK":
                    ui.notify(f"Volume '{vol}' deleted", type='warning')
                elif res['status'] == "ERROR":
                    ui.notify(f"{vol}: {res['errors'][0]['desc']}", type='warning')

    app.storage.user['busy'] = False


# def run_command(cmd):
#     try:
#         result = subprocess.run(cmd, shell=True, capture_output=True, universal_newlines=True)
#         if result.returncode == 0:
#             logger.debug("# %s ==> OK", cmd)
#         else:
#             logger.warning("# %s ==> %s", cmd, result.stdout)
#             logger.debug(result.stderr)

#         if result.stdout != "":
#             logger.debug(result.stdout)
#         if result.stderr != "":
#             if "Failed to connect to IPv6" not in result.stderr:
#                 logger.debug(result)
#             else:
#                 logger.debug("ignoring IPv6 errors...")

#     except Exception as error:
#         logger.warning(error)


# def get_command_output(cmd):
#     try:
#         result = subprocess.run(cmd, shell=True, capture_output=True, universal_newlines=True)
#         if result.returncode == 0:
#             logger.debug("# %s ==> OK", cmd)
#         else:
#             logger.warning("# %s ==> %s", cmd, result.stdout)
#             logger.debug(result.stderr)

#         if result.stdout != "":
#             return result.stdout
#         if result.stderr != "":
#             if "Failed to connect to IPv6" not in result.stderr:
#                 logger.debug(result)
#             else:
#                 logger.debug("ignoring IPv6 errors...")

#     except Exception as error:
#         logger.warning(error)


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
    await run.io_bound(run_command, f"echo {app.storage.user['MAPR_PASS']} | maprlogin password -cluster {os.environ['EDGE_CLUSTER']} -user {app.storage.user['MAPR_USER']}")
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
                ui.image(f"https://{app.storage.user['MAPR_USER']}:{app.storage.user['MAPR_PASS']}@{host}:8443/files{imageUrl}")
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

    logger.debug("REST_URL: %s", REST_URL)
    try:
        response = await run.io_bound(requests.get, url=REST_URL, auth=(app.storage.user["MAPR_USER"], app.storage.user["MAPR_PASS"]), verify=False)
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

    REST_URL = f"https://{os.environ['EDGE_IP']}:8443/rest/stream/replica/{toggle_action}?path={EDGE_VOLUME_PATH}/{EDGE_STREAM_REPLICATED}&replica={HQ_VOLUME_PATH}/{HQ_STREAM_REPLICATED}"

    try:
        response = requests.get(url=REST_URL, auth=(app.storage.user["MAPR_USER"], app.storage.user["MAPR_PASS"]), verify=False)
        response.raise_for_status()

        logger.debug(response.text)

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
