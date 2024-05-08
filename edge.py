from nicegui import app, ui
import inspect
from edge_services import asset_request_service, asset_viewer_service, broadcast_listener_service, make_asset_request, upstream_comm_service
from functions import *

from helpers import *

def edge_page():
    # Edge Dashboard
    with ui.row().classes("w-full no-wrap place-items-center"):
        ui.label("Edge Dashboard").classes("text-bold ml-2")
        ui.icon("info").tooltip("Edge services simulate an environment where intermittent connectivity and low-bandwidth data transfers are the norm. \
            In such environments, we would like to minimize the data and the overhead, while keeping information relevant and intact. \
            All this communication happens bi-directionally in real-time with lightweight messaging service, Ezmeral Event Store.")

        ui.space()

        # Connectivity indicator
        with ui.row().classes("place-items-center"):
            ui.label().bind_text_from(app.storage.general, "stream_replication")
            ui.button("Mirror", on_click=mirror_volume).classes("py-0 min-h-0").props("flat")
            ui.label().bind_text_from(app.storage.general, "volume_replication")

    with ui.row().classes("w-full no-wrap ml-2"):
        # left panel
        with ui.column().classes("w-fit"):
            with ui.list().props('bordered separator').classes("text-xs w-full"):
                ui.item_label('Data Feed and Services').props('header').classes('text-bold text-sm bg-primary')
                for svc in SERVICES["EDGE"]:
                    service_status(svc)

            with ui.list().props('bordered separator').classes("text-xs w-full"):
                ui.item_label('System Metrics').props('header').classes('text-bold text-sm bg-primary')
                for svc in SERVICES["EDGE"]:
                    service_counter(svc)

            with ui.list().props('bordered separator').classes("text-xs w-full"):
                ui.item_label('Control Panel').props('header').classes('text-bold text-sm bg-primary')
                for svc in SERVICES["EDGE"]:
                    service_settings(svc)


        # right panel
        with ui.column().classes("w-full"):
            with ui.stepper().classes("w-full").props("vertical header-nav") as stepper:
                with ui.step("Upstream Comm"):
                    ui.label(
                        "Monitor upstream connectivity and data replication status"
                    )

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button("Show code", on_click=lambda: show_code(extract_wrapped(upstream_comm_service))).props("outline")
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, upstream_comm_service
                            ),
                        )
                        ui.button("Next", on_click=stepper.next, color="secondary")
                        # ui.button("Back", on_click=stepper.previous, color="none")

                with ui.step("Broadcast Listener"):
                    ui.label(
                        "We will subscribe to the ASSET_BROADCAST topic so we can be notified of incoming new assets."
                    )

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button("Show code", on_click=lambda: show_code(extract_wrapped(broadcast_listener_service))).props("outline")
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, broadcast_listener_service
                            ),
                        )
                        ui.button("Next", on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step("Asset Request"):
                    ui.label(
                        "Any assets requested by clicking on the asset data will be put into ASSET_REQUEST topic, so HQ can process and send the asset through the replicated volume."
                    )

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button("Show code", on_click=lambda: show_code(extract_wrapped(asset_request_service))).props("outline")
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, asset_request_service
                            ),
                        )
                        ui.button("Next", on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step("Asset Viewer"):
                    ui.label(
                        "We will periodically mirror the volume where the requested assets are copied."
                    )

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button("Show code", on_click=lambda: show_code(extract_wrapped(asset_viewer_service))).props("outline")
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, asset_viewer_service
                            ),
                        )
                        # ui.button("Next", on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

            # List the broadcasted messages
            with ui.scroll_area().classes("w-full"):
                with ui.list().props('dense').classes("text-xs w-full") as asset_list:
                    ui.item_label('Real-time data feed').classes('text-bold text-sm')
                    for asset in app.storage.general.get("edge_broadcastreceived", []):
                        with ui.item(on_click=lambda e: print(e)).bind_enabled_from(app.storage.general["services"], "stream_replication").classes("text-xs"):
                            with ui.item_section():
                                ui.item_label(asset['title'])
                            with ui.item_section().props('side'):
                                ui.label().bind_text_from(asset, "status")

                ui.timer(0.5, asset_list.update)
            
            # The image display widget to show downloaded assets in real-time
            with ui.scroll_area().classes("w-full"):
                with ui.grid(columns=6).classes("p-1") as images:
                    ui.timer(0.5, lambda: imageshow(os.environ['EDGE_IP'], "edgeimages"))

