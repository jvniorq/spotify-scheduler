from __future__ import annotations

import os
import time

from .app import create_app
from .config import WebSettings

settings = WebSettings.from_env()
os.environ["TZ"] = settings.timezone
if hasattr(time, "tzset"):
    time.tzset()

app = create_app(settings)
