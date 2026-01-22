#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.
# Defaults to Mock runner. Uncomment to use Hailo runner when ready.
export USE_HAILO_RUNNER=1 

./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 11434 --reload > server.log 2>&1
