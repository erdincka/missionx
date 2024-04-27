import logging
import os
import importlib_resources

import requests
from nicegui import app, ui, binding
import inspect
from functions import *

from helpers import *
from services import asset_broadcast_service, nasa_feed_service, image_download_service

logging.basicConfig(level=logging.INFO,
                format="%(asctime)s:%(levelname)s:%(funcName)s: %(message)s",
                datefmt='%H:%M:%S')

logger = logging.getLogger()

# https://sam.hooke.me/note/2023/10/nicegui-binding-propagation-warning/
binding.MAX_PROPAGATION_TIME = 0.05

TITLE = "Data Fabric Core to Edge Demo"
STORAGE_SECRET = "ezmer@1r0cks"

@ui.page("/")
async def home():
    if "ui" not in app.storage.general.keys():
        app.storage.general["ui"] = {}

    if "services" not in app.storage.general.keys():
        app.storage.general["services"] = {}

    # Reset previous run state if it was hang
    app.storage.user["busy"] = False

    # ui counters
    app.storage.general["nasafeed_count"] = 0
    app.storage.general["imagedownload_count"] = 0
    app.storage.general["assetrequest_count"] = 0
    app.storage.general["assetbroadcast_count"] = 0
    app.storage.general["upstreamcomm_count"] = 0

    # and image list
    app.storage.general["hqimages"] = []

    with ui.header(elevated=True).style('background-color: #3874c8').classes('items-center justify-between uppercase'):
        ui.label(APP_NAME)
        ui.space()

        ui.label("HQ Cluster:")
        ui.label().bind_text_from(os.environ, "MAPR_CLUSTER")
        ui.space()
        ui.label("HQ Cluster IP:")
        ui.label().bind_text_from(os.environ, "MAPR_IP")
        ui.space()
        ui.label("Edge Cluster:")
        ui.label().bind_text_from(os.environ, "MAPR_CLUSTER_EDGE")
        ui.space()
        ui.label("Edge Cluster IP:")
        ui.label().bind_text_from(os.environ, "MAPR_IP_EDGE")
        ui.space()
 
        # Status indicator
        ui.spinner("ios", size="2em", color="red").bind_visibility_from(
            app.storage.user, "busy"
        )
        ui.icon("check_circle", size="2em", color="green").bind_visibility_from(
            app.storage.user, "busy", lambda x: not x
        )

    with ui.expansion(
        TITLE,
        icon="info",
        caption="Core to Edge end to end pipeline processing using Ezmeral Data Fabric",
    ).classes("w-full").classes("text-bold"):
        ui.markdown(DEMO["description"]).classes("font-normal")
        ui.image(importlib_resources.files("main").joinpath(DEMO["image"])).classes(
            "object-scale-down g-10"
        )

    ui.separator()

    with ui.expansion(
        "Set up the demo environment", icon="engineering", caption="Prepare to run"
    ).classes("w-full text-bold") as setup_page:

        ui.label("Create the volume, topics and tables to use with this demo.")

        ui.code(inspect.getsource(prepare)).classes("w-full")

        ui.button("Run", on_click=prepare).bind_enabled_from(
            app.storage.user, "busy", lambda x: not x
        )

    setup_page.bind_value(app.storage.general["ui"], "setup")

    ui.separator()

    # HQ
    ui.label("HQ Dashboard").classes("text-bold")

    with ui.row().classes("w-full place-items-center"):
        ui.label("Services")
        ui.space()
        for svc in SERVICES["HQ"]:
            service_status(svc)
            ui.space()

    with ui.scroll_area().classes("w-full h-80"):
        with ui.grid(columns=6).classes("p-1") as images:
            ui.timer(0.5, lambda: imageshow("hqimages"))


    ui.space()

    log = ui.log().classes("w-full h-40 resize-y").style("white-space: pre-wrap")
    logger.addHandler(LogElementHandler(log, logging.INFO))

    ui.separator()

    # EDGE
    ui.label("Edge Dashboard").classes("text-bold")

    with ui.row().classes("w-full place-items-center"):
        ui.label("Services")
        ui.space()
        for svc in SERVICES["EDGE"]:
            service_status(svc)
            ui.space()

    with ui.scroll_area().classes("w-full h-80"):
        with ui.grid(columns=6).classes("p-1") as images:
            ui.timer(0.5, lambda: imageshow("edgeimages"))



# INSECURE REQUESTS ARE OK in Demos
requests.packages.urllib3.disable_warnings()
urllib_logger = logging.getLogger("urllib3.connectionpool")
urllib_logger.setLevel(logging.WARNING)

requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.WARNING)
watcher_logger = logging.getLogger("watchfiles.main")
watcher_logger.setLevel(logging.FATAL)

faker_log = logging.getLogger("faker.factory")
faker_log.setLevel(logging.FATAL)

paramiko_log = logging.getLogger("paramiko.transport")
paramiko_log.setLevel(logging.FATAL)

charset_log = logging.getLogger("charset_normalizer")
charset_log.setLevel(logging.FATAL)

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title=TITLE,
        dark=None,
        storage_secret=STORAGE_SECRET,
        reload=True,
        port=3000,
    )
    # Start services
    asyncio.get_event_loop().run_in_executor(None, nasa_feed_service)
    asyncio.get_event_loop().run_in_executor(None, image_download_service)
    asyncio.get_event_loop().run_in_executor(None, asset_broadcast_service)

app.on_exception(gracefully_fail)