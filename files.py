
import logging
import os
import pathlib
import importlib_resources
import requests

from helpers import *

logger = logging.getLogger()

def putfile(host: str, file: str, destfolder: str, *args, **kwargs):
    """
    PUT request to Admin REST API at /files.
    args and kwargs for requests.put.
    """

    basedir = importlib_resources.files("main")

    filepath = basedir.joinpath(file)
    filename = pathlib.Path(filepath).name
    destination = f"{HQ_VOLUME_PATH}/{destfolder}/{filename}"

    REST_URL = f"https://{host}:8443/files{destination}"

    try:
        with open(filepath, "rb") as f:
            response = requests.put(
                url=REST_URL,
                auth=(os.environ["MAPR_USER"], os.environ["MAPR_PASS"]),
                verify=False,
                data=f,
                timeout=5,
                *args,
                **kwargs
            )
            response.raise_for_status()
            return response

    except Exception as error:
        logger.warning("PUTFILE ERROR %s", error)
        return None


# Get file from destination
def getfile(host: str, filepath: str, *args, **kwargs):
    """
    GET request to Admin REST API at /files.
    args and kwargs for requests.get.
    """

    REST_URL = f"https://{host}:8443/files{filepath}"

    try:
        response = requests.get(
            url=REST_URL,
            auth=(os.environ["MAPR_USER"], os.environ["MAPR_PASS"]),
            verify=False,
            timeout=5,
            *args,
            **kwargs
        )
        response.raise_for_status()
        return response

    except Exception as error:
        logger.warning("GETFILE ERROR %s", error)
        return None

