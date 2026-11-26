"""Used by run.bat: exits with code 0 when Streamlit is installed and new enough for the app theme."""
import sys

try:
    import streamlit

    major, minor = (int(x) for x in streamlit.__version__.split(".")[:2])
    sys.exit(0 if (major, minor) >= (1, 50) else 1)
except Exception:
    sys.exit(1)
