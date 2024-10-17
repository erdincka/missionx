import inspect
import importlib_resources
from nicegui import ui, app

from common import *
from functions import *

class Help(ui.dialog):
    def __init__(self) -> None:
        super().__init__()
        with self, ui.card().classes("w-full place-items-center grow"):
            with ui.expansion(
                TITLE,
                icon="info",
                caption="Core to Edge end to end pipeline processing using Ezmeral Data Fabric",
                group="help",
            ).classes("w-full").classes("text-bold"):
                ui.markdown(DEMO["description"]).classes("font-normal")
                ui.image(importlib_resources.files("main").joinpath(DEMO["image"])).classes(
                    "object-scale-down g-10"
                )

            ui.separator()

            # Prepare
            with ui.expansion("Demo Preparations", icon="engineering", caption="Need to create volumes and streams before demo", group="help").classes("w-full text-bold"):

                ui.label("Create the volumes, topics and tables at the HQ cluster.")

                ui.code(inspect.getsource(prepare_core)).classes("w-full")

                ui.button("Run", on_click=lambda: run_command_with_dialog(prepare_core()))

                ui.space()

                ui.label("Create the volumes at the Edge cluster.")

                ui.code(inspect.getsource(prepare_edge)).classes("w-full")

                ui.button("Run", on_click=lambda: run_command_with_dialog(prepare_edge()))

                ui.space()

                ui.label("We need to establish bi-directional communication between HQ and Edge. Let's first enable the replication of broadcast stream so we can get intelligence data from HQ.")

                ui.code(inspect.getsource(stream_replica_setup)).classes("w-full")

                ui.button("Run", on_click=lambda:
                        stream_replica_setup(
                            hqhost=app.storage.user["HQ_HOST"],
                            user=app.storage.user["MAPR_USER"],
                            password=app.storage.user["MAPR_PASS"],
                        ))

            ui.separator()

            ui.button('Close', on_click=self.close)
