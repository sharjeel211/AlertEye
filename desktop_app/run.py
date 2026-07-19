"""
Quick launcher — runs AlertEye in standalone mode (no login required).
Use this to test detection without the web portal running.
"""
import sys
sys.argv.append("--standalone")

import main
main.main()
