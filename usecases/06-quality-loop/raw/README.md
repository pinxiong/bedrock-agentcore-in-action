# raw/ · boto3 sidecar (uc06)

Not part of the deployment. Nothing here is imported by `app/aia_uc06/`
and nothing here is packaged by `agentcore deploy`. It exists so a reader can see
what the CLI did for them.

| Script | Client | What it shows |
|---|---|---|
| `control_plane.py` | `bedrock-agentcore-control` | list and read back the resources `agentcore` just created |
| `data_plane.py` | `bedrock-agentcore` | call `invoke_agent_runtime` directly and print the raw SSE stream |

Both scripts are optional. If you do not write them, delete this directory:
the independence check only requires what the use case needs in order to run.
