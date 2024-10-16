import logging
from nicegui import app, ui, observables
from dashboard import *
from edge_services import *
from functions import *

from helpers import *
from common import *

dashboard = Dashboard()
logger = logging.getLogger(__name__)


@ui.page("/edge_dashboard", title="Edge Dashboard")
def edge_page():
    # Edge Services
    auditlistener_timer = ui.timer(dashboard.auditlistener_delay, lambda: run.io_bound(audit_listener_service,
                                                                                                    host=app.storage.user['EDGE_HOST'],
                                                                                                    clustername=get_cluster_name('EDGE')),
                                                                            active=False)
    upstreamcomm_timer = ui.timer(dashboard.upstreamcomm_delay, lambda: run.io_bound(upstream_comm_service,
                                                                                                  host=app.storage.user['EDGE_HOST'],
                                                                                                  user=app.storage.user['MAPR_USER'],
                                                                                                  password=app.storage.user['MAPR_PASS'],
                                                                                                  messages=dashboard.messages),
                                                                            active=False)
    broadcastlistener_timer = ui.timer(dashboard.broadcastlistener_delay, lambda: run.io_bound(broadcast_listener_service,
                                                                                                            clustername=get_cluster_name('EDGE'),
                                                                                                            dashboard=dashboard),
                                                                            active=False)
    assetrequest_timer = ui.timer(dashboard.assetrequest_delay, lambda: run.io_bound(asset_request_service,
                                                                                                  clustername=get_cluster_name('EDGE'),
                                                                                                  assets=dashboard.assets),
                                                                            active=False)
    assetviewer_timer = ui.timer(dashboard.assetviewer_delay, lambda: run.io_bound(asset_viewer_service,
                                                                                                host=app.storage.user['EDGE_HOST'],
                                                                                                user=app.storage.user['MAPR_USER'],
                                                                                                password=app.storage.user['MAPR_PASS'],
                                                                                                dashboard=dashboard),
                                                                            active=False)

    # Edge Dashboard
    with ui.row().classes("w-full no-wrap place-items-center"):
        ui.label("Edge Dashboard").classes("text-bold ml-2")
        ui.icon("info").tooltip("Edge services simulate an environment where intermittent connectivity and low-bandwidth data transfers are the norm. \
            In such environments, we would like to minimize the data and the overhead, while keeping information relevant and intact. \
            All this communication happens bi-directionally in real-time with lightweight messaging service, Ezmeral Event Store.")

        ui.space()
        ui.switch('Audit Listener').bind_value_to(auditlistener_timer, 'active')
        ui.switch('Upstream Comm').bind_value_to(upstreamcomm_timer, 'active')
        ui.switch('Broadcast Listener').bind_value_to(broadcastlistener_timer, 'active')
        ui.switch('Asset Request').bind_value_to(assetrequest_timer, 'active')
        ui.switch('Asset Viewer').bind_value_to(assetviewer_timer, 'active')

        ui.space()


        # Connectivity indicator
        with ui.row().classes("place-items-center"):
            # Setup stream replication
            ui.button("Replica", on_click=lambda:
                stream_replica_setup(
                    hqhost=app.storage.user["HQ_HOST"],
                    edge_clustername=get_cluster_name("EDGE"),
                    user=app.storage.user["MAPR_USER"],
                    password=app.storage.user["MAPR_PASS"],
                )).classes("py-0 min-h-0").props("flat")
            # Trigger volume mirror
            ui.button("Mirror", on_click=lambda: start_volume_mirroring(edgehost=app.storage.user["EDGE_HOST"], user=app.storage.user["MAPR_USER"], password=app.storage.user["MAPR_PASS"])).classes("py-0 min-h-0").props("flat")
            ui.label().bind_text_from(app.storage.general, "volume_replication")

    with ui.row().classes("w-full no-wrap ml-2"):
        # left panel
        with ui.column().classes("w-fit"):

            # Replication status
            with ui.list().props('bordered separator').classes("text-xs w-full"):
                ui.item_label('HQ Replication Status').props('header').classes('text-bold text-sm bg-primary')
                with ui.item().classes("text-xs m-1 p-2 place-items-center"):
                    ui.item_label().classes("no-wrap").bind_text_from(app.storage.general, "stream_replication")
                with ui.item().classes("m-1 p-1"):
                    ui.button(on_click=toggle_replication).classes("w-full flat secondary").bind_text_from(app.storage.general, "stream_replication", lambda x: "Resume" if x == "PAUSED" else "Pause")

            # Metrics
            with ui.list().props('bordered separator').classes("text-xs w-full"):
                ui.item_label('System Metrics').props('header').classes('text-bold text-sm bg-primary')
                for svc in SERVICES["EDGE"]:
                    service_counter(svc)

        # right panel
        with ui.column().classes("w-full"):

            # List the broadcasted messages
            assets_table = (
                ui.table(
                    title="Published assets",
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
                .on("rowClick", lambda e: make_asset_request(e.args[1]['assetID'], dashboard.assets))
                .props("dense separator=None wrap-cells flat bordered virtual-scroll")
                .classes("w-full")
                .style("height: 300px")
            )

            # Refresh the asset list
            ui.timer(0.5, lambda: assets_table.update_rows(reversed(dashboard.assets), clear_selection=False))

            with ui.grid(columns=5).classes("w-full"):
                # The image display widget to show downloaded assets in real-time
                ui.timer(0.5, lambda: dashboard_tiles(app.storage.user["EDGE_HOST"], dashboard.messages))
                # update metrics
                # ui.timer(0.5, lambda: update_metrics_for("HQ", metric_chart))
