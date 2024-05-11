from nicegui import app, ui
from edge_services import make_asset_request
from functions import *

from helpers import *
import steps

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
            ui.button("Mirror", on_click=mirror_volume).classes("py-0 min-h-1").props("flat")
            ui.label().bind_text_from(app.storage.general, "volume_replication")

    with ui.row().classes("w-full no-wrap ml-2"):
        # left panel
        with ui.column().classes("w-fit"):

            with ui.list().props('bordered separator').classes("text-xs w-full"):
                ui.item_label('HQ Replication Status').props('header').classes('text-bold text-sm bg-primary')
                with ui.item().classes("text-xs m-1 p-2 place-items-center"):
                    ui.item_label().classes("no-wrap").bind_text_from(app.storage.general, "stream_replication")
                with ui.item().classes("m-1 p-1"):
                    ui.button(on_click=toggle_replication).classes("w-full flat secondary").bind_text_from(app.storage.general, "stream_replication", lambda x: "Resume" if x == "PAUSED" else "Pause")


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
                for step in steps.FLOW["EDGE"]:
                    with ui.step(step.get('title',"")):
                        ui.label(step.get('description', ""))
                        with ui.stepper_navigation():
                            ui.button("Code", on_click=lambda s=step: show_code(s.get("code", ""))).props("outline")
                            ui.button(
                                "Start",
                                on_click=lambda s=step: asyncio.get_event_loop().run_in_executor(
                                    None, s.get("function", None)
                                ),
                            )
                            ui.button('Next', on_click=stepper.next, color="secondary")
                            ui.button('Back', on_click=stepper.previous, color="none")

            # List the broadcasted messages
            ui.label("Available Assets")
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
                    app.storage.general.get("broadcastreceived", [])
                ),
            )


            # The image display widget to show downloaded assets in real-time
            with ui.grid(columns=5).classes("p-1") as images:
                ui.timer(0.5, lambda: dashboard_tiles(os.environ['EDGE_IP'], "dashboard_edge"))

