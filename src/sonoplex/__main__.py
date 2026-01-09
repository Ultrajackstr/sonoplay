"""Entry point for python -m sonoplex."""


def main():
    """Start the Sonoplex server."""
    # Import here to avoid circular imports during package setup
    from logging_config import configure_logging
    configure_logging()
    
    from plex.plexserver import start_plex_server
    start_plex_server()


if __name__ == "__main__":
    main()
