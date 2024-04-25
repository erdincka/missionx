import logging
import os
import importlib_resources

import requests
from nicegui import app, ui, binding
import inspect
from functions import *

from helpers import *

logging.basicConfig(level=logging.DEBUG,
                format="%(asctime)s:%(levelname)s:%(funcName)s: %(message)s",
                datefmt='%H:%M:%S')

logger = logging.getLogger(APP_NAME)

# https://sam.hooke.me/note/2023/10/nicegui-binding-propagation-warning/
binding.MAX_PROPAGATION_TIME = 0.05

TITLE = "Data Fabric Core to Edge Demo"
STORAGE_SECRET = "ezmer@1r0cks"

@ui.page("/")
def home():
    if "ui" not in app.storage.general.keys():
        app.storage.general["ui"] = {}
    # Reset service statuses for each run
    app.storage.general["services"] = {}

    # and previous run state if it was hang
    app.storage.user["busy"] = False

    # and ui counters
    app.storage.user["ui"] = {}

    # and image list
    app.storage.user["hqimages"] = []

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
        ui.image(importlib_resources.files("app").joinpath(DEMO["image"])).classes(
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

    # Dashboards
    with ui.splitter().classes("w-full") as splitter:
        with splitter.before:
            with ui.row().classes("w-full items-center p-1"):
                ui.label("HQ Dashboard").classes("mr-2 text-bold")

                ui.space()

                for svc in SERVICES["HQ"]:
                    service_status(svc)                    

                ui.space()

                with ui.row():
                    ui.label("Feed: ")
                    ui.label().bind_text_from(app.storage.user["ui"], "nasaevent")
                with ui.row():
                    ui.label("Assets: ")
                    ui.label().bind_text_from(app.storage.user["ui"], "imagedownload")
                with ui.row():
                    ui.label("Requests: ")
                    ui.label().bind_text_from(app.storage.user["ui"], "assetrequest")
            ui.separator()

            with ui.scroll_area().classes("w-full h-80"):
                with ui.grid(columns=3).classes("p-1") as images:
                    # ui.timer(0.5, lambda: imageshow("hqimages"))
                    pass

        with splitter.after:
            with ui.row().classes("w-full items-center p-1"):
                ui.label("Edge Dashboard").classes("ml-2 text-bold")

                ui.space()

                # ui.icon("thumb_up").on('click', stream_replica_setup)

                ui.space()

                with ui.row():
                    ui.label("Events: ")
                    ui.label().bind_text_from(app.storage.user["ui"], "assetbroadcast")

                    ui.label("Responses: ")
                    ui.label().bind_text_from(app.storage.user["ui"], "upstreamcomm")

                    # ui.button("Stream", on_click=stream_replica_setup, icon="settings").props("flat")
            ui.separator()

            with ui.grid(columns=3).classes("p-1"):
                # ui.timer(0.5, lambda: imageshow("edgeimages"))
                pass

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

# Entry point for the module
def enter():
    logger.debug("Running as module")
    ui.run(
        title=TITLE,
        dark=None,
        storage_secret=STORAGE_SECRET,
        reload=False,
        port=3000,
    )


# For development and debugs
if __name__ in {"__main__", "__mp_main__"}:
    logger.debug("Running in DEV")

    ui.run(
        title=TITLE,
        dark=None,
        storage_secret=STORAGE_SECRET,
        reload=True,
        port=3000,
    )

# client lifecycle
# app.on_exception(stop_services)
# app.on_disconnect(stop_services)
# app.on_connect(start_services)
