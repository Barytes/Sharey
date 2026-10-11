"""Explicit opt-in process interruption gates for the acceptance runner."""

import json
import os
import threading
from pathlib import Path


def pause_for_test(stage: str, key: str) -> None:
    directory = os.environ.get("SHAREY_TEST_FAULT_DIR")
    if (
        not directory
        or os.environ.get("SHAREY_TEST_PAUSE_STAGE") != stage
        or os.environ.get("SHAREY_TEST_PAUSE_KEY") != key
    ):
        return
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    temporary = root / f"{stage}.pending"
    temporary.write_text(json.dumps({"stage": stage, "pid": os.getpid()}))
    temporary.replace(root / f"{stage}.json")
    threading.Event().wait()
