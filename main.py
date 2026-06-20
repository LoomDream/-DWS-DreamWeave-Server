from __future__ import annotations

import uvicorn

from network.config import load_config
from network.api import create_app


def main() -> None:
    config = load_config()
    uvicorn.run(
        create_app(config),
        host=config.server.host,
        port=config.server.port,
    )


if __name__ == "__main__":
    main()
