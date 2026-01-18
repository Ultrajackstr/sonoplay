"""Version and startup banner for SonoPlex Player."""

VERSION = "1.1.2"
LICENSE = "GPL-3.0"
PRODUCT = "SonoPlex Player"


def print_banner() -> None:
    """Print the startup banner with product name, version, and license."""
    version_str = f"v{VERSION}"
    
    # Build the version/license line, centered in the box
    info_line = f"Version: {version_str}          License: {LICENSE}"
    
    banner = f"""
╔══════════════════════════════════════════════════════╗
║   ____                    ____  _                    ║
║  / ___|  ___  _ __   ___ |  _ \\| | _____  __         ║
║  \\___ \\ / _ \\| '_ \\ / _ \\| |_) | |/ _ \\ \\/ /         ║
║   ___) | (_) | | | | (_) |  __/| |  __/>  <          ║
║  |____/ \\___/|_| |_|\\___/|_|   |_|\\___/_/\\_\\         ║
║                                                      ║
║  {info_line:<52}║
╚══════════════════════════════════════════════════════╝
"""
    print(banner)
