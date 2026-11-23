import os, re, subprocess, time

PKG = os.environ.get("PKG", "com.paradox.dscm")
APK_URL = os.environ["APK_URL"]
WAIT = int(os.environ.get("WAIT_SECONDS", "30"))
API = os.environ.get("API", "")

def run(cmd):
    print("+", cmd, flush=True)
    return subprocess.run(cmd, shell=True)

def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout

def write(name, text):
    with open(os.path.join("output", name), "a") as f:
        f.write(str(text) + "\n")

def dump_ui(name):
    run("adb shell uiautomator dump /sdcard/dump.xml")
    run("adb pull /sdcard/dump.xml output/" + name)
    try:
        return open(os.path.join("output", name)).read()
    except Exception:
        return ""

def find_tap(xml, pattern):
    m = re.search(r'(?:content-desc|text)="[^"]*' + pattern + r'[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if not m:
        return None
    return ((int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2)

def tap(x, y):
    run("adb shell input tap %d %d" % (x, y))

def shot(name):
    run("adb exec-out screencap -p > output/" + name)

os.makedirs("output", exist_ok=True)
write("config.txt", "LABEL=%s API=%s PROFILE=%s" % (os.environ.get("LABEL", ""), API, os.environ.get("PROFILE", "")))
run("curl -L '" + APK_URL + "' -o app.apk")
write("install.txt", sh("ls -l app.apk"))
write("install.txt", sh("adb install -r app.apk"))
run("adb shell monkey -p " + PKG + " -c android.intent.category.LAUNCHER 1")
time.sleep(WAIT)
shot("02-app.png")

xml = dump_ui("dump_last.xml")
t = find_tap(xml, "Continue as guest")
if t:
    tap(*t)
    write("taps.txt", "TAP Continue as guest %s label" % (t,))
else:
    size = sh("adb shell wm size")
    m = re.search(r"(\d+)x(\d+)", size)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)
    tap(w // 2, int(h * 0.71))
    write("taps.txt", "TAP Continue as guest fallback %d %d" % (w // 2, int(h * 0.71)))
time.sleep(6)
shot("03-after-guest.png")

# Nickname step: "What should we call you?" -> type a name -> "Start playing"
player_name = "Tester" + (API if API else "1")
run('adb shell input text "%s"' % player_name)
write("taps.txt", "TYPE name %s" % player_name)
time.sleep(2)
xml = dump_ui("dump_name.xml")
t = find_tap(xml, "Start playing")
if t:
    tap(*t)
    write("taps.txt", "TAP Start playing %s label" % (t,))
else:
    write("taps.txt", "Start playing NOT FOUND")
time.sleep(8)

# Notifications permission dialog -> Decline
xml = dump_ui("dump_notif.xml")
t = find_tap(xml, "Decline")
if t:
    tap(*t)
    write("taps.txt", "TAP Decline notifications %s label" % (t,))
    time.sleep(5)
else:
    write("taps.txt", "Decline notifications NOT FOUND")
shot("04-lobby.png")

xml = dump_ui("dump_game.xml")
done = False
for name in ["Ludo", "Chess", "Carrom", "Dominoes", "Snakes"]:
    t = find_tap(xml, name)
    if t:
        tap(*t)
        write("taps.txt", "GAME TAP %s %s" % (name, t))
        done = True
        break
if not done:
    write("taps.txt", "GAME TAP none-found, swipe up")
    run("adb shell input swipe 500 1500 500 700 300")
time.sleep(8)
shot("05-game.png")
run("adb logcat -d > output/logcat.txt")
run("ls -la output")
print("SESSION20 DONE")
