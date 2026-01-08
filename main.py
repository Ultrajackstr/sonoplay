from logging_config import configure_logging

configure_logging()

from plex.plexserver import start_plex_server

if __name__ == "__main__":
    start_plex_server()
