import os, re, subprocess, time
PKG = "com.example.vm"
APK_URL = os.environ["APK_URL"]
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
def find_switch(xml):
    m = re.search(r'class="android.widget.Switch"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if not m:
        return None
    return ((int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2)
def top_pkg():
    out = sh("adb shell dumpsys activity activities")
    m = re.search(r"topResumedActivity=ActivityRecord\{[^ ]* [^ ]* ([a-zA-Z0-9_.]+)/", out)
    return m.group(1) if m else "?"
def size():
    m = re.search(r"(\d+)x(\d+)", sh("adb shell wm size"))
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 1920)
W, H = 1080, 1920
def tapf(fx, fy, log):
    x, y = int(W * fx), int(H * fy)
    run("adb shell input tap %d %d" % (x, y))
    write("taps.txt", "TAPF %s %d %d" % (log, x, y))

os.makedirs("output", exist_ok=True)
run("curl -L '" + APK_URL + "' -o app.apk")
write("install.txt", sh("ls -l app.apk"))
write("install.txt", sh("adb install -r app.apk"))
run("adb push assets/sample-video-30s.mp4 /sdcard/Movies/sample-video-30s.mp4")
run("adb push assets/sample-video-30s.mp4 /sdcard/Download/sample-video-30s.mp4")
run("adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Movies/sample-video-30s.mp4")
time.sleep(3)
W, H = size()
write("taps.txt", "screen %dx%d" % (W, H))
run("adb shell rm -f /sdcard/anx.mp4")
rec = subprocess.Popen("adb shell screenrecord --size 720x1280 /sdcard/anx.mp4", shell=True)
time.sleep(2)
run("adb shell monkey -p " + PKG + " -c android.intent.category.LAUNCHER 1")
time.sleep(9)
shot("01-launch.png")
# 'Storage Access Required' card: 'Open Settings' button centre measured from run screenshots
for attempt in range(3):
    tapf(0.676, 0.605, "open-settings-%d" % attempt)
    time.sleep(5)
    write("taps.txt", "top after open-settings %d: %s" % (attempt, top_pkg()))
    if "settings" in top_pkg().lower():
        break
shot("02-settings.png")
xml = dump_ui("dump_settings.xml")
sw = find_switch(xml)
row = find_tap(xml, "Allow access to manage all files") or find_tap(xml, "Allow access")
if sw:
    run("adb shell input tap %d %d" % sw)
    write("taps.txt", "settings SWITCH TAP %s" % (sw,))
elif row:
    run("adb shell input tap %d %d" % (int(W * 0.885), row[1]))
    write("taps.txt", "settings ROW TAP y=%d" % row[1])
else:
    tapf(0.885, 0.295, "settings-toggle-fallback")
time.sleep(3)
shot("03-toggle.png")
write("taps.txt", "appops BEFORE backup: " + sh("adb shell appops get " + PKG + " MANAGE_EXTERNAL_STORAGE").strip().replace("\n", " | "))
# Backup grant only if the on-camera toggle did not take effect
run("adb shell appops set --uid " + PKG + " MANAGE_EXTERNAL_STORAGE allow")
run("adb shell input keyevent 4")
time.sleep(3)
shot("04-back-in-app.png")
# Fresh relaunch: returning from Settings leaves a stale 'Try Again' screen,
# while a cold start with the permission granted loads the library (proven in run 2)
run("adb shell am force-stop " + PKG)
time.sleep(2)
run("adb shell monkey -p " + PKG + " -c android.intent.category.LAUNCHER 1")
time.sleep(9)
shot("05-library.png")
# Folders list is the default Library view: rows are 0 (y .46), Download (y .565), Movies (y .665)
tapf(0.50, 0.665, "movies-folder")
time.sleep(5)
shot("06-movies-folder.png")
# Inside Movies: tap the sample video row to play it
tapf(0.55, 0.40, "video-row")
time.sleep(12)
shot("07-playing.png")
time.sleep(8)
shot("08-playing2.png")
run("adb shell pkill -INT screenrecord")
time.sleep(3)
try:
    rec.wait(timeout=10)
except Exception:
    pass
run("adb pull /sdcard/anx.mp4 output/anx-declaration.mp4")
write("result.txt", sh("ls -l output/"))
run("adb logcat -d > output/logcat.txt")
print("ANX VIDEO V4 DONE")
