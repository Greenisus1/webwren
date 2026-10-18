#!/usr/bin/env python3
"""Webwren - host a little website from your Pi.

Fullscreen curses UI: create and edit pages, then start/stop a small
static web server with one key. The server is a detached child process
(stdlib http.server), so the site stays up after you close the UI.
Pure stdlib, nothing to set up.

MIT license, copyright Greenisus1. Built with AI assistance from my design.
"""
import curses, json, os, re, signal, subprocess, sys, time
import urllib.request

VERSION = "1.0.0"
APP_DIR = os.environ.get("WEBWREN_HOME", "/root/webwren")
SITE = os.path.join(APP_DIR, "site")
CFG = os.path.join(APP_DIR, "config.json")
PIDFILE = os.path.join(APP_DIR, "server.pid")
LOGFILE = os.path.join(APP_DIR, "server.log")
DEFAULT_PORT = int(os.environ.get("WEBWREN_PORT", "8080"))

TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:sans-serif;max-width:40em;margin:3em auto;line-height:1.5}}</style>
</head><body>
<h1>{title}</h1>
<p>Replace this with your content.</p>
</body></html>
"""

INDEX_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>My Pi site</title>
<style>body{{font-family:sans-serif;max-width:40em;margin:3em auto;line-height:1.5}}</style>
</head><body>
<h1>My Pi site</h1>
<p>It works - this Pi is hosting a website.</p>
</body></html>
"""


def load_cfg():
    try:
        return json.load(open(CFG))
    except Exception:
        return {"port": DEFAULT_PORT}


def save_cfg(cfg):
    os.makedirs(APP_DIR, exist_ok=True)
    json.dump(cfg, open(CFG, "w"))


def ensure_site():
    os.makedirs(SITE, exist_ok=True)
    if not os.path.exists(os.path.join(SITE, "index.html")):
        open(os.path.join(SITE, "index.html"), "w").write(INDEX_TEMPLATE)


def pages():
    if not os.path.isdir(SITE):
        return []
    return sorted(f for f in os.listdir(SITE)
                  if f.endswith((".html", ".htm", ".txt", ".md", ".css")))


def page_path(name):
    name = os.path.basename(name)  # no path escapes
    return os.path.join(SITE, name)


def new_page(name):
    path = page_path(name)
    if os.path.exists(path):
        return False
    title = re.sub(r"\.(html?|txt|md|css)$", "", name).replace("-", " ").title()
    open(path, "w").write(TEMPLATE.format(title=title))
    return True


def server_pid():
    try:
        pid = int(open(PIDFILE).read().strip())
        os.kill(pid, 0)
        with open(f"/proc/{pid}/cmdline", "rb") as fh:
            if b"--serve" in fh.read():
                return pid
    except Exception:
        pass
    return None


def start_server(port):
    if server_pid():
        return False, "already running"
    log = open(LOGFILE, "ab")
    p = subprocess.Popen([sys.executable, os.path.abspath(__file__),
                          "--serve", str(port), SITE],
                         stdout=log, stderr=subprocess.STDOUT,
                         start_new_session=True)
    open(PIDFILE, "w").write(str(p.pid))
    time.sleep(0.4)
    if p.poll() is not None:
        return False, "server died on start - see server.log"
    return True, p.pid


def stop_server():
    pid = server_pid()
    if not pid:
        return False
    os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        try:
            os.kill(pid, 0)
            time.sleep(0.1)
        except ProcessLookupError:
            break
    try:
        os.remove(PIDFILE)
    except OSError:
        pass
    return True


def lan_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def serve(port, root):
    """Child-process entry: run the static file server."""
    import http.server
    handler = functools_partial(root)
    http.server.ThreadingHTTPServer(("0.0.0.0", port), handler).serve_forever()


def functools_partial(root):
    import functools, http.server
    return functools.partial(http.server.SimpleHTTPRequestHandler,
                             directory=root)


class Editor:
    def __init__(self, text):
        self.lines = text.split("\n") if text else [""]
        self.y = self.x = 0

    def key(self, ch):
        line = self.lines[self.y]
        if ch == curses.KEY_UP:
            self.y = max(0, self.y - 1)
        elif ch == curses.KEY_DOWN:
            self.y = min(len(self.lines) - 1, self.y + 1)
        elif ch == curses.KEY_LEFT:
            if self.x > 0:
                self.x -= 1
            elif self.y > 0:
                self.y -= 1
                self.x = len(self.lines[self.y])
        elif ch == curses.KEY_RIGHT:
            if self.x < len(line):
                self.x += 1
            elif self.y < len(self.lines) - 1:
                self.y += 1
                self.x = 0
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            if self.x > 0:
                self.lines[self.y] = line[:self.x - 1] + line[self.x:]
                self.x -= 1
            elif self.y > 0:
                prev = self.lines[self.y - 1]
                self.lines[self.y - 1] = prev + line
                del self.lines[self.y]
                self.y -= 1
                self.x = len(prev)
        elif ch in (10, 13):
            self.lines[self.y] = line[:self.x]
            self.lines.insert(self.y + 1, line[self.x:])
            self.y += 1
            self.x = 0
        elif 32 <= ch < 127:
            self.lines[self.y] = line[:self.x] + chr(ch) + line[self.x:]
            self.x += 1
        self.x = min(self.x, len(self.lines[self.y]))

    def text(self):
        return "\n".join(self.lines)


# ---------- UI ----------

def header(scr, w, sub):
    scr.addnstr(0, 0, f" WEBWREN v{VERSION} - {sub}".ljust(w - 1), w - 1,
                curses.A_REVERSE)


def keys(scr, h, w, s):
    scr.addnstr(h - 1, 0, s[:w - 1], w - 1, curses.A_REVERSE)


def prompt(scr, label):
    curses.echo()
    curses.curs_set(1)
    h, w = scr.getmaxyx()
    scr.addnstr(h - 3, 2, label + " ", w - 4, curses.A_BOLD)
    scr.refresh()
    try:
        v = scr.getstr(h - 3, 2 + len(label) + 1, 200).decode().strip()
    except Exception:
        v = ""
    curses.noecho()
    curses.curs_set(0)
    return v


def edit_page(scr, name):
    path = page_path(name)
    try:
        ed = Editor(open(path).read())
    except Exception:
        return "cannot read page"
    curses.curs_set(1)
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        header(scr, w, f"editing: {name[:w - 26]}")
        top = max(0, ed.y - (h - 5))
        for row, line in enumerate(ed.lines[top:top + h - 4]):
            scr.addnstr(2 + row, 2, line, w - 4)
        keys(scr, h, w, "type to edit - [esc] save and close")
        scr.move(2 + ed.y - top, min(2 + ed.x, w - 2))
        scr.refresh()
        ch = scr.getch()
        if ch == 27:
            open(path, "w").write(ed.text().rstrip("\n") + "\n")
            curses.curs_set(0)
            return "saved"
        ed.key(ch)


def view_log(scr):
    try:
        lines = open(LOGFILE, errors="replace").read().splitlines()[-200:]
    except Exception:
        lines = ["(no log yet)"]
    top = max(0, len(lines) - 10)
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        header(scr, w, "server log")
        body = h - 3
        top = max(0, min(top, len(lines) - body))
        for row, line in enumerate(lines[top:top + body]):
            scr.addnstr(2 + row, 2, line, w - 4)
        keys(scr, h, w, "[j/k] scroll  [q] back")
        scr.refresh()
        ch = scr.getch()
        if ch in (curses.KEY_UP, ord("k")):
            top = max(0, top - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            top = min(max(0, len(lines) - body), top + 1)
        elif ch in (ord("q"), 27):
            return


def main(scr):
    curses.curs_set(0)
    ensure_site()
    cfg = load_cfg()
    sel, msg = 0, ""
    while True:
        scr.erase()
        h, w = scr.getmaxyx()
        pid = server_pid()
        header(scr, w, "your website")
        state = f"SERVING on port {cfg['port']} (pid {pid})" if pid else "stopped"
        scr.addnstr(2, 2, f"Server:  {state}", w - 4,
                    curses.A_BOLD if pid else 0)
        if pid:
            scr.addnstr(3, 2, f"Address: http://{lan_ip()}:{cfg['port']}/",
                        w - 4)
        scr.addnstr(4, 2, f"Site:    {SITE}", w - 4)
        pg = pages()
        scr.addnstr(6, 2, f"Pages ({len(pg)}):", w - 4, curses.A_BOLD)
        body = h - 10
        for row, name in enumerate(pg[:body]):
            attr = curses.A_REVERSE if row == sel else 0
            scr.addnstr(7 + row, 4, name.ljust(w - 8), w - 8, attr)
        if msg:
            scr.addnstr(h - 2, 2, msg, w - 4, curses.A_BOLD)
        keys(scr, h, w, "[s]tart/stop server  [e]dit  [a]dd page  "
                        "[d]elete  [p]ort  [l]og  [q]uit")
        scr.refresh()
        ch = scr.getch()
        msg = ""
        if ch in (curses.KEY_UP, ord("k")):
            sel = max(0, sel - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            sel = min(max(0, len(pg) - 1), sel + 1)
        elif ch == ord("s"):
            if pid:
                msg = "Server stopped." if stop_server() else "not running"
            else:
                ok, info = start_server(cfg["port"])
                msg = f"Serving on port {cfg['port']}." if ok else f"Start failed: {info}"
        elif ch == ord("e") and pg:
            msg = edit_page(scr, pg[sel])
        elif ch == ord("a"):
            name = prompt(scr, "New page filename (e.g. about.html):")
            if name:
                msg = "Created." if new_page(name) else "That file exists."
        elif ch == ord("d") and pg:
            os.remove(page_path(pg[sel]))
            sel = max(0, sel - 1)
            msg = "Deleted."
        elif ch == ord("p"):
            v = prompt(scr, f"Port [{cfg['port']}] (blank keeps):")
            if v.isdigit() and 1 <= int(v) <= 65535:
                cfg["port"] = int(v)
                save_cfg(cfg)
                msg = "Port saved - restart the server to apply."
        elif ch == ord("l"):
            view_log(scr)
        elif ch in (ord("q"), 27):
            return


if __name__ == "__main__":
    if "--serve" in sys.argv:
        i = sys.argv.index("--serve")
        serve(int(sys.argv[i + 1]), sys.argv[i + 2])
        sys.exit(0)
    curses.wrapper(main)
