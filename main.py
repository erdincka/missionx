import logging
import os
import importlib_resources

import requests
from nicegui import app, ui, binding
import inspect
from functions import *

from hq import hq_page

from edge import edge_page

# configure the logging
configure_logging()

# logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)

TITLE = "Data Fabric Core to Edge Demo"
STORAGE_SECRET = "ezmer@1r0cks"

@ui.page("/")
async def home():
    if "ui" not in app.storage.general.keys():
        app.storage.general["ui"] = {}

    # if "services" not in app.storage.general.keys():
    app.storage.general["services"] = {}

    # Reset previous run state if it was hang
    app.storage.user["busy"] = False

    # and ui counters & settings
    for svc in list(SERVICES["HQ"] + SERVICES["EDGE"]):
        name, delay = svc
        prop = name.lower().replace(' ', '')
        app.storage.general[f"{prop}_count"] = 0
        app.storage.general[f"{prop}_delay"] = delay
    app.storage.general["tile_remove"] = 20

    # and image lists
    app.storage.general["dashboard_hq"] = []
    app.storage.general["dashboard_edge"] = []

    # and connectivity status
    app.storage.general["stream_replication"] = ""
    app.storage.general["volume_replication"] = ""

    # Header
    with ui.header(elevated=True).style('background-color: #3874c8').classes('items-center justify-between'):
        ui.label(f"{APP_NAME}: {TITLE}")
        ui.space()

        ui.label("HQ Cluster:")
        ui.link(target=f"https://{os.environ['MAPR_USER']}:{os.environ['MAPR_PASS']}@{os.environ['MAPR_IP']}:8443/", new_tab=True).bind_text_from(os.environ, "MAPR_CLUSTER").classes("text-sky-300 hover:text-blue-600")
        ui.space()
        ui.label("Edge Cluster:")
        ui.link(target=f"https://{os.environ['MAPR_USER']}:{os.environ['MAPR_PASS']}@{os.environ['EDGE_IP']}:8443/", new_tab=True).bind_text_from(os.environ, "EDGE_CLUSTER").classes("text-sky-300 hover:text-blue-600")
        ui.space()

        # Status indicator
        ui.spinner("ios", size="2em", color="red").bind_visibility_from(
            app.storage.user, "busy"
        ).tooltip("Running")
        ui.icon("check_circle", size="2em", color="green").bind_visibility_from(
            app.storage.user, "busy", lambda x: not x
        ).tooltip("Ready")
        ui.switch(on_change=toggle_debug).bind_value(app.storage.user, "debugging").tooltip("Debug")

    # Info
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

    # Prepare
    with ui.expansion("Set up the demo environment", icon="engineering", caption="Prepare the cluster for the demo").classes("w-full text-bold") as setup_page:

        ui.label("Create the volumes, topics and tables at the HQ cluster.")

        ui.code(inspect.getsource(prepare_core)).classes("w-full")

        ui.button("Run", on_click=prepare_core).bind_enabled_from(
            app.storage.user, "busy", lambda x: not x
        )

        ui.space()

        ui.label("Create the volume at the Edge cluster.")

        ui.code(inspect.getsource(prepare_edge)).classes("w-full")

        ui.button("Run", on_click=prepare_edge).bind_enabled_from(
            app.storage.user, "busy", lambda x: not x
        )

        ui.space()

        ui.label("We need to establish bi-directional communication between HQ and Edge. Let's first enable the replication of broadcast stream so we can get intelligence data from HQ.")

        ui.code(inspect.getsource(stream_replica_setup)).classes("w-full")

        ui.button("Run", on_click=stream_replica_setup).bind_enabled_from(
            app.storage.user, "busy", lambda x: not x
        )


    setup_page.bind_value(app.storage.general["ui"], "setup")

    ui.separator()

    with ui.splitter(limits=(25,75)) as site_panels:
        with site_panels.before:
            hq_page()
        with site_panels.after:
            edge_page()

    ui.separator()
    log = ui.log().classes("w-full h-40 resize-y").style("white-space: pre-wrap")
    logger.addHandler(LogElementHandler(log, logging.INFO))

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title=TITLE,
        dark=None,
        storage_secret=STORAGE_SECRET,
        reload=True,
        port=3000,
    )

# catch-all exceptions
app.on_exception(gracefully_fail)
# app.on_disconnect(app_init)
