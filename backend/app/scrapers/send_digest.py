"""Send the weekly fuel price digest.

Invoked by:
  - Manual:    python -m app.scrapers.send_digest
  - Cron:      GitHub Actions weekly (see .github/workflows/digest.yml)
"""
from __future__ import annotations

import logging

from app.db import migrate
from app.services.digest import send_weekly_digest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


if __name__ == "__main__":
    migrate.run()
    sent = send_weekly_digest()
    log.info("digest complete: sent=%d", sent)
