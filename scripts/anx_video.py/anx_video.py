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
    m = re.search(r'(?:content-desc|text)="' + pattern + r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if not m:
        m = re.search(r'(?:content-desc|text)="[^"]*' + pattern + r'[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if not m:
        return None
    return ((int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2)
def tap(x, y):
    run("adb shell input tap %d %d" % (x, y))
def tap_label(xml, labels, logname):
    for lab in labels:
        t = find_tap(xml, re.escape(lab))
        if t:
            tap(*t); write("taps.txt", "%s TAP %s %s" % (logname, lab, t)); return True
    write("taps.txt", "%s none of %s found" % (logname, labels)); return False

os.makedirs("output", exist_ok=True)
run("curl -L '" + APK_URL + "' -o app.apk")
write("install.txt", sh("ls -l app.apk"))
write("install.txt", sh("adb install -r app.apk"))
# Push the sample video BEFORE first launch so the library can find it
run("adb push assets/sample-video-30s.mp4 /sdcard/Movies/sample-video-30s.mp4")
run("adb push assets/sample-video-30s.mp4 /sdcard/Download/sample-video-30s.mp4")
run("adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Movies/sample-video-30s.mp4")
time.sleep(3)
# Start screen recording (max 170s, we stop it ourselves)
run("adb shell rm -f /sdcard/anx.mp4")
rec = subprocess.Popen("adb shell screenrecord --size 720x1280 /sdcard/anx.mp4", shell=True)
time.sleep(2)
run("adb shell monkey -p " + PKG + " -c android.intent.category.LAUNCHER 1")
time.sleep(8)
shot("01-launch.png")
# Permission flow: up to 4 passes over whatever screens appear
for i in range(4):
    xml = dump_ui("dump_perm%d.xml" % i)
    acted = tap_label(xml, ["Grant access", "Grant", "Allow access", "Give access", "Enable access", "Continue", "Allow", "While using the app", "Only this time"], "perm%d" % i)
    shot("02-perm%d.png" % i)
    time.sleep(4)
    if not acted:
        break
# If a system Settings 'All files access' page is showing, turn the toggle on:
xml = dump_ui("dump_settings.xml")
t = find_tap(xml, "Allow access to all files")
if t:
    tap(*t); write("taps.txt", "settings TAP Allow access to all files %s" % (t,)); time.sleep(3)
shot("03-after-perm.png")
run("adb shell input keyevent 4")
time.sleep(3)
# Relaunch the app in case Settings took over
run("adb shell monkey -p " + PKG + " -c android.intent.category.LAUNCHER 1")
time.sleep(6)
shot("04-library.png")
# Folders view
xml = dump_ui("dump_lib.xml")
tap_label(xml, ["Folders"], "folders")
time.sleep(5)
shot("05-folders.png")
xml = dump_ui("dump_folders.xml")
# Open the Movies folder if listed
tap_label(xml, ["Movies", "sample-video-30s", "Download"], "folder-open")
time.sleep(5)
shot("06-folder-open.png")
# Back to Videos / Library and open the sample video
run("adb shell input keyevent 4"); time.sleep(2)
xml = dump_ui("dump_back.xml")
if not tap_label(xml, ["sample-video-30s"], "video-tap1"):
    tap_label(xml, ["Videos", "Library"], "tab")
    time.sleep(4)
    xml = dump_ui("dump_videos.xml")
    tap_label(xml, ["sample-video-30s"], "video-tap2")
time.sleep(10)
shot("07-playing.png")
time.sleep(8)
shot("08-playing2.png")
# Stop recording and pull it
run("adb shell pkill -INT screenrecord")
time.sleep(3)
try:
    rec.wait(timeout=10)
except Exception:
    pass
run("adb pull /sdcard/anx.mp4 output/anx-declaration.mp4")
write("result.txt", sh("ls -l output/"))
run("adb logcat -d > output/logcat.txt")
print("ANX VIDEO DONE")
