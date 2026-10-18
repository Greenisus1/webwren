"""PTY walkthrough: boot, add page, start server, fetch it over HTTP, stop, quit."""
import json, os, pty, re, select, sys, tempfile, time, urllib.request

home = tempfile.mkdtemp()
env = dict(os.environ, WEBWREN_HOME=home, WEBWREN_PORT="18098",
           TERM="xterm-256color", LINES="30", COLUMNS="100")
pid, fd = pty.fork()
if pid == 0:
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    os.execvpe(sys.executable, [sys.executable, "webwren.py"], env)

out = b""
def pump(t):
    global out
    end = time.time() + t
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try: out += os.read(fd, 65536)
            except OSError: break

fail = []
pump(2.0)
if not re.search(rb"WEBWREN v1\.0\.0", out): fail.append("title")
if not re.search(rb"index\.html", out): fail.append("default page listed")
os.write(fd, b"a"); pump(0.6)
os.write(fd, b"about.html\n"); pump(0.8)
if not re.search(rb"about\.html", out): fail.append("page added")
os.write(fd, b"s"); pump(1.5)          # start server
if not re.search(rb"SERVING on port 18098", out): fail.append("serving state")
try:
    body = urllib.request.urlopen("http://127.0.0.1:18098/about.html",
                                  timeout=5).read().decode()
    if "<h1>About</h1>" not in body: fail.append("http body")
except Exception as e:
    fail.append(f"http fetch: {e}")
os.write(fd, b"s"); pump(1.5)          # stop
try:
    urllib.request.urlopen("http://127.0.0.1:18098/", timeout=2)
    fail.append("server still up after stop")
except Exception:
    pass
os.write(fd, b"q"); pump(0.8)
wp, _ = os.waitpid(pid, os.WNOHANG)
if wp == 0:
    try: os.kill(pid, 9); os.waitpid(pid, 0)
    except ProcessLookupError: pass
    fail.append("did not quit")
if fail:
    print("PTY FAIL:", ", ".join(fail)); sys.exit(1)
print("PTY PASS")
