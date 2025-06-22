#!/usr/bin/env bash

# [ -d /app ] || git clone https://github.com/erdincka/catchx.git /app

# cd /app

. $HOME/.local/bin/env
unset VIRTUAL_ENV
# uv init --app --name core-edge --description "Core to Edge Pipelines with Data Fabric" --author-from git
# uv add nicegui 'protobuf==3.20.*' requests importlib_resources
# uv pip install ./maprdb_python_client-1.1.7-py3-none-any.whl
uv run main.py

# don't exit when service dies.
# sleep infinity
