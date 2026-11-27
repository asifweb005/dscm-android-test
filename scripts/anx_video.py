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
# ANX shows a 'Storage Access Required' card with an 'Open Settings' button (Flutter: no text in UI dump, use coordinates)
tapf(0.676, 0.569, "open-settings")
time.sleep(5)
shot("02-settings.png")
xml = dump_ui("dump_settings.xml")
t = find_tap(xml, "Allow access to manage all files") or find_tap(xml, "Allow access") or find_tap(xml, "manage all files")
if t:
    run("adb shell input tap %d %d" % t)
    write("taps.txt", "settings-label TAP %s" % (t,))
else:
    # fallback: the toggle switch sits at the right end of that row
    tapf(0.885, 0.295, "settings-toggle-fallback")
time.sleep(3)
shot("03-toggle.png")
# Backup grant in case the toggle tap missed (the on-camera action above already happened)
run("adb shell appops set --uid " + PKG + " MANAGE_EXTERNAL_STORAGE allow")
run("adb shell input keyevent 4")
time.sleep(4)
shot("04-back-in-app.png")
run("adb shell monkey -p " + PKG + " -c android.intent.category.LAUNCHER 1")
time.sleep(6)
shot("05-library.png")
# Folders view (toggle at top of Library)
tapf(0.269, 0.316, "folders-tab")
time.sleep(5)
shot("06-folders.png")
# Open the first folder row (Movies)
tapf(0.50, 0.46, "folder-row")
time.sleep(5)
shot("07-folder-open.png")
run("adb shell input keyevent 4")
time.sleep(3)
# Videos view and play the sample video
tapf(0.72, 0.316, "videos-tab")
time.sleep(5)
shot("08-videos.png")
tapf(0.50, 0.46, "video-row")
time.sleep(12)
shot("09-playing.png")
time.sleep(8)
shot("10-playing2.png")
run("adb shell pkill -INT screenrecord")
time.sleep(3)
try:
    rec.wait(timeout=10)
except Exception:
    pass
run("adb pull /sdcard/anx.mp4 output/anx-declaration.mp4")
write("result.txt", sh("ls -l output/"))
run("adb logcat -d > output/logcat.txt")
print("ANX VIDEO V2 DONE")
