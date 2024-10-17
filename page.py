import io
import json
from fastapi.responses import StreamingResponse
import httpx
from nicegui import ui, app

from documentation import Help
from functions import *
from hq import hq_page

from sites import *

logger = logging.getLogger(__name__)

ui.add_head_html('<link href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.6.0/css/fontawesome.min.css" rel="stylesheet">', shared=True)
ui.add_body_html('<script src="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.6.0/js/all.min.js" integrity="sha256-qq1ob4lpAizCQs1tkv5gttMXUlgpiHyvG3JcCIktRvs=" crossorigin="anonymous"></script>', shared=True)

@ui.page('/')
async def index():
    if "tile_remove" not in app.storage.general.keys(): app.storage.general["tile_remove"] = 20

    # Header
    header(title=TITLE)

    hq_page()
    # with ui.splitter(limits=(25,75)) as site_panels:
    #     with site_panels.before:
    #         hq_page()
    #     with site_panels.after:
    #         edge_page()

    # ui.separator()

    logging_card().classes(
        "flex-grow shrink absolute sticky bottom-0 left-0 w-full opacity-50 hover:opacity-100"
    )

    footer()


def header(title: str):

    help = Help().props("full-width")

    with ui.header(elevated=True).classes("items-center justify-between uppercase py-1 px-4") as header:
        ui.button(icon="home", on_click=lambda: ui.navigate.to(index)).props("flat color=light")

        ui.label(title)

        ui.space()
        ui.button("Help", icon="help", on_click=help.open).props("flat color=light")
        ui.switch("Logs").props("checked-icon=check unchecked-icon=clear").bind_value(app.storage.user, 'demo_mode').bind_visibility_from(app.storage.user, HQ, backward=lambda x: x and len(x) > 0)
        ui.space()

        with ui.row().classes("place-items-center"):
            # HQ MCS link
            ui.link(
                target=f"https://{app.storage.user.get('MAPR_USER', '')}:{app.storage.user.get('MAPR_PASS', '')}@{app.storage.user.get('HQ_HOST', '')}:8443/app/mcs/",
                new_tab=True
            ).classes(
                "text-white hover:text-blue-600"
            ).bind_text_from(app.storage.user, HQ, backward=lambda x: x["name"] if x else "No HQ Cluster"
            ).bind_visibility_from(app.storage.user, HQ, backward=lambda x: x and len(x) > 0)

            # EDGE MCS link
            ui.link(
                target=f"https://{app.storage.user.get('MAPR_USER', '')}:{app.storage.user.get('MAPR_PASS', '')}@{app.storage.user.get('EDGE_HOST', '')}:8443/app/mcs/",
                new_tab=True
            ).classes(
                "text-white hover:text-blue-600"
            ).bind_text_from(app.storage.user, EDGE, backward=lambda x: x["name"] if x else "No HQ Cluster"
            ).bind_visibility_from(app.storage.user, EDGE, backward=lambda x: x and len(x) > 0)

            # Connect to a cluster
            # ui.label("Not configured!").classes("text-bold red").bind_visibility_from(app.storage.user, "cluster", backward=lambda x: not x or len(x) == 0)
            ui.button(icon="link" if "configured" in app.storage.user.keys() and app.storage.user["configured"] else "link_off", on_click=cluster_connect).props("flat color=light")

            ui.button(icon="settings", on_click=demo_configuration_dialog).props(
                "flat color=light"
            )

            ui.icon("error", size="2em", color="red").bind_visibility_from(
                app.storage.user, "configured", lambda x: not x
            ).tooltip("Requires configuration!")

    return header


def footer():
    with ui.footer().classes("py-1 px-4") as footer:
        with ui.row().classes("w-full items-center"):

            # Endpoints
            ui.label("Volumes:")

            with ui.button_group().props("flat color=dark"):
                # GNS
                ui.button(
                    "GNS",
                    on_click=lambda: run_command_with_dialog(
                        f"df -h {MOUNT_PATH}; tree -L 2 {MOUNT_PATH}"
                    ),
                )
                # Core
                ui.button(
                    HQ,
                    on_click=lambda: run_command_with_dialog(
                        f"ls -lAR {MOUNT_PATH}/{HQSite['clusterName']}{HQ_VOLUME_PATH}"
                    ),
                )
                # Edge
                EdgeSite["clusterName"] = get_cluster_name("EDGE")
                ui.button(
                    EDGE,
                    on_click=lambda: run_command_with_dialog(
                        f"ls -lAR {MOUNT_PATH}/{EdgeSite['clusterName']}{EDGE_VOLUME_PATH}"
                    ),
                )

            ui.space()

            # Github link
            with ui.link(
                target=DEMO["link"],
                new_tab=True,
            ).classes(
                "place-items-center"
            ):
                ui.html("""
                <div id="c40" class="fill-white scale-125 m-1"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"></path></svg>
                </div>
                """)

    return footer


def cluster_connect():
    # with ui.dialog().props("full-width") as cluster_connect_dialog, ui.card():
    with ui.dialog() as cluster_connect_dialog, ui.card().classes("w-full place-items-center"):
        with ui.row().classes("w-full place-items-center"):
            with ui.grid(columns=2).classes("flex-grow"):
                ui.input("HQ Node").classes("flex-grow").bind_value(app.storage.user, "HQ_HOST")
                ui.input("Edge Node").classes("flex-grow").bind_value(app.storage.user, "EDGE_HOST")
            with ui.grid(columns=2).classes("flex-grow"):
                ui.input("Username").classes("flex-grow").bind_value(app.storage.user, "MAPR_USER")
                ui.input("Password", password=True, password_toggle_button=True).classes("flex-grow").bind_value(app.storage.user, "MAPR_PASS")
        ui.button("Configure & create...", icon="rocket_launch", on_click=run_configuration_steps).tooltip("Configures maprclient and creates volumes, streams and tables required for the demo")

        ui.separator()

        with ui.grid(columns=2):
            for step in cluster_configuration_steps:
                # ui.label(step["name"])
                ui.label(step["info"])
                ui.icon("", size='sm', color="info").bind_name_from(step, "status").classes("justify-self-end")

    cluster_connect_dialog.open()


async def run_configuration_steps():

    logger.info("Connecting to HQ node %s...", app.storage.user['HQ_HOST'])
    for step in cluster_configuration_steps:
        # Step 1 - Get cluster information
        if step["name"] == "clusterinfo":
            step["status"] = "run_circle"

            for cluster in HQ, EDGE: # update app.storage with both cluster's clusterinfo
                try:
                    auth = (app.storage.user["MAPR_USER"], app.storage.user["MAPR_PASS"])
                    URL = f"https://{app.storage.user[cluster + '_HOST']}:8443/rest/dashboard/info"

                    async with httpx.AsyncClient(verify=False) as client:
                        response = await client.get(URL, auth=auth)

                        # logger.debug(response.text)

                        if response is None or response.status_code != 200:
                            logger.warning("Response: %s", response.text)
                            step["status"] = "error"

                        else:
                            res = response.json()
                            # logger.debug("Got dashboard data: %s", json.dumps(res))
                            # Set cluster information
                            app.storage.user[cluster] = res["data"][0]["cluster"]

                except Exception as error:
                    logger.error("Failed to connect to cluster.")
                    logger.info(error)
                    step["status"] = "error"

            step["status"] = "check"

        # Step 2 - Configure cluster
        elif step["name"] == "reconfigure":
            step["status"] = "run_circle"

            # Run configuration for client only on HQ
            os.environ["CLUSTER_IP"] = app.storage.user[HQ]["ip"]
            os.environ["CLUSTER_NAME"] = app.storage.user[HQ]["name"]
            os.environ["MAPR_USER"] = app.storage.user["MAPR_USER"]
            os.environ["MAPR_PASS"] = app.storage.user["MAPR_PASS"]
            async for out in run_command("/bin/bash ./configure-maprclient.sh"):
                logger.info(out.strip())

            step["status"] = "check"

        # Step 3 - Create volumes and streams
        elif step["name"] == "createvolumes":
            step["status"] = "run_circle"
            if await create_volumes(app.storage.user["HQ_HOST"], [HQ_VOLUME_PATH, HQ_MISSION_FILES]) \
                and await create_tables(app.storage.user["HQ_HOST"], [HQ_IMAGETABLE]) \
                and await create_streams(app.storage.user["HQ_HOST"], [f"{HQ_VOLUME_PATH}/{STREAM_PIPELINE}", f"{HQ_STREAM_REPLICATED}"]) \
                and await create_volumes(app.storage.user["EDGE_HOST"], [EDGE_VOLUME_PATH]) \
                and await create_mirror_volume(HQSite['clusterName'], app.storage.user["EDGE_HOST"], HQ_MISSION_FILES, EDGE_MISSION_FILES):
                # These should be created later on demo steps
                # and await create_streams(app.storage.user["EDGE_HOST"],[f"{EDGE_VOLUME_PATH}/{EDGE_STREAM_REPLICATED}"]):
                # and await create_tables(app.storage.user["EDGE_HOST"], []) \
                step["status"] = "check"
            else: step["status"] = "error"

        # Step 4 - Enable auditing
        elif step["name"] == "auditing":
            step["status"] = "run_circle"
            for cluster in HQ, EDGE: # enable auditing on both clusters
                try:
                    auth = (app.storage.user["MAPR_USER"], app.storage.user["MAPR_PASS"])
                    auditdata = {"mfs.enable.audit.as.stream":"1"}

                    for URL in [f"https://{app.storage.user[cluster + '_HOST']}:8443/rest/audit/cluster?enabled=true",
                                f"https://{app.storage.user[cluster + '_HOST']}:8443/rest/audit/data?enabled=true",
                                f"https://{app.storage.user[cluster + '_HOST']}:8443/rest/config/save",
                                ]:
                        async with httpx.AsyncClient(verify=False) as client:
                            response = await client.post(URL, auth=auth, data={"values" : auditdata} if "config/save" in URL else None)
                            # logger.debug(response.text)

                            if response is None or response.status_code != 200:
                                logger.warning("Response: %s", response.text)
                                step["status"] = "error"

                            else:
                                res = response.json()
                                logger.debug(f"Set cluster audit resulted with: {res}")

                except Exception as error:
                    logger.error("Failed to enable auditing.")
                    logger.info(error)
                    step["status"] = "error"

            step["status"] = "check"

        else: logger.debug("%s not defined", step["name"])

    # mark configured
    app.storage.user["configured"] = True


def demo_configuration_dialog():
    with ui.dialog().props("position=right full-height") as dialog, ui.card().classes("relative bordered"):
        # with close button
        ui.button(icon="close", on_click=dialog.close).props("flat round dense").classes("absolute right-2 top-2")

        # save/restore the configuration
        with ui.row():
            ui.button(icon="download", on_click=config_show().open)
            ui.button(icon="upload", on_click=config_load().open)

        with ui.card_section():
            ui.label("Mount Path").classes("text-lg w-full")
            ui.label("to Global Namespace")
            with ui.row().classes("w-full place-items-center mt-4"):
                ui.button("List cluster root", on_click=lambda: run_command_with_dialog(f"ls -lA /mapr")).bind_enabled_from(app.storage.user, "busy", backward=lambda x: not x)
                ui.button("Remount", on_click=lambda: run_command_with_dialog(f"([ -d /mapr ] && umount -l /mapr) || mkdir /mapr; mount -t nfs4 -o nolock,soft {app.storage.user.get('HQ_HOST', '127.0.0.1')}:/mapr /mapr")).bind_enabled_from(app.storage.user, "busy", backward=lambda x: not x)
                # ui.button("Volumes", on_click=create_volumes).bind_enabled_from(app.storage.user, "busy", backward=lambda x: not x)
                # ui.button("Streams", on_click=create_streams).bind_enabled_from(app.storage.user, "busy", backward=lambda x: not x)
                # ui.button("Tables", on_click=create_tables).bind_enabled_from(app.storage.user, "busy", backward=lambda x: not x)

        ui.separator()
        with ui.card_section():
            ui.label("Clean up!").classes("text-lg")
            ui.label("Use when done with the demo. This will remove all volumes and streams, ALL DATA will be gone!").classes("text-sm text-italic")
            ui.button("DELETE ALL!", on_click=delete_volumes, color="negative").classes("mt-4").bind_enabled_from(app.storage.user, "busy", backward=lambda x: not x)

    dialog.on("close", lambda d=dialog: d.delete())
    dialog.open()


def config_show():
    with ui.dialog() as config_show, ui.card().classes("grow"):
        ui.code(json.dumps(app.storage.user, indent=2), language="json").classes("w-full text-wrap")
        with ui.row().classes("w-full"):
            ui.button(
                "Save",
                icon="save",
                on_click=lambda: ui.download("/config"),
            )
            ui.space()
            ui.button(
                "Close",
                icon="cancel",
                on_click=config_show.close,
            )
    return config_show


def config_load():
    with ui.dialog() as config_load, ui.card().classes("grow"):
        ui.upload(label="Config JSON", auto_upload=True, on_upload=lambda e: config_save(e.content.read().decode("utf-8"), config_load)).classes(
            "max-w-full"
        ).props("accept='application/json' hide-upload-btn")

    return config_load


def config_save(val: str, dialog):
    try:
        for key, value in json.loads(val.replace("\n", "")).items():
            app.storage.user[key] = value
        dialog.close()
        ui.notify("Settings loaded", type="positive")
        ui.notify("Refresh the page!!", type="error")
    except (TypeError, json.decoder.JSONDecodeError, ValueError) as error:
        ui.notify("Not a valid json", type="negative")
        logger.warning(error)


@app.get("/config")
def download(content: str = None):
    # by default downloading settings
    if content is None:
        content = app.storage.user

    string_io = io.StringIO(json.dumps(content))  # create a file-like object from the string

    headers = {"Content-Disposition": "attachment; filename=config.json"}
    return StreamingResponse(string_io, media_type="text/plain", headers=headers)
