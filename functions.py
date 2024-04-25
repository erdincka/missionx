import logging
import os
import subprocess
from nicegui import app, run
from helpers import *

logger = logging.getLogger("functions")

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


def service_status(service: tuple):
    name, icon = service
    prop = name.lower().replace(" ", "")

    if prop not in app.storage.general["services"]:
        app.storage.general["services"][prop] = False

    ui.button(icon=icon, on_click=lambda n=prop: toggle_service(n)).tooltip(name).props("flat round").bind_visibility_from(
        app.storage.general["services"], prop
    )

    ui.button(icon=icon, color="none", on_click=lambda n=prop: toggle_service(n)).tooltip(name).props("flat round").bind_visibility_from(
        app.storage.general["services"], prop, backward=lambda x: not x
    )


