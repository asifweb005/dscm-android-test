import os, re, subprocess, time

PKG = os.environ.get("PKG", "com.paradox.dscm")
APK_URL = os.environ["APK_URL"]
SESSION_MINUTES = int(os.environ.get("SESSION_MINUTES", "300"))
CHECK_EVERY = int(os.environ.get("CHECK_EVERY", "10"))

def run(cmd):
    print("+", cmd, flush=True)
    return subprocess.run(cmd, shell=True)

def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout

def write(name, text):
    with open(os.path.join("output", name), "a") as f:
        f.write(str(text) + "\n")

def shot(name):
    run("adb exec-out screencap -p > output/" + name)

os.makedirs("output", exist_ok=True)
write("session-log.txt", "START session_minutes=%d check_every=%d" % (SESSION_MINUTES, CHECK_EVERY))
run("curl -L '" + APK_URL + "' -o app.apk")
write("install.txt", sh("ls -l app.apk"))
write("install.txt", sh("adb install -r app.apk"))
run("adb shell monkey -p " + PKG + " -c android.intent.category.LAUNCHER 1")
time.sleep(30)
shot("02-app.png")

run("adb shell uiautomator dump /sdcard/dump.xml")
run("adb pull /sdcard/dump.xml output/dump_last.xml")
xml = ""
try:
    xml = open("output/dump_last.xml").read()
except Exception:
    pass
m = re.search(r'(?:content-desc|text)="[^"]*Continue as guest[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
if m:
    x = (int(m.group(1)) + int(m.group(3))) // 2
    y = (int(m.group(2)) + int(m.group(4))) // 2
    src = "label"
else:
    size = sh("adb shell wm size")
    mm = re.search(r"(\d+)x(\d+)", size)
    w, h = (int(mm.group(1)), int(mm.group(2))) if mm else (1080, 2400)
    x, y = w // 2, int(h * 0.71)
    src = "fallback"
write("session-log.txt", "TAP Continue as guest %d %d %s" % (x, y, src))
run("adb shell input tap %d %d" % (x, y))
time.sleep(10)
shot("03-after-guest.png")

start = time.time()
end = start + SESSION_MINUTES * 60
i = 0
while time.time() < end:
    time.sleep(CHECK_EVERY * 60)
    i += 1
    alive = bool(sh("adb shell pidof " + PKG).strip())
    if alive:
        write("session-log.txt", "check %d ALIVE elapsed_min=%d" % (i, int((time.time() - start) // 60)))
    else:
        write("session-log.txt", "check %d DEAD elapsed_min=%d - relaunching" % (i, int((time.time() - start) // 60)))
        run("adb shell monkey -p " + PKG + " -c android.intent.category.LAUNCHER 1")
        time.sleep(15)
    shot("soak-%02d.png" % i)
write("session-log.txt", "SESSION DONE checks=%d" % i)
run("adb logcat -d > output/logcat.txt")
run("ls -la output")
print("SESSION LONG DONE")
