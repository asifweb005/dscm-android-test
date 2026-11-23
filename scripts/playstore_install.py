import os, re, subprocess, time

EMAIL = os.environ["GOOGLE_EMAIL"]
PASSWORD = os.environ["GOOGLE_PASSWORD"]
PKG = os.environ.get("PKG", "com.paradox.dscm")

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

def tap_label(pattern):
    run("adb shell uiautomator dump /sdcard/dump.xml")
    run("adb pull /sdcard/dump.xml output/dump_last.xml")
    xml = ""
    try:
        xml = open("output/dump_last.xml").read()
    except Exception:
        pass
    m = re.search(r'(?:content-desc|text)="[^"]*' + pattern + r'[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if m:
        x = (int(m.group(1)) + int(m.group(3))) // 2
        y = (int(m.group(2)) + int(m.group(4))) // 2
        write("steps.txt", "TAP %s %d %d" % (pattern, x, y))
        run("adb shell input tap %d %d" % (x, y))
        return True
    write("steps.txt", "NOT FOUND %s" % pattern)
    return False

os.makedirs("output", exist_ok=True)
write("steps.txt", "open Play Store")
run("adb shell monkey -p com.android.vending -c android.intent.category.LAUNCHER 1")
time.sleep(15)
shot("01-playstore.png")
tap_label("Sign in")
time.sleep(8)
shot("02-signin.png")
write("steps.txt", "type email")
run('adb shell input text "%s"' % EMAIL.replace(" ", "%s"))
time.sleep(2)
tap_label("Next")
time.sleep(8)
shot("03-password.png")
write("steps.txt", "type password")
run('adb shell input text "%s"' % PASSWORD.replace(" ", "%s"))
time.sleep(2)
tap_label("Next")
time.sleep(12)
shot("04-after-password.png")
for label in ["I agree", "Accept", "No thanks", "Not now"]:
    if tap_label(label):
        time.sleep(6)
shot("05-play-home.png")
write("accounts.txt", sh("adb shell dumpsys account"))
write("steps.txt", "open app page + install")
run('adb shell am start -a android.intent.action.VIEW -d "market://details?id=%s"' % PKG)
time.sleep(10)
shot("06-app-page.png")
tap_label("Install")
installed = False
for i in range(24):
    time.sleep(10)
    if PKG in sh("adb shell pm list packages"):
        write("steps.txt", "INSTALLED after ~%ds" % ((i + 1) * 10))
        installed = True
        break
if not installed:
    write("steps.txt", "NOT INSTALLED")
shot("07-after-install.png")
write("steps.txt", "launch app")
run("adb shell monkey -p " + PKG + " -c android.intent.category.LAUNCHER 1")
time.sleep(30)
shot("08-app.png")
run("adb logcat -d > output/logcat.txt")
run("ls -la output")
print("PLAYSTORE INSTALL DONE")
