# Webwren

Host a little website from your Pi. Fullscreen terminal UI to create and
edit pages, then start or stop the built-in static web server with one
key. Pure Python standard library - no Docker, no nginx, nothing to set
up. Great for a personal page, a diary, or a landing page for your
Minecraft server.

## What it does

- **One key serving** (`s`): starts a small web server on your chosen
  port (default 8080) and shows the address to visit
  (http://your-pi:8080/). The server is a detached process, so the site
  stays up when you close the app. `s` again stops it.
- **Pages**: add (`a`), edit (`e`, built-in fullscreen editor), delete
  (`d`). A starter index.html is created for you.
- **Request log** (`l`): tail the server's access log in-app.
- **Port** (`p`): change the listen port; it persists.

## Install (Pi App Store)

Install through the Pi App Store, or:

```sh
sudo bash app-store.sh install   # checks Python/curses, compiles sources
sudo python3 webwren.py          # or: bash app-store.sh run
sudo bash app-store.sh stop      # stop the server from outside the UI
```

Site files live in `/root/webwren/site/` (override the base with the
`WEBWREN_HOME` environment variable, port default with `WEBWREN_PORT`).
The server listens on all interfaces - that is the point of hosting a
site, but be aware anything in the site folder is public on your network.

## Tests

```sh
python3 test_webwren.py   # unit tests (pages, path safety, live HTTP serve)
python3 test_pty.py       # fullscreen walkthrough incl. real HTTP fetch
```

MIT license, copyright Greenisus1. Built with AI assistance from my design.
