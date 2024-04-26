import logging
import os
import subprocess
import textwrap
from nicegui import app, run
from helpers import *

logger = logging.getLogger()

async def run_command(cmd):
    app.storage.user["busy"] = True
    try:
        result = await run.io_bound(subprocess.run, cmd, shell=True, capture_output=True, universal_newlines=True)
        if result.returncode == 0:
            logger.info("# %s ==> OK", cmd)
        else:
            logger.info("# %s ==> ERROR", cmd)

        if result.stdout != "":
            logger.debug(result.stdout)
        if result.stderr != "":
            if "Failed to connect to IPv6" not in result.stderr:
                logger.debug(result.stderr)
            else:
                logger.debug("ignoring IPv6 errors...")

    except Exception as error:
        logger.warning(error)

    finally:
        app.storage.user["busy"] = False


async def prepare():
    await run_command(f"maprcli audit data -cluster {os.environ['MAPR_CLUSTER']} -enabled true -retention 1")
    await run_command(f"maprcli config save -cluster {os.environ['MAPR_CLUSTER']} -values \"{{ 'mfs.enable.audit.as.stream':'1' }}\" ")
    await run_command(f"maprcli volume create -name {HQ_VOLUME_NAME} -cluster {os.environ['MAPR_CLUSTER']} -path {HQ_VOLUME_PATH} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1")
    await run_command(f"maprcli volume audit -name {HQ_VOLUME_NAME} -cluster {os.environ['MAPR_CLUSTER']} -dataauditops '+create,+delete,+tablecreate,-all' -forceenable true -enabled true")
    await run_command(f"hadoop mfs -setaudit on {HQ_VOLUME_PATH}")
    await run_command(f"maprcli table create -path {HQ_VOLUME_PATH}/{HQ_IMAGETABLE} -tabletype json")
    await run_command(f"maprcli stream create -path {HQ_VOLUME_PATH}/{STREAM_LOCAL} -ttl 86400 -compression lz4 -produceperm p -consumeperm p -topicperm p")
    await run_command(f"maprcli stream create -path {HQ_VOLUME_PATH}/{HQ_STREAM_REPLICATED} -ttl 86400 -compression lz4 -produceperm p -consumeperm p -topicperm p")
    await run_command(f"maprcli volume create -name {HQ_MISSION_FILES} -cluster {os.environ['MAPR_CLUSTER']} -path {HQ_VOLUME_PATH}/{HQ_MISSION_FILES} -replication 1 -minreplication 1 -nsreplication 1 -nsminreplication 1")


def toggle_service(prop: str):
    app.storage.general["services"][prop] = not app.storage.general["services"].get(prop, False)

# return buttons to show and control service status
def service_status(service: tuple):
    name, icon = service
    prop = name.lower().replace(" ", "")

    if prop not in app.storage.general["services"]:
        app.storage.general["services"][prop] = False

    with ui.button(on_click=lambda n=prop: toggle_service(n)).tooltip(name).props("round").bind_visibility_from(
        app.storage.general["services"], prop
    ).classes("size-fit"):
        ui.icon(icon, size="xl")
        ui.badge().bind_text_from(app.storage.general, f"{prop}_count").props('floating')

    with ui.button(color="none", on_click=lambda n=prop: toggle_service(n)).tooltip(name).props("round").bind_visibility_from(
        app.storage.general["services"], prop, backward=lambda x: not x
    ).classes("size-fit"):
        ui.icon(icon, size="xl")
        ui.badge().bind_text_from(app.storage.general, f"{prop}_count").props('floating')


# return image to display on UI
def imageshow(src):
    # TODO: delete old images
    if src in app.storage.general and len(app.storage.general[src]) > 0:
        title, location = app.storage.general[src].pop(0)
        # TODO: use /mapr mount
        img_url = f"https://{os.environ['MAPR_USER']}:{os.environ['MAPR_PASS']}@{os.environ['MAPR_IP']}:8443/files{location}"
        with ui.card().tooltip(title).classes("h-64") as img:
            ui.image(img_url)
            ui.space()
            with ui.card_section().classes("align-text-bottom text-sm"):
                ui.label(textwrap.shorten(title, 24))

        return img


# Handle exceptions without UI failure
def gracefully_fail(exc: Exception):
    print("gracefully failing...")
    logger.debug("Exception: %s", exc)
    app.storage.user["busy"] = False

