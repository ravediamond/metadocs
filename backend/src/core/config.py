import os

# Configuration flag
SYSTEM_MODE = os.getenv(
    "SYSTEM_MODE", "open_source"
)  # Options: 'open_source', 'saas', 'commercial'
