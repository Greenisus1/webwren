#!/bin/bash
# pi-app-store: 1
# pi-app-store-category: web
# pi-app-store-description: Host a little website from your Pi: create and edit pages in a fullscreen editor, start or stop the built-in web server with one key, watch the request log.
set -eu
cd -- "$(dirname -- "$0")"
ready() { python3 -c 'import curses' >/dev/null 2>&1; }
action=${1:-run}
case "${action,,}" in
 install)
  if ! ready; then
   [ "$(id -u)" -eq 0 ] || { echo 'Install through the Store with sudo to add Python.';exit 1; }
   if command -v apt-get >/dev/null;then apt-get update;apt-get install -y python3
   elif command -v apk >/dev/null;then apk add --no-cache python3
   elif command -v pacman >/dev/null;then echo 'Arch may upgrade the whole system; review pacman prompt.';pacman -Syu --needed python
   else echo 'Install Python 3 with curses using your distro tools.';exit 1;fi
  fi
  ready
  python3 -c 'from pathlib import Path;[compile(p.read_bytes(),str(p),"exec") for p in Path(".").glob("*.py")]' ;;
 status) ready ;;
 run) [ "$#" -eq 0 ] || shift;exec python3 webwren.py "$@" ;;
 stop)
  [ -f /root/webwren/server.pid ] && kill "$(cat /root/webwren/server.pid)" 2>/dev/null && rm -f /root/webwren/server.pid && echo 'webwren server stopped' || echo 'webwren server not running' ;;
 *) echo 'Use install, status, run or stop (any casing).';exit 2 ;;
esac
