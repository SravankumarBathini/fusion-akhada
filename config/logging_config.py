"""Application logging defaults for local and hosted Streamlit runs."""

import logging


def configure_logging() -> None:
    """Configure one concise, timestamped diagnostic stream."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=False,
    )
