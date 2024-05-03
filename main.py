import logging
import os
import importlib_resources

import requests
from nicegui import app, ui, binding
import inspect
from edge_services import asset_request_service, asset_viewer_service, broadcast_listener_service, make_asset_request, upstream_comm_service
from functions import *

from helpers import *
from hq_services import asset_broadcast_service, asset_response_service, nasa_feed_service, image_download_service
import steps

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

    # if "services" not in app.storage.general.keys():
    app.storage.general["services"] = {}

    # Reset previous run state if it was hang
    app.storage.user["busy"] = False

    # and ui counters
    app.storage.general["nasafeed_count"] = 0
    app.storage.general["imagedownload_count"] = 0
    app.storage.general["assetbroadcast_count"] = 0
    app.storage.general["assetrequest_count"] = 0
    app.storage.general["assetresponse_count"] = 0
    app.storage.general["broadcastlistener_count"] = 0
    app.storage.general["auditlistener_count"] = 0
    app.storage.general["upstreamcomm_count"] = 0
    app.storage.general["imageviewer_count"] = 0

    # and image lists
    app.storage.general["hqimages"] = []
    app.storage.general["edgeimages"] = []

    # and connectivity status
    app.storage.general["stream_replication"] = ""
    app.storage.general["volume_replication"] = ""

    # Header
    with ui.header(elevated=True).style('background-color: #3874c8').classes('items-center justify-between uppercase'):
        ui.label(f"{APP_NAME}: {TITLE}")
        ui.space()

        ui.label("HQ Cluster:")
        ui.link(target=f"https://{os.environ['MAPR_IP']}:8443/", new_tab=True).bind_text_from(os.environ, "MAPR_CLUSTER").classes("text-sky-300 hover:text-blue-600")
        ui.space()
        ui.label("Edge Cluster:")
        ui.link(target=f"https://{os.environ['EDGE_IP']}:8443/", new_tab=True).bind_text_from(os.environ, "EDGE_CLUSTER").classes("text-sky-300 hover:text-blue-600")
        ui.space()

        # Status indicator
        ui.spinner("ios", size="2em", color="red").bind_visibility_from(
            app.storage.user, "busy"
        )
        ui.icon("check_circle", size="2em", color="green").bind_visibility_from(
            app.storage.user, "busy", lambda x: not x
        )

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
    with ui.expansion(
        "Set up the demo environment", icon="engineering", caption="Prepare the cluster for the demo"
    ).classes("w-full text-bold") as setup_page:

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

    setup_page.bind_value(app.storage.general["ui"], "setup")

    ui.separator()

    with ui.splitter().classes("px-2") as splitter:
        # HQ Dashboard
        with splitter.before:
            # HQ
            ui.label("HQ Dashboard").classes("text-bold")

            with ui.row().classes("w-full place-items-center h-16"):
                ui.label("Services")
                ui.space()
                for svc in SERVICES["HQ"]:
                    service_status(svc)
                    ui.space()

            ui.label(steps.INTRO).classes("h-32")

            with ui.stepper().classes("w-full h-96").props("contracted") as stepper:
                with ui.step('Data Ingestion'):
                    ui.label("Data Ingestion").classes("text-bold")
                    ui.label(steps.INGESTION)

                    with ui.expansion("Code", caption="Code to enable service", icon="code").classes("w-full"):
                        ui.code(inspect.getsource(extract_wrapped(nasa_feed_service))).classes(
                            "w-full"
                        )

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, nasa_feed_service
                            ),
                        )
                        ui.button('Next', on_click=stepper.next, color="secondary")
                        # ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step('Data Processing (ETL)'):
                    ui.label("Data Processing (ETL)").classes("text-bold")

                    ui.label(steps.ETL)

                    with ui.expansion("Code", caption="Code to enable service", icon="code").classes("w-full"):
                        ui.code(inspect.getsource(extract_wrapped(image_download_service))).classes(
                            "w-full"
                        )

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, image_download_service
                            ),
                        )
                        ui.button('Next', on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step('Broadcast'):
                    ui.label("Broadcast").classes("text-bold")
                    ui.label(
                        "Now we are ready to know all the field teams that we have new intelligence. We send a message to Asset Broadcast topic, so any/all subscribers can see relevant metadata for that asset."
                    )

                    with ui.expansion("Code", caption="Code to enable service", icon="code").classes("w-full"):
                        ui.code(inspect.getsource(extract_wrapped(asset_broadcast_service))).classes(
                            "w-full"
                        )

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, asset_broadcast_service
                            ),
                        )
                        ui.button('Next', on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step('Request Listener'):
                    ui.label("Request Listener").classes("text-bold")
                    ui.label(
                        "We broadcast the assets we've got from the feed. Now we are ready to serve the assets for any fielt team if they request it. For that, we have a listener service that monitors the topic ASSET_REQUEST for any request from the field."
                    )

                    with ui.expansion("Code", caption="Code to enable service", icon="code").classes("w-full"):
                        ui.code(
                            inspect.getsource(extract_wrapped(asset_response_service))
                        ).classes("w-full")

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, asset_response_service
                            ),
                        )
                        ui.button("Next", on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step("Enable stream replication"):
                    ui.label("Enable stream replication").classes("text-bold")
                    ui.label(
                        "We need to establish bi-directional communication between HQ and Edge. Let's first enable the replication of broadcast stream so we can get intelligence data from HQ."
                    )

                    with ui.expansion(
                        "Code", caption="Code to setup replication", icon="code"
                    ).classes("w-full"):
                        ui.code(inspect.getsource(stream_replica_setup)).classes(
                            "w-full"
                        )

                    with ui.stepper_navigation():
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, stream_replica_setup
                            ),
                        )
                        ui.button("Back", on_click=stepper.previous, color="none")

                    ui.label("Now you are ready to proceed with the services used by the Field teams. Proceed to Edge dashboard for the rest of the demo.")

            # The image display widget to show downloaded assets in real-time
            with ui.scroll_area().classes("w-full h-64"):
                with ui.grid(columns=5).classes("p-1") as images:
                    ui.timer(0.5, lambda: imageshow(os.environ['MAPR_IP'], "hqimages"))

        # Edge Dashboard
        with splitter.after:
            # EDGE
            with ui.row().classes("w-full"):
                ui.label("Edge Dashboard").classes("pl-2 text-bold")
                ui.space()
                ui.label("Volume:")
                ui.label().bind_text_from(app.storage.general, "volume_replication")
                ui.space()
                ui.label("Stream:")
                ui.label().bind_text_from(app.storage.general, "stream_replication")

            with ui.row().classes("w-full place-items-center h-16"):
                ui.label("Services").classes("p-2")
                ui.space()
                for svc in SERVICES["EDGE"]:
                    service_status(svc)
                    ui.space()

            ui.label("Edge services simulate an environment where intermittent connectivity and low-bandwidth data transfers are the norm. \
                        In such environments, we would like to minimize the data and the overhead, while keeping information relevant and intact. \
                        All this communication happens bi-directionally in real-time with lightweight messaging service, Ezmeral Event Store.").classes("pl-2 h-32")

            with ui.stepper().classes("w-full h-96").props("contracted") as stepper:
                # with ui.step("Setup"):
                #     ui.label("Setup").classes("text-bold")
                #     ui.label(
                #         "Set up edge cluster for HQ connection and data replication"
                #     )

                #     with ui.expansion(
                #         "Code", caption="Code to enable service", icon="code"
                #     ).classes("w-full"):
                #         ui.code(
                #             inspect.getsource(
                #                 prepare_edge
                #             )
                #         ).classes("w-full")

                #     ui.label("Click 'Run' to enable the service")

                #     with ui.stepper_navigation():
                #         ui.button(
                #             "Run",
                #             on_click=lambda: asyncio.get_event_loop().run_in_executor(
                #                 None, prepare_edge
                #             ),
                #         )
                #         ui.button("Next", on_click=stepper.next, color="secondary")
                #         # ui.button("Back", on_click=stepper.previous, color="none")

                with ui.step("Upstream Comm"):
                    ui.label("Upstream Comm").classes("text-bold")
                    ui.label(
                        "Monitor upstream connectivity and data replication status"
                    )

                    with ui.expansion(
                        "Code", caption="Code to enable service", icon="code"
                    ).classes("w-full"):
                        ui.code(
                            inspect.getsource(
                                extract_wrapped(upstream_comm_service)
                            )
                        ).classes("w-full")

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, upstream_comm_service
                            ),
                        )
                        ui.button("Next", on_click=stepper.next, color="secondary")
                        # ui.button("Back", on_click=stepper.previous, color="none")

                with ui.step("Broadcast Listener"):
                    ui.label("Broadcast Listener").classes("text-bold")
                    ui.label(
                        "We will subscribe to the ASSET_BROADCAST topic so we can be notified of incoming new assets."
                    )

                    with ui.expansion(
                        "Code", caption="Code to enable service", icon="code"
                    ).classes("w-full"):
                        ui.code(
                            inspect.getsource(extract_wrapped(broadcast_listener_service))
                        ).classes("w-full")

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, broadcast_listener_service
                            ),
                        )
                        ui.button("Next", on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step("Asset Request"):
                    ui.label("Asset Request").classes("text-bold")
                    ui.label(
                        "Any assets requested by clicking on the asset data will be put into ASSET_REQUEST topic, so HQ can process and send the asset through the replicated volume."
                    )

                    with ui.expansion(
                        "Code", caption="Code to enable service", icon="code"
                    ).classes("w-full"):
                        ui.code(
                            inspect.getsource(extract_wrapped(asset_request_service))
                        ).classes("w-full")

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, asset_request_service
                            ),
                        )
                        ui.button("Next", on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step("Asset Viewer"):
                    ui.label("Asset Viewer").classes("text-bold")
                    ui.label(
                        "We will periodically mirror the volume where the requested assets are copied."
                    )

                    with ui.expansion(
                        "Code", caption="Code to enable service", icon="code"
                    ).classes("w-full"):
                        ui.code(
                            inspect.getsource(extract_wrapped(asset_viewer_service))
                        ).classes("w-full")

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, asset_viewer_service
                            ),
                        )
                        # ui.button("Next", on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

            # List the broadcasted messages
            ui.label("Available Assets")
            with ui.scroll_area().classes("w-full h-48"):
                assets = (
                    ui.table(
                        columns=[
                            # {
                            #     "name": "assetID",
                            #     "label": "Asset",
                            #     "field": "assetID",
                            #     "required": True,
                            #     "align": "left",
                            # },
                            {
                                "name": "title",
                                "label": "Title",
                                "field": "title",
                                "required": True,
                                "align": "left",
                            },
                            {
                                "name": "status",
                                "label": "Status",
                                "field": "status",
                            }
                        ],
                        rows=[],
                        row_key="assetID",
                        pagination=0,
                    )
                    .on("rowClick", lambda e: make_asset_request(e.args[1]))
                    .props("dense separator=None wrap-cells")
                    .classes("w-full")
                )
                ui.timer(
                    0.5,
                    lambda: assets.update_rows(
                        app.storage.general.get("edge_broadcastreceived", [])
                    ),
                )
            # The image display widget to show downloaded assets in real-time
            with ui.scroll_area().classes("w-full h-64"):
                with ui.grid(columns=6).classes("p-1") as images:
                    ui.timer(0.5, lambda: imageshow(os.environ['EDGE_IP'], "edgeimages"))

    ui.separator()

    log = ui.log().classes("w-full h-40 resize-y").style("white-space: pre-wrap")
    logger.addHandler(LogElementHandler(log, logging.INFO))


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

app.on_exception(gracefully_fail)
