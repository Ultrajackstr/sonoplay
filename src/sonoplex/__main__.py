"""Entry point for python -m sonoplex."""

import sys


def main():
    """Start the Sonoplex server."""
    # Configure logging first using new module
    from sonoplex.core.logging import configure_logging
    configure_logging()
    
    # Import and start - still uses old plexserver for now
    # Full migration in future phase
    from plex.plexserver import start_plex_server
    start_plex_server()


if __name__ == "__main__":
    sys.exit(main() or 0)
