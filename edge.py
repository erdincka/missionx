from nicegui import app, ui
import inspect
from edge_services import asset_request_service, asset_viewer_service, broadcast_listener_service, make_asset_request, upstream_comm_service
from functions import *

from helpers import *

def edge_page():
    # Edge Dashboard
    with ui.row().classes("w-full"):
        ui.label("Edge Dashboard").classes("text-bold")

    with ui.row().classes("w-full place-items-center sticky top-28 bg-slate-100 dark:bg-slate-700 p-3"):
        ui.label("Edge").classes("text-bold")

        ui.label().bind_text_from(app.storage.general, "stream_replication")

        ui.space()

        for svc in SERVICES["EDGE"]:
            service_status(svc)
            ui.space()

        with ui.row().classes("place-items-center"):
            ui.button("Mirror", on_click=mirror_volume)
            ui.label().bind_text_from(app.storage.general, "volume_replication")

    ui.label("Edge services simulate an environment where intermittent connectivity and low-bandwidth data transfers are the norm. \
                In such environments, we would like to minimize the data and the overhead, while keeping information relevant and intact. \
                All this communication happens bi-directionally in real-time with lightweight messaging service, Ezmeral Event Store.")

    with ui.stepper().classes("w-full").props("vertical") as stepper:
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

