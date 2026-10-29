# -*- coding: utf-8 -*-
"""
موجو (Mojo) — یه موجود ژله‌ای، شیطون و کنجکاو که روی دسکتاپ ویندوز ۱۱ زندگی می‌کنه.
"""
import io
import json
import math
import os
import queue
import random
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import urllib.request
import datetime as dt
import wave
import struct
import logging
import webbrowser
import tkinter as tk
from tkinter import simpledialog, filedialog

try:
    import winreg
except ImportError:
    winreg = None
try:
    import winsound
except ImportError:
    winsound = None
try:
    import psutil
except ImportError:
    psutil = None
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

APP = "MojoBuddy"
DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP)
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = os.path.join(DATA_DIR, "state.json")
LOG_FILE = os.path.join(DATA_DIR, "mojo.log")
try:
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 1_000_000:
        os.remove(LOG_FILE)
    logging.basicConfig(filename=LOG_FILE, level=logging.WARNING, format="%(asctime)s %(message)s",
                        encoding="utf-8")
except Exception:
    pass


def log_exc():
    msg = traceback.format_exc()
    try:
        logging.error(msg)
    except Exception:
        pass
    try:
        if sys.stderr:
            sys.stderr.write(msg)
    except Exception:
        pass

TRANSP = "#010203"
EW, EH, ECX, ECY, ERX, ERY = 380, 420, 190, 235, 64, 82
EGG_CLICKS = 6
CW, CH = 300, 290
FOOT = 266
CXC = CW / 2
BW, BH = 44, 40
WOOD, WOOD_D = "#9a6a32", "#5c3a17"
CREAM, INK, TEAL = "#fff6dc", "#3b2a14", "#0d9488"
F = ("Segoe UI", 11)
BF = ("Segoe UI", 10)

P2E = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
E2P = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(n):
    return str(n).translate(E2P)


def to_int(s):
    return int(s.strip().translate(P2E))


def bmp(s):
    return "".join(ch for ch in str(s) if ord(ch) <= 0xFFFF)


def short(s, n=140):
    s = " ".join(bmp(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def today_str():
    return dt.date.today().isoformat()


def lerp(a, b, k):
    return a + (b - a) * k


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def mix(c1, c2, k):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(lerp(x, y, k)) for x, y in zip(a, b))


def wchoice(opts):
    tot = sum(w for _, w in opts)
    r = random.uniform(0, tot)
    for f, w in opts:
        r -= w
        if r <= 0:
            return f
    return opts[-1][0]


def to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy, gy = 979, gy - 1600
    else:
        jy, gy = 0, gy - 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
            - 80 + gd + g_d_m[gm - 1])
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
WEEKDAYS = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]


def persian_date():
    d = dt.date.today()
    jy, jm, jd = to_jalali(d.year, d.month, d.day)
    return f"{WEEKDAYS[d.weekday()]} {fa(jd)} {MONTHS[jm - 1]} {fa(jy)}"


def work_area():
    try:
        import ctypes
        from ctypes import wintypes
        rc = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rc), 0):
            return rc.left, rc.top, rc.right, rc.bottom
    except Exception:
        pass
    return None


def fg_window():
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        h = u.GetForegroundWindow()
        if not h or u.IsIconic(h) or not u.IsWindowVisible(h):
            return None
        rc = wintypes.RECT()
        u.GetWindowRect(h, ctypes.byref(rc))
        n = u.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, buf, n + 1)
        return h, (rc.left, rc.top, rc.right, rc.bottom), buf.value
    except Exception:
        return None


APP_NAMES = {"chrome": "Chrome", "msedge": "Edge", "firefox": "Firefox", "brave": "Brave", "opera": "Opera",
             "code": "VS Code", "devenv": "Visual Studio", "pycharm64": "PyCharm", "notepad": "Notepad",
             "notepad++": "Notepad++", "explorer": "File Explorer", "winword": "Word", "excel": "Excel",
             "powerpnt": "PowerPoint", "telegram": "Telegram", "discord": "Discord", "spotify": "Spotify",
             "vlc": "VLC", "steam": "Steam", "python": "Python", "pythonw": "Python", "windowsterminal": "Terminal",
             "cmd": "CMD", "powershell": "PowerShell", "whatsapp": "WhatsApp", "obs64": "OBS", "photoshop": "Photoshop",
             "acrobat": "Acrobat", "mpc-hc64": "MPC-HC", "potplayermini64": "PotPlayer", "blender": "Blender"}


def fg_process():
    """(نام خوانای برنامه‌ی پنجره‌ی جلو، عنوان پنجره) یا None"""
    try:
        import ctypes
        from ctypes import wintypes
        u, k = ctypes.windll.user32, ctypes.windll.kernel32
        h = u.GetForegroundWindow()
        if not h or u.IsIconic(h):
            return None
        pid = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        n = u.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, buf, n + 1)
        title = buf.value
        k.OpenProcess.restype = wintypes.HANDLE
        ph = k.OpenProcess(0x1000, False, pid.value)
        if not ph:
            return None
        try:
            sz = wintypes.DWORD(520)
            pb = ctypes.create_unicode_buffer(520)
            if not k.QueryFullProcessImageNameW(ph, 0, pb, ctypes.byref(sz)):
                return None
        finally:
            k.CloseHandle(ph)
        stem = os.path.splitext(os.path.basename(pb.value))[0]
        if not stem:
            return None
        return APP_NAMES.get(stem.lower(), stem[:1].upper() + stem[1:]), title
    except Exception:
        return None


def idle_seconds():
    try:
        import ctypes
        from ctypes import wintypes

        class LII(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        li = LII()
        li.cbSize = ctypes.sizeof(LII)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li))
        return (ctypes.windll.kernel32.GetTickCount() - li.dwTime) / 1000.0
    except Exception:
        return 0.0


def fmt_dur(sec):
    sec = int(sec)
    h, m = sec // 3600, (sec % 3600) // 60
    if h and m:
        return f"{fa(h)} ساعت و {fa(m)} دقیقه"
    if h:
        return f"{fa(h)} ساعت"
    if m:
        return f"{fa(m)} دقیقه"
    return "کمتر از یه دقیقه" if sec < 45 else "یه دقیقه"



def win_rect(hwnd):
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        if not u.IsWindow(hwnd) or u.IsIconic(hwnd) or not u.IsWindowVisible(hwnd):
            return None
        rc = wintypes.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(rc))
        return rc.left, rc.top, rc.right, rc.bottom
    except Exception:
        return None


def set_cursor(x, y):
    try:
        import ctypes
        ctypes.windll.user32.SetCursorPos(int(x), int(y))
        return True
    except Exception:
        return False


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_cmd():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    py = sys.executable
    pyw = os.path.join(os.path.dirname(py), "pythonw.exe")
    if os.path.exists(pyw):
        py = pyw
    return f'"{py}" "{os.path.abspath(__file__)}"'


def autostart_enabled():
    if not winreg:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP)
            return True
    except OSError:
        return False


def set_autostart(on):
    if not winreg:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, autostart_cmd())
            else:
                try:
                    winreg.DeleteValue(k, APP)
                except OSError:
                    pass
        return True
    except OSError:
        return False


def alive(w):
    try:
        return bool(w.winfo_exists())
    except tk.TclError:
        return False


JOKES = [
    "چرا برنامه‌نویس‌ها همیشه سرما می‌خورن؟ چون Windows باز می‌ذارن!",
    "به کامپیوتر گفتم خسته‌ای؟ گفت نه، فقط یه Restart لازم دارم.",
    "باتری به موبایل گفت: تو فقط وقتی منو یادت میاد که ۱٪ ام!",
    "من ورزش می‌کنم؛ هر روز ۱۰ دقیقه به ورزش کردن فکر می‌کنم.",
    "برنامه‌نویس رفت سوپرمارکت. زنش گفت: یه شیر بخر، اگه تخم‌مرغ داشتن ۶ تا بیار. با ۶ تا شیر برگشت: «تخم‌مرغ داشتن!»",
    "ژله‌ها هیچ‌وقت دعوا نمی‌کنن... فقط یه کم می‌لرزن و قهر می‌کنن.",
    "چرا کامپیوتر عینک زد؟ چون Windows هاش کثیف بود!",
]

FACTS = [
    "عسل هیچ‌وقت خراب نمی‌شه؛ اگه دربسته باشه، سال‌ها دووم میاره.",
    "اختاپوس سه تا قلب داره!",
    "از نظر گیاه‌شناسی، موز توت محسوب می‌شه.",
    "زرافه هم مثل ما فقط ۷ تا مهره‌ی گردن داره.",
    "نور سریع‌تر از صدا می‌ره؛ برای همین اول برق رو می‌بینی بعد رعد رو می‌شنوی.",
    "ما تقریباً یک‌سوم عمرمونو می‌خوابیم.",
    "قلب میگو توی سرشه!",
    "ژله‌ماهی ۹۵٪ آبه و مغز نداره، ولی خوشبخته.",
]

QUIPS = [
    "یه چیزی یادم رفته... آها، فراموش کردم چی بود.",
    "اینجا چقدر پیکسل داره!",
    "اگه ژله بودن گناهه، من مجرمم.",
    "کسی بستنی دیده؟ برای دوستم می‌پرسم.",
    "دارم فکر می‌کنم... نه، همون خالی بود.",
    "بی‌سر و صدا کنارتم. فقط یه کم ژله‌ام که شل می‌شم.",
    "این موس رو دوست دارم؛ شبیه موشه ولی نمی‌خوره منو.",
    "یه لحظه به صفحه‌ت نگاه کردم... چه شلوغ!",
    "اگه خسته‌ای بگو؛ برات می‌رقصم.",
    "ببین، من الان دارم کار می‌کنم. (نه نمی‌کنم)",
    "هوم... بوی چایی میاد؟",
    "امروز هم بهترین موجود دسکتاپ‌ام!",
]

POKES = ["ای! قلقلکم میاد!", "هی! چرا می‌زنی؟", "قول می‌دم کاری نکردم!", "بوینگ!", "من ژله‌ام، دکمه نیستم!",
         "ایییی نکن، می‌ریزم!", "باشه باشه، سلام!", "بزن بزن... ولی آروم."]
DROP_LINES = ["ووووی! سرم گیج رفت!", "فرود اضطراری!", "دفعه‌ی بعد بگو بالا می‌برمت!", "بوووم! سالم نشستم."]
PEEK_LINES = ["هی... دیدمت!", "بوووو!", "بی‌سر و صدا اومدم.", "کسی منو دید؟", "اینجا امنه؟", "سلاااام از اون‌ور دیوار!"]
GLITCH_LINES = ["ت... تو... منو... می‌بینی؟", "هیچی نبود، فقط یه لحظه از بعد دیگه رد شدم.",
                "ایراد از من نیست؛ از پیکسل‌هاست!", "قول می‌دم باگ نیست، ویژگیه!"]
PARADE_TEXTS = ["نون داره این اطراف؟", "بغلم کن", "آب بخور!", "من گم نشدم", "پنیر ندیدی؟", "حال کردی؟",
                "تعطیلات کی میشه؟", "من بی‌گناهم", "یه ژله می‌خوای؟", "کار نکن، بازی کن"]

DRAW_PROMPTS = ["از میوه‌ی مورد علاقه‌ت نقاشی بکش", "یه خونه‌ی رویایی بکش", "منو بکش! (قشنگ بکشی‌ها)",
                "یه حیوون عجیب‌وغریب اختراع کن و بکش", "حال و هوای امروزت رو نقاشی کن", "یه گل بکش",
                "غذای مورد علاقه‌ت رو بکش", "یه موجود فضایی بکش", "خودتو ۱۰ سال دیگه بکش", "یه ماشین خفن بکش"]
DRAW_PRAISE = ["شاهکاره! می‌چسبونمش به یخچال!", "واااو! پیکاسو شرمنده شد.", "این رو قاب می‌کنم!",
               "عجب هنرمندی! ژله‌ها عاشق هنرن.", "من که کلی خوشم اومد!"]

ASKS = {
    "fruit": ("میوه‌ی مورد علاقه‌ت چیه؟", "{v}! یادم می‌مونه. ژله‌ها عاشق میوه‌ان."),
    "color": ("رنگ مورد علاقه‌ت چیه؟", "{v}؟ سلیقه‌ی خوبی داری!"),
    "animal": ("حیوون مورد علاقه‌ت چیه؟", "{v}! باحاله. من خودم یه موجود عجیبم، ولی {v} هم خوبه."),
    "food": ("غذای مورد علاقه‌ت چیه؟", "{v}... آب از دهنم افتاد!"),
    "movie": ("فیلم یا سریال مورد علاقه‌ت چیه؟", "{v}؟ باید یه شب باهم ببینیمش!"),
    "game": ("بازی مورد علاقه‌ت چیه؟", "{v}! بعداً ازت یاد می‌گیرم."),
    "place": ("اگه می‌تونستی همین الان هرجای دنیا باشی، کجا بودی؟", "{v}؟! منو هم ببر!"),
    "hobby": ("سرگرمی مورد علاقه‌ت چیه؟", "{v}... جالبه! بیشتر یادم بده."),
}
FACT_LINES = {
    "fruit": "یادمه {v} دوست داشتی. امروز خوردیش؟",
    "color": "رنگ {v} واقعاً قشنگه.",
    "animal": "امروز یاد {v} افتادم.",
    "food": "حدس می‌زنم الان {v} می‌چسبه.",
    "movie": "هنوز به {v} فکر می‌کنم.",
    "game": "یه دست {v} بزنیم؟",
    "place": "یه روزی می‌ریم {v}، قول بده.",
    "hobby": "امروز به {v} رسیدی؟",
}

ASKS.update({
    "music": ("چه سبک موسیقی یا خواننده‌ای رو بیشتر گوش می‌دی؟", "{v}! یه روز باید برام بخونیش."),
    "book": ("یه کتاب که دوستش داری چیه؟", "{v}؟ اسمش رو حفظ کردم!"),
    "job": ("شغل رویاهات چیه؟", "{v}! تو که می‌تونی. من هم کمکت می‌کنم."),
    "power": ("اگه یه ابرقدرت داشتی چی بود؟", "{v}! خیلی خفنه. من فقط می‌تونم شل بشم."),
    "goal": ("یه هدف برای این هفته داری؟ بگو تا هواتو داشته باشم.", "«{v}»... روی من حساب کن!"),
    "snack": ("خوراکی مورد علاقه‌ت چیه؟", "{v}! آب از لب و لوچه‌م راه افتاد."),
    "app": ("کدوم برنامه رو همیشه روی کامپیوترت باز می‌کنی؟", "{v}! پس باید ببینمش."),
})
FACT_LINES.update({
    "music": "امروز یه آهنگ از {v} گوش دادی؟",
    "book": "هنوز به {v} فکر می‌کنم.",
    "job": "امروز یه قدم کوچیک به سمت «{v}» برداشتی؟",
    "power": "اگه ابرقدرت {v} داشتم، اول یه بستنی می‌خریدم.",
    "goal": "هدفت «{v}» بود؛ چه خبر؟",
    "snack": "الان یه {v} می‌چسبه.",
    "app": "امروز {v} رو باز کردی؟",
    "pet": "{v}‌ها بامزه‌ان، ولی ژله‌ها بامزه‌ترن!",
    "scene": "یه روز با هم بریم {v}؟",
    "chrono": "تو «{v}» هستی؛ یادمه!",
    "drink": "امروز {v} خوردی؟",
    "season": "{v} فصل مورد علاقه‌ته؛ یادم موند.",
    "taste": "یادمه تو «{v}» رو بیشتر دوست داری.",
    "genre": "امشب یه فیلم {v} ببینیم؟",
})
FACT_LABELS = {"fruit": "میوه", "color": "رنگ", "animal": "حیوون", "food": "غذا", "movie": "فیلم/سریال",
               "game": "بازی", "place": "جای رویایی", "hobby": "سرگرمی", "music": "موسیقی", "book": "کتاب",
               "job": "شغل رویایی", "power": "ابرقدرت", "goal": "هدف", "snack": "خوراکی", "app": "برنامه",
               "pet": "گربه/سگ", "scene": "کوه/دریا", "chrono": "سحرخیز/شب‌زنده‌دار", "drink": "نوشیدنی",
               "season": "فصل", "taste": "شیرین/شور", "genre": "ژانر", "platform": "پلتفرم", "social": "انرژی"}

DIZZY_DIST, DIZZY_FRAMES = 250, 150
COIN_WIN = 30
COLOR_PRICE, CUSTOM_PRICE = 8, 20
SHOP_ITEMS = [
    {"id": "jetpack", "name": "جت‌پک", "desc": "موجو گاهی جت‌پک می‌پوشه و توی آسمون دسکتاپ پرواز می‌کنه!",
     "price": 90, "tag": "#f97316"},
    {"id": "parachute", "name": "چتر نجات", "desc": "اگه از بالا پرتش کنی چترشو باز می‌کنه، نرم میاد پایین و سرش گیج نمی‌ره.",
     "price": 60, "tag": "#3b82f6"},
]

GOOGLE = "https://www.google.com/search?q={q}"
YT = "https://www.youtube.com/results?search_query={q}"
IMG = "https://www.google.com/search?tbm=isch&q={q}"
GIFTS = {
    "fruit": ("یه دستور باحال با {v} پیدا کردم!", GOOGLE, "دسر با {v}"),
    "food": ("بهترین طرز تهیه‌ی {v} رو برات پیدا کردم!", GOOGLE, "طرز تهیه {v} خوشمزه"),
    "snack": ("یه ایده‌ی خوشمزه با {v}!", GOOGLE, "ایده با {v}"),
    "movie": ("چند تا فیلم شبیه {v} پیدا کردم!", GOOGLE, "فیلم های شبیه {v}"),
    "game": ("خبرهای تازه و ترفندهای {v} رو پیدا کردم!", GOOGLE, "{v} ترفند و اخبار جدید"),
    "animal": ("ویدیوهای بامزه‌ی {v}!", YT, "{v} بامزه"),
    "place": ("عکس‌های قشنگ {v}!", IMG, "{v}"),
    "hobby": ("یه آموزش باحال برای {v}!", YT, "آموزش {v}"),
    "music": ("یه پلی‌لیست از {v} برات پیدا کردم!", YT, "{v} پلی لیست"),
    "color": ("والپیپر {v} برای دسکتاپت!", IMG, "wallpaper {v}"),
    "book": ("خلاصه و نقد {v} رو پیدا کردم!", GOOGLE, "خلاصه کتاب {v}"),
    "job": ("یه مسیر یادگیری برای «{v}»!", GOOGLE, "چطور {v} بشیم"),
    "goal": ("چند تا ترفند برای رسیدن به «{v}»!", GOOGLE, "ترفند رسیدن به {v}"),
    "power": ("ببین ابرقدرت {v} توی فیلم‌ها چطوریه!", YT, "{v} ابرقدرت"),
}
PERSONAL_CH = {
    "fruit": "امروز یه {v} بخور و بیا بگو چطور بود.",
    "hobby": "۱۵ دقیقه به {v} برس.",
    "animal": "از {v} یه نقاشی بکش.",
    "book": "۱۰ صفحه از {v} (یا یه کتاب دیگه) بخون.",
    "music": "یه آهنگ جدید از {v} پیدا کن و گوش بده.",
    "goal": "امروز یه قدم کوچیک به سمت «{v}» بردار.",
    "movie": "امشب یه قسمت یا صحنه از {v} ببین.",
    "place": "۵ دقیقه چشماتو ببند و تصور کن توی {v} هستی.",
}
SHOW_KINDS = {
    "game": {"title": "بازی مورد علاقه", "q": "کدوم بازی رو از همه بیشتر دوست داری؟",
             "pick": "حالا فایل بازی (یا میان‌برش) رو نشونم بده تا بشناسمش:",
             "ask": "دوست داری {n} رو بازی کنیم؟", "file": True},
    "app": {"title": "برنامه مورد علاقه", "q": "کدوم برنامه رو همیشه باز می‌کنی؟",
            "pick": "فایل برنامه (یا میان‌برش) رو نشونم بده:",
            "ask": "{n} رو برات باز کنم؟", "file": True},
    "music": {"title": "موسیقی مورد علاقه", "q": "یه آهنگ یا پوشه‌ی موسیقی که دوست داری چیه؟",
              "pick": "فایل آهنگ یا پوشه‌ی موسیقی رو نشونم بده:",
              "ask": "دوست داری {n} رو گوش بدیم؟", "file": True, "dir": True},
    "site": {"title": "سایت مورد علاقه", "q": "کدوم سایت رو هر روز سر می‌زنی؟",
             "pick": "", "ask": "بریم سراغ {n}؟", "file": False},
}

HEALTH = [("آب", "وقت آب خوردنه! یه لیوان آب بخور."),
          ("چشم", "۲۰ ثانیه به یه چیز دور نگاه کن تا چشمات استراحت کنن."),
          ("کمر", "صاف بشین و شونه‌هات رو شل کن."),
          ("قدم", "بلند شو و یه دقیقه قدم بزن، من هم همراهتم!"),
          ("نفس", "یه نفس عمیق بکش... و آروم بده بیرون.")]

FOODS = [("سیب", "yes", "ممم سیب! خوشمزه‌ست."),
         ("موز", "yes", "موز! کاملاً شبیه ژله‌ها نیست ولی خوبه."),
         ("پیتزا", "love", "پیتزاااا! دوستت دارم!"),
         ("شکلات", "love", "شکلات؟! امروز بهترین روز زندگیمه!"),
         ("بروکلی", "yuck", "ایییی بروکلی؟! نه نه نه!"),
         ("فلفل تند", "hot", "آخخخ تند بود! آب! آب!"),
         ("برگر", "love", "برگر! دقیقاً همین رو می‌خواستم!"),
         ("بستنی", "love", "بستنی! مغزم یخ کرد ولی می‌ارزید!"),
         ("هندوانه", "yes", "هندوانه! تابستون تو یه تیکه.")]

CHALLENGES = [
    ("یه لیوان آب بزرگ بخور.", None, None, None),
    ("۵ دقیقه بدون موبایل قدم بزن.", None, None, None),
    ("۱۰ تا شنا یا اسکوات بزن.", None, None, None),
    ("میزتو ۵ دقیقه مرتب کن.", None, None, None),
    ("به یکی از دوستات پیام بده و حالشو بپرس.", None, None, None),
    ("۱۰ دقیقه چیز جدیدی یاد بگیر.", None, None, None),
    ("سه چیزی که ازشون ممنونی رو بنویس.", None, None, None),
    ("یه آهنگ جدید گوش بده.", None, None, None),
    ("یه نقاشی برای من بکش.", "drawings", ">=", 1),
    ("منو توی «بگیرمش» ۴ بار بگیر.", "catches", ">=", 4),
    ("توی کوییز یه جواب درست بده.", "quiz_right", ">=", 1),
    ("سه بار توی سنگ‌کاغذ‌قیچی منو ببر.", "rps_wins", ">=", 3),
    ("توی دوز یه بار منو ببر.", "ttt_wins", ">=", 1),
    ("توی ریاضی سریع حداقل ۸ تا درست جواب بده.", "math_best", ">=", 8),
    ("توی تست واکنش زیر ۳۰۰ میلی‌ثانیه بزن.", "reaction_best", "<=", 300),
    ("عدد رو با حداکثر ۷ حدس پیدا کن.", "guess_best", "<=", 7),
]

QUIZ = [
    ("کدوم سیاره به سیاره‌ی سرخ معروفه؟", ["ناهید", "مریخ", "مشتری", "زحل"], 1),
    ("بزرگ‌ترین اقیانوس جهان کدومه؟", ["اطلس", "هند", "آرام", "منجمد شمالی"], 2),
    ("یه شش‌ضلعی چند ضلع داره؟", ["۵", "۶", "۷", "۸"], 1),
    ("نماد شیمیایی طلا چیه؟", ["Ag", "Fe", "Au", "Gd"], 2),
    ("حاصل ۷ × ۸ چنده؟", ["۵۴", "۵۶", "۵۸", "۶۴"], 1),
    ("بلندترین قله‌ی جهان کدومه؟", ["اورست", "دماوند", "کی‌تو", "مون‌بلان"], 0),
    ("یک کیلوبایت (دودویی) چند بایته؟", ["۱۰۰۰", "۱۰۲۴", "۵۱۲", "۲۰۴۸"], 1),
    ("سریع‌ترین حیوان خشکی کدومه؟", ["شیر", "اسب", "یوزپلنگ", "گوزن"], 2),
    ("سراینده‌ی شاهنامه کیه؟", ["سعدی", "حافظ", "فردوسی", "مولوی"], 2),
    ("پایتخت ژاپن کدومه؟", ["اوساکا", "کیوتو", "توکیو", "ناگویا"], 2),
]

DEFAULT = {
    "user_name": "", "xp": 0, "streak": 0, "best_streak": 0, "last_done": "",
    "facts": {}, "gallery": [], "moods": [], "reminders": [],
    "chaos": 2, "mouse_ok": True, "window_ok": True, "mute_until": 0,
    "api_key": "", "first_run": True, "today": {}, "stats": {"games": 0, "wins": 0},
    "sound": 2, "library": [], "ev_stats": {}, "gifts": {}, "no_kinds": {},
    "study_total": 0, "study_count": 0,
    "track_ok": False, "usage": {},
    "look": {"body": "#5eead4", "eye": "#3b2a14", "cheek": "#fb7185"},
    "coins": 0, "owned": {}, "owned_colors": [],
}


def load_state():
    S = json.loads(json.dumps(DEFAULT))
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            for k, v in json.load(f).items():
                S[k] = v
    except Exception:
        pass
    return S


def save_state(S):
    try:
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(S, f, ensure_ascii=False)
        os.replace(tmp, STATE_FILE)
    except Exception:
        pass


LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def ttt_winner(bd):
    for a, b, c in LINES:
        if bd[a] and bd[a] == bd[b] == bd[c]:
            return bd[a]
    return "draw" if all(bd) else None


def ttt_bot(bd):
    for who in ("O", "X"):
        for ln in LINES:
            vals = [bd[i] for i in ln]
            if vals.count(who) == 2 and vals.count("") == 1:
                return ln[vals.index("")]
    if not bd[4]:
        return 4
    return random.choice([i for i in range(9) if not bd[i]])


class Sounds:
    NAMES = ["b0", "b1", "b2", "b3", "b4", "b5", "pop", "thud", "boing", "land", "squeak", "ding",
             "happy", "yay", "sad", "giggle", "whoosh", "glitch", "page"]
    RATE = 22050
    AMP = {1: 0.22, 2: 0.45, 3: 0.8}

    def __init__(self, level):
        self.dir = os.path.join(DATA_DIR, "sounds")
        self.level, self.files, self.last = 0, {}, 0.0
        try:
            os.makedirs(self.dir, exist_ok=True)
            self.set_level(level)
        except Exception:
            log_exc()

    def tone(self, f0, f1, dur, shape="sine", vib=0.0):
        r = self.RATE
        n = int(r * dur)
        out, ph = [], 0.0
        for i in range(n):
            k = i / max(1, n - 1)
            f = f0 + (f1 - f0) * k
            if vib:
                f += math.sin(i / r * 44.0) * vib
            ph += 2 * math.pi * f / r
            if shape == "tri":
                v = 2 / math.pi * math.asin(math.sin(ph))
            elif shape == "square":
                v = 0.55 if math.sin(ph) >= 0 else -0.55
            else:
                v = math.sin(ph)
            env = min(1.0, i / (r * 0.005)) * min(1.0, (n - i) / (r * 0.025)) * (1 - 0.45 * k)
            out.append(v * env)
        return out

    def noise(self, dur):
        n = int(self.RATE * dur)
        out, prev = [], 0.0
        for i in range(n):
            prev = prev * 0.6 + random.uniform(-1, 1) * 0.4
            out.append(prev * math.sin(math.pi * i / max(1, n - 1)) ** 2)
        return out

    def defs(self):
        T = self.tone
        d = {}
        for i, f in enumerate([380, 440, 500, 560, 640, 720]):
            d[f"b{i}"] = T(f, f * 1.12, 0.055, "tri")
        d["pop"] = T(750, 220, 0.09)
        d["thud"] = T(140, 45, 0.16)
        d["boing"] = T(260, 620, 0.26, "sine", vib=25)
        d["land"] = T(240, 110, 0.07, "tri")
        d["squeak"] = T(900, 1600, 0.11, "tri")
        d["ding"] = T(988, 988, 0.1) + T(1319, 1319, 0.22)
        d["happy"] = (T(523, 523, 0.08, "tri") + T(659, 659, 0.08, "tri") + T(784, 784, 0.08, "tri")
                      + T(1047, 1047, 0.2, "tri"))
        d["yay"] = (T(523, 523, 0.08, "tri") + T(659, 659, 0.08, "tri") + T(784, 784, 0.08, "tri")
                    + T(1047, 1047, 0.08, "tri") + T(784, 784, 0.08, "tri") + T(1047, 1047, 0.08, "tri")
                    + T(1319, 1319, 0.3, "tri"))
        d["sad"] = T(420, 300, 0.18, "tri") + T(330, 190, 0.32, "tri")
        d["giggle"] = sum([T(600 + 150 * (i % 2), 700 + 150 * (i % 2), 0.05, "tri") for i in range(6)], [])
        d["whoosh"] = self.noise(0.3)
        d["glitch"] = sum([T(random.randint(200, 1800), random.randint(200, 1800), 0.03, "square")
                           for _ in range(10)], [])
        d["page"] = [v * 0.7 for v in self.noise(0.16)]
        return d

    def write(self, path, samples):
        amp = self.AMP[self.level]
        n = len(samples)
        data = struct.pack(f"<{n}h", *(int(clamp(s * amp, -1.0, 1.0) * 32767) for s in samples))
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.RATE)
            wf.writeframes(data)

    def set_level(self, level):
        self.level, self.files = level, {}
        if level <= 0:
            return
        paths = {n: os.path.join(self.dir, f"{n}_{level}.wav") for n in self.NAMES}
        if not all(os.path.exists(p) for p in paths.values()):
            for n, samples in self.defs().items():
                self.write(paths[n], samples)
        self.files = paths

    def play(self, name, force=False):
        if self.level <= 0 or not winsound or name not in self.files:
            return
        now = time.time()
        if not force and now - self.last < 0.08:
            return
        self.last = now
        try:
            winsound.PlaySound(self.files[name], winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except Exception:
            pass


COVER, COVER_D, COVER_L = "#a8294f", "#6a1633", "#d1537f"    # جلد شرابی مایل به صورتی
PAGE, PAGE_D, GOLD = "#fff6e3", "#d9c9a6", "#f2c14e"
SAND, SAND_D = "#f2b95b", "#d99a3a"
BOOK_WN, BOOK_WF, BOOK_H = 156, 126, 34         # کتاب بازِ روی زمین (نمای مورب)
BK_W, BK_H = 64, 104                            # کتاب بسته‌ی ایستاده (بلندتر از خود موجو)


def draw_closed_book(c, x0, ytop, w, h):
    c.create_rectangle(x0 + 5, ytop + 5, x0 + w + 6, ytop + h + 3, fill=PAGE, outline=COVER_D, width=2)
    for i in range(1, 4):
        c.create_line(x0 + w + 1 + i, ytop + 8, x0 + w + 1 + i, ytop + h - 1, fill=PAGE_D)
    c.create_rectangle(x0, ytop, x0 + w, ytop + h, fill=COVER, outline=COVER_D, width=3)
    c.create_rectangle(x0, ytop, x0 + w * 0.15, ytop + h, fill=COVER_D, outline=COVER_D)
    for fy in (0.14, 0.5, 0.86):
        c.create_line(x0 + 1, ytop + h * fy, x0 + w * 0.15, ytop + h * fy, fill=GOLD, width=2)
    c.create_rectangle(x0 + w * 0.22, ytop + 5, x0 + w - 5, ytop + h - 5, outline=COVER_L, width=1)
    c.create_rectangle(x0 + w * 0.32, ytop + h * 0.12, x0 + w * 0.9, ytop + h * 0.46, outline=GOLD, width=2)
    ox, oy, r = x0 + w * 0.61, ytop + h * 0.29, min(w, h) * 0.13
    c.create_polygon(ox, oy - r, ox + r, oy, ox, oy + r, ox - r, oy, fill=GOLD, outline="")
    for fy, fw in ((0.6, 0.5), (0.68, 0.34)):
        c.create_line(x0 + w * (0.61 - fw / 2 * 0.9), ytop + h * fy, x0 + w * (0.61 + fw / 2 * 0.9), ytop + h * fy,
                      fill=GOLD, width=2, capstyle="round")
    bx = x0 + w * 0.72
    c.create_polygon(bx, ytop + h - 2, bx + 9, ytop + h - 2, bx + 9, ytop + h + 13, bx + 4.5, ytop + h + 8,
                     bx, ytop + h + 13, fill="#f58aa8", outline=COVER_D)


def draw_open_book(c, cx, yn, open_q=1.0, flip=None):
    Wn, Wf, H = BOOK_WN, BOOK_WF, BOOK_H
    yf = yn - H
    c.create_polygon(cx - Wf / 2 - 6, yf - 4, cx + Wf / 2 + 6, yf - 4, cx + Wn / 2 + 7, yn + 3, cx - Wn / 2 - 7, yn + 3,
                     fill=COVER, outline=COVER_D, width=3)
    c.create_line(cx - Wn / 2 - 4, yn + 1, cx + Wn / 2 + 4, yn + 1, fill=COVER_L, width=2)
    if open_q > 0.02:
        q = open_q
        for side in (-1, 1):
            far_o = cx + side * (Wf / 2 - 3) * q
            near_o = cx + side * (Wn / 2 - 4) * q
            gut = cx + side * 1.5
            c.create_polygon(gut, yf + 2, far_o, yf + 1, near_o, yn - 2, gut, yn - 3, fill=PAGE, outline=PAGE_D)
            if q > 0.7:
                for i in range(5):
                    f = (i + 1) / 6.0
                    y = lerp(yf + 2, yn - 3, f)
                    xo = lerp(far_o, near_o, f) - side * 12 * q
                    xi = gut + side * 7
                    ratio = 0.72 + 0.28 * math.sin(i * 2.3 + side * 1.7)
                    c.create_line(xo, y, xo + (xi - xo) * ratio, y, fill="#bfae8c", width=2 if f > 0.5 else 1)
        c.create_line(cx, yf + 2, cx, yn - 3, fill=PAGE_D, width=2)
    if flip is not None and open_q >= 1.0:
        ang = math.pi * flip
        lift = math.sin(ang) * 16
        xf, xn = cx + (Wf / 2 - 4) * math.cos(ang), cx + (Wn / 2 - 5) * math.cos(ang)
        c.create_polygon(cx, yf + 2, xf, yf + 1 - lift * 1.2, xn, yn - 2 - lift, cx, yn - 3,
                         fill="#fffaf0" if flip < 0.5 else "#f3e6c8", outline=PAGE_D)


def hg_w(d, Hb, W):
    return 2.4 + (W - 2.4) * math.sin(min(1.0, d / (Hb * 0.6)) * math.pi / 2)


def draw_hourglass(c, hx, base, pct, label, t):
    W, Hb = 17, 36
    yb = base - 8
    yn = yb - Hb
    ytop = yn - Hb
    prof = [(Hb * i / 10, hg_w(Hb * i / 10, Hb, W)) for i in range(11)]
    for s in (-1, 1):
        c.create_line(hx + s * (W + 4), ytop, hx + s * (W + 4), yb, width=5, fill=WOOD_D, capstyle="round")
        c.create_line(hx + s * (W + 4), ytop, hx + s * (W + 4), yb, width=2, fill=WOOD)
    top_pts = [(hx - w, yn - d) for d, w in prof] + [(hx + w, yn - d) for d, w in reversed(prof)]
    bot_pts = [(hx - w, yn + d) for d, w in prof] + [(hx + w, yn + d) for d, w in reversed(prof)]
    c.create_polygon(top_pts, fill="#e6f4ff", outline="#5f86ad", width=2)
    c.create_polygon(bot_pts, fill="#e6f4ff", outline="#5f86ad", width=2)
    ds = Hb * 0.9 * (1.0 - pct)
    if ds > 1.5:
        sp = [(d, w) for d, w in prof if d <= ds] + [(ds, hg_w(ds, Hb, W))]
        c.create_polygon([(hx - w + 1.5, yn - d) for d, w in sp] + [(hx + w - 1.5, yn - d) for d, w in reversed(sp)],
                         fill=SAND, outline="")
    pile = Hb * 0.88 * pct
    if pile > 1.5:
        d0 = Hb - pile
        sp = [(d0, hg_w(d0, Hb, W))] + [(d, w) for d, w in prof if d > d0]
        pts = [(hx - w + 1.5, yn + d) for d, w in sp] + [(hx + w - 1.5, yn + d) for d, w in reversed(sp)]
        pts.append((hx, yn + d0 - min(6, pile * 0.35)))
        c.create_polygon(pts, fill=SAND, outline="")
    if 0.0 < pct < 1.0:
        c.create_line(hx, yn - 3, hx, yn + Hb - pile - 1, fill=SAND_D, width=2, dash=(2, 2), dashoffset=t % 4)
    c.create_line(hx - W + 5, ytop + 8, hx - W + 6, ytop + 20, fill="white", width=2, capstyle="round")
    for yy in (ytop - 8, yb):
        c.create_rectangle(hx - W - 8, yy, hx + W + 8, yy + 8, fill=WOOD, outline=WOOD_D, width=2)
        c.create_line(hx - W - 5, yy + 2, hx + W + 5, yy + 2, fill="#c08a4d", width=1)
    c.create_rectangle(hx - 26, ytop - 32, hx + 26, ytop - 16, fill=CREAM, outline=WOOD_D, width=2)
    c.create_text(hx, ytop - 24, text=label, font=("Segoe UI", 8, "bold"), fill=INK)


def draw_food(c, name, X, Y, sc=1.0, ang=0.0, style=None):
    if name == "کیک":
        draw_cake_slice(c, X, Y, sc, style)
        return
    ca, sa = math.cos(ang), math.sin(ang)

    def P(x, y):
        x, y = x * sc, y * sc
        return X + x * ca - y * sa, Y + x * sa + y * ca

    def poly(pts, **kw):
        flat = []
        for x, y in pts:
            flat += list(P(x, y))
        c.create_polygon(flat, **kw)

    def circ(x, y, r, **kw):
        px, py = P(x, y)
        rr = r * sc
        c.create_oval(px - rr, py - rr, px + rr, py + rr, **kw)

    if name == "سیب":
        circ(-5, 0, 13, fill="#dc2626", outline="#7f1d1d", width=2)
        circ(6, 0, 13, fill="#dc2626", outline="#7f1d1d", width=2)
        circ(0, 1, 12, fill="#dc2626", outline="")
        circ(-6, -4, 3, fill="#fca5a5", outline="")
        a, b = P(0, -10), P(2, -20)
        c.create_line(a[0], a[1], b[0], b[1], fill="#78350f", width=max(2, 3 * sc))
        poly([(2, -17), (13, -24), (11, -13)], fill="#22c55e", outline="#15803d")
    elif name == "موز":
        pts = [(-14, -18), (-6, -20), (6, -8), (14, 12), (10, 20), (3, 16), (-3, 0), (-10, -12)]
        poly(pts, fill="#facc15", outline="#a16207", width=2, smooth=True)
        poly([(-14, -18), (-6, -20), (-7, -14), (-13, -13)], fill="#78350f", outline="#78350f")
        poly([(10, 20), (3, 16), (6, 22)], fill="#78350f", outline="#78350f")
    elif name == "پیتزا":
        poly([(0, -26), (-17, 12), (17, 12)], fill="#fbbf24", outline="#b45309", width=2)
        poly([(-18, 10), (18, 10), (19, 18), (-19, 18)], fill="#d97706", outline="#92400e", width=2, smooth=True)
        circ(-2, -3, 4.2, fill="#dc2626", outline="#7f1d1d")
        circ(-7, 5, 3.6, fill="#dc2626", outline="#7f1d1d")
        circ(6, 4, 3.8, fill="#dc2626", outline="#7f1d1d")
        circ(1, -14, 2.8, fill="#dc2626", outline="#7f1d1d")
        circ(5, -6, 1.6, fill="#65a30d", outline="")
    elif name == "شکلات":
        poly([(-11, -22), (11, -22), (11, 8), (-11, 8)], fill="#78350f", outline="#3f1d0b", width=2)
        for gx in (-3.7, 3.7):
            a, b = P(gx, -22), P(gx, 8)
            c.create_line(a[0], a[1], b[0], b[1], fill="#3f1d0b", width=1)
        for gy in (-12, -2):
            a, b = P(-11, gy), P(11, gy)
            c.create_line(a[0], a[1], b[0], b[1], fill="#3f1d0b", width=1)
        poly([(-12, 6), (12, 6), (13, 22), (-13, 22)], fill="#e2e8f0", outline="#94a3b8", width=2)
        poly([(-8, 11), (8, 11), (8, 17), (-8, 17)], fill="#ef4444", outline="")
    elif name == "بروکلی":
        poly([(-4, 2), (4, 2), (6, 22), (-6, 22)], fill="#a3e635", outline="#4d7c0f", width=2)
        for (x, y, r) in ((-9, -4, 9), (8, -5, 9), (0, -12, 10), (-1, 0, 9)):
            circ(x, y, r, fill="#16a34a", outline="#14532d", width=2)
        circ(-2, -12, 2, fill="#4ade80", outline="")
    elif name == "فلفل تند":
        poly([(-5, -18), (6, -18), (10, -2), (8, 14), (2, 24), (-3, 12), (-9, -2)], fill="#dc2626", outline="#7f1d1d",
             width=2, smooth=True)
        poly([(-7, -17), (-2, -26), (7, -26), (6, -17)], fill="#16a34a", outline="#14532d", width=2)
        circ(-3, -6, 2.5, fill="#fca5a5", outline="")
    elif name == "برگر":
        poly([(-17, -4), (-14, -16), (0, -22), (14, -16), (17, -4)], fill="#d97706", outline="#92400e", width=2, smooth=True)
        for (x, y) in ((-6, -14), (2, -17), (8, -11)):
            circ(x, y, 1.4, fill="#fde68a", outline="")
        poly([(-18, -4), (-12, 0), (-6, -4), (0, 0), (6, -4), (12, 0), (18, -4), (17, 2), (-17, 2)], fill="#22c55e", outline="#15803d")
        poly([(-17, 1), (17, 1), (17, 9), (-17, 9)], fill="#78350f", outline="#3f1d0b", width=2)
        poly([(-17, 9), (17, 9), (15, 14), (-15, 14)], fill="#facc15", outline="")
        poly([(-17, 14), (17, 14), (14, 22), (-14, 22)], fill="#d97706", outline="#92400e", width=2, smooth=True)
    elif name == "بستنی":
        poly([(-10, 2), (10, 2), (0, 28)], fill="#f59e0b", outline="#92400e", width=2)
        for (x1, y1, x2, y2) in ((-6, 4, 3, 18), (6, 4, -3, 18), (-3, 3, 4, 10)):
            a, b = P(x1, y1), P(x2, y2)
            c.create_line(a[0], a[1], b[0], b[1], fill="#b45309", width=1)
        circ(0, -2, 12, fill="#fda4af", outline="#be123c", width=2)
        circ(0, -16, 10, fill="#fef3c7", outline="#b45309", width=2)
        circ(-3, -19, 2.2, fill="white", outline="")
        circ(5, -24, 2.4, fill="#dc2626", outline="#7f1d1d")
    elif name == "هندوانه":
        c.create_arc(*(lambda a, b: (a[0], a[1], b[0], b[1]))(P(-22, -26), P(22, 18)), start=180, extent=180, style="pieslice",
                     fill="#dc2626", outline="#166534", width=max(3, 5 * sc)) if ang == 0 else None
        if ang != 0:
            poly([(-22, -4), (-19, -16), (-10, -23), (0, -26), (10, -23), (19, -16), (22, -4)], fill="#dc2626", outline="#166534", width=3, smooth=True)
        for (x, y) in ((-10, -9), (0, -13), (9, -8), (-2, -4)):
            circ(x, y, 1.8, fill="#111827", outline="")
    else:
        circ(0, 0, 12, fill="#fbbf24", outline="#92400e", width=2)





def _dark(c, k=0.4):
    return mix(c, "#000000", k)


def draw_topping(c, kind, cx, ty, sc=1.0):
    if kind == "گیلاس":
        c.create_line(cx, ty - 8 * sc, cx + 6 * sc, ty - 22 * sc, fill="#166534", width=max(2, 2 * sc))
        c.create_oval(cx - 9 * sc, ty - 16 * sc, cx + 9 * sc, ty + 1 * sc, fill="#dc2626", outline="#7f1d1d", width=2)
        c.create_oval(cx - 5 * sc, ty - 13 * sc, cx - 1 * sc, ty - 9 * sc, fill="#fecaca", outline="")
    elif kind == "توت‌فرنگی":
        pts = [cx - 11 * sc, ty - 16 * sc, cx + 11 * sc, ty - 16 * sc, cx + 7 * sc, ty - 3 * sc, cx, ty + 2 * sc,
               cx - 7 * sc, ty - 3 * sc]
        c.create_polygon(pts, fill="#e11d48", outline="#7f1d1d", width=2, smooth=True)
        for dx, dy in ((-5, -10), (2, -12), (5, -7), (-1, -6)):
            c.create_oval(cx + dx * sc - 1, ty + dy * sc - 1, cx + dx * sc + 1, ty + dy * sc + 1, fill="#fde68a", outline="")
        c.create_polygon(cx - 8 * sc, ty - 16 * sc, cx, ty - 24 * sc, cx + 8 * sc, ty - 16 * sc, cx, ty - 13 * sc,
                         fill="#22c55e", outline="#166534")
    elif kind == "اسپرینکل":
        rnd = random.Random(7)
        cols = ["#ef4444", "#3b82f6", "#facc15", "#22c55e", "#a855f7", "#fb923c"]
        for _ in range(16):
            x = cx + rnd.uniform(-34, 34) * sc
            y = ty + rnd.uniform(-5, 5) * sc
            dx, dy = rnd.uniform(-4, 4) * sc, rnd.uniform(-2.5, 2.5) * sc
            c.create_line(x - dx, y - dy, x + dx, y + dy, fill=rnd.choice(cols), width=max(2, 3 * sc), capstyle="round")
    elif kind == "شمع":
        c.create_rectangle(cx - 5 * sc, ty - 34 * sc, cx + 5 * sc, ty + 1 * sc, fill="#60a5fa", outline="#1e3a8a", width=2)
        for yy in (-27, -19, -11, -3):
            c.create_line(cx - 5 * sc, ty + yy * sc, cx + 5 * sc, ty + (yy - 5) * sc, fill="white", width=2)
        c.create_line(cx, ty - 34 * sc, cx, ty - 39 * sc, fill="#1f2937", width=2)
        c.create_oval(cx - 5 * sc, ty - 51 * sc, cx + 5 * sc, ty - 38 * sc, fill="#fbbf24", outline="#ea580c", width=2)
        c.create_oval(cx - 2 * sc, ty - 46 * sc, cx + 2 * sc, ty - 40 * sc, fill="#fef9c3", outline="")


def draw_cake_slice(c, X, Y, sc, style):
    st = style or {}
    bc = BATTERS.get(st.get("batter"), "#f6dfa4")
    cc = CREAMS.get(st.get("cream"), "#ff8fbf")

    def P(x, y):
        return X + x * sc, Y + y * sc

    def rect(x0, y0, x1, y1, col, ol=None):
        a, b = P(x0, y0), P(x1, y1)
        c.create_rectangle(a[0], a[1], b[0], b[1], fill=col, outline=ol or _dark(col, 0.35), width=2)

    rect(-17, 4, 17, 15, bc)
    rect(-17, 0, 17, 4, cc)
    rect(-17, -11, 17, 0, bc)
    rect(-18, -18, 18, -11, cc)
    for i in range(5):
        a = P(-14 + i * 7, -11)
        c.create_oval(a[0] - 3.5 * sc, a[1] - 3 * sc, a[0] + 3.5 * sc, a[1] + 3 * sc, fill=cc, outline=_dark(cc, 0.3))
    t = st.get("topping")
    a = P(0, -18)
    if t == "گیلاس":
        c.create_oval(a[0] - 6 * sc, a[1] - 11 * sc, a[0] + 6 * sc, a[1] + 1 * sc, fill="#dc2626", outline="#7f1d1d", width=2)
    elif t == "توت‌فرنگی":
        c.create_polygon(a[0] - 7 * sc, a[1] - 11 * sc, a[0] + 7 * sc, a[1] - 11 * sc, a[0], a[1] + 1 * sc,
                         fill="#e11d48", outline="#7f1d1d", width=2)
    elif t == "اسپرینکل":
        for i, col in enumerate(("#ef4444", "#3b82f6", "#facc15", "#22c55e")):
            c.create_line(a[0] - 12 * sc + i * 8 * sc, a[1] - 2 * sc, a[0] - 9 * sc + i * 8 * sc, a[1] - 5 * sc,
                          fill=col, width=3, capstyle="round")
    elif t == "شمع":
        c.create_rectangle(a[0] - 2.5 * sc, a[1] - 18 * sc, a[0] + 2.5 * sc, a[1], fill="#60a5fa", outline="#1e3a8a")
        c.create_oval(a[0] - 3 * sc, a[1] - 26 * sc, a[0] + 3 * sc, a[1] - 17 * sc, fill="#fbbf24", outline="#ea580c")



# ───────────── کیک‌پزی (نسخه‌ی مرحله‌به‌مرحله) ─────────────
BATTERS = {"موز": "#f9e08b", "توت‌فرنگی": "#f7a8b8", "شکلات": "#7a4a2b", "بلوبری": "#8f87e8",
           "پرتقال": "#fdba5a", "نارگیل": "#f4efe3"}
CREAMS = {"صورتی": "#ff8fbf", "سفید": "#ffffff", "آبی": "#7cc4ff", "زرد": "#ffd84d", "سبز": "#8fe07f",
          "بنفش": "#b99cff"}
TOPPINGS = ["گیلاس", "توت‌فرنگی", "اسپرینکل", "شمع"]
PROMPTS = ["طعم کیک چی باشه؟", "خامه‌ش چه رنگی باشه؟", "با چی تزئینش کنیم؟"]
KINDS = ["batter", "cream", "topping"]


def ease_out(k):
    k = clamp(k, 0.0, 1.0)
    return 1 - (1 - k) ** 3


def ease_in(k):
    k = clamp(k, 0.0, 1.0)
    return k * k


def bounce_out(k):
    k = clamp(k, 0.0, 1.0)
    if k < 1 / 2.75:
        return 7.5625 * k * k
    if k < 2 / 2.75:
        k -= 1.5 / 2.75
        return 7.5625 * k * k + 0.75
    if k < 2.5 / 2.75:
        k -= 2.25 / 2.75
        return 7.5625 * k * k + 0.9375
    k -= 2.625 / 2.75
    return 7.5625 * k * k + 0.984375


def draw_batter_icon(c, name, cx, cy, s=1.0):
    def P(x, y):
        return cx + x * s, cy + y * s

    def poly(pts, **kw):
        flat = []
        for x, y in pts:
            flat += list(P(x, y))
        c.create_polygon(flat, **kw)

    def circ(x, y, r, **kw):
        a = P(x, y)
        c.create_oval(a[0] - r * s, a[1] - r * s, a[0] + r * s, a[1] + r * s, **kw)

    if name == "موز":
        poly([(-26, -12), (-12, -24), (8, -16), (24, 6), (24, 20), (10, 18), (-6, 2), (-22, -4)], fill="#fde047",
             outline="#a16207", width=2, smooth=True)
        poly([(-26, -12), (-18, -22), (-12, -24), (-14, -14)], fill="#78350f", outline="#78350f")
        poly([(24, 20), (24, 8), (28, 22)], fill="#78350f", outline="#78350f")
        poly([(-14, -14), (2, -8), (16, 8)], fill="", outline="#facc15", width=2, smooth=True)
    elif name == "توت‌فرنگی":
        poly([(-20, -14), (20, -14), (22, 0), (10, 20), (0, 26), (-10, 20), (-22, 0)], fill="#e11d48",
             outline="#7f1d1d", width=2, smooth=True)
        for dx, dy in ((-10, -4), (2, -8), (10, 2), (-4, 6), (4, 12), (-11, 8)):
            circ(dx, dy, 1.8, fill="#fde68a", outline="")
        poly([(-14, -14), (-6, -26), (0, -18), (6, -26), (14, -14), (0, -10)], fill="#22c55e", outline="#166534", width=2)
    elif name == "شکلات":
        poly([(-18, -26), (18, -26), (18, 12), (-18, 12)], fill="#78350f", outline="#3f1d0b", width=2)
        for gx in (-6, 6):
            a, b = P(gx, -26), P(gx, 12)
            c.create_line(a[0], a[1], b[0], b[1], fill="#3f1d0b", width=1)
        for gy in (-13, 0):
            a, b = P(-18, gy), P(18, gy)
            c.create_line(a[0], a[1], b[0], b[1], fill="#3f1d0b", width=1)
        poly([(-19, 8), (19, 8), (20, 26), (-20, 26)], fill="#e2e8f0", outline="#94a3b8", width=2)
        poly([(-12, 13), (12, 13), (12, 21), (-12, 21)], fill="#ef4444", outline="")
    elif name == "بلوبری":
        for (x, y) in ((-12, 8), (12, 8), (0, -10)):
            circ(x, y, 14, fill="#4338ca", outline="#1e1b4b", width=2)
            circ(x - 4, y - 5, 3, fill="#a5b4fc", outline="")
            circ(x + 1, y - 9, 3.5, fill="#1e1b4b", outline="")
    elif name == "پرتقال":
        circ(0, 4, 22, fill="#fb923c", outline="#c2410c", width=2)
        circ(-8, -4, 5, fill="#fed7aa", outline="")
        poly([(0, -16), (12, -26), (14, -14)], fill="#22c55e", outline="#166534", width=2)
        circ(0, -17, 2, fill="#78350f", outline="")
    elif name == "نارگیل":
        circ(0, 2, 23, fill="#78350f", outline="#3f1d0b", width=2)
        circ(2, 4, 16, fill="#fffdf5", outline="#3f1d0b", width=2)
        circ(2, 4, 8, fill="#e5e7eb", outline="")
        circ(-14, -14, 2, fill="#3f1d0b", outline="")
        circ(-8, -18, 2, fill="#3f1d0b", outline="")


def draw_cream_icon(c, col, cx, cy, s=1.0):
    o = _dark(col, 0.3) if col != "#ffffff" else "#94a3b8"
    for (w, y, h) in ((30, 14, 14), (24, 2, 13), (17, -9, 12)):
        c.create_oval(cx - w * s, cy + (y - h / 2) * s, cx + w * s, cy + (y + h / 2) * s, fill=col, outline=o, width=2)
    c.create_polygon(cx - 9 * s, cy - 11 * s, cx + 9 * s, cy - 11 * s, cx + 3 * s, cy - 27 * s, cx - 1 * s, cy - 31 * s,
                     fill=col, outline=o, width=2, smooth=True)
    c.create_oval(cx - 18 * s, cy + 6 * s, cx - 8 * s, cy + 11 * s, fill=mix(col, "#ffffff", 0.6), outline="")


def draw_choice_icon(c, kind, val, cx, cy, s=1.0):
    if kind == "batter":
        draw_batter_icon(c, val, cx, cy, s)
    elif kind == "cream":
        draw_cream_icon(c, CREAMS[val], cx, cy, s)
    else:
        if val == "اسپرینکل":
            c.create_oval(cx - 32 * s, cy + 6 * s, cx + 32 * s, cy + 26 * s, fill="#fda4af", outline="#be185d", width=2)
        mult = {"گیلاس": 1.5, "توت‌فرنگی": 1.4, "اسپرینکل": 1.0, "شمع": 0.85}.get(val, 1.0)
        draw_topping(c, val, cx, cy + 18 * s, s * 0.95 * mult)


def cake_draw(c, cx, by, sc=1.0, sponge=None, fill=1.0, frost=None, fk=0.0, topping=None, drop=0.0, W=130):
    Wc, eh = W * sc, 12 * sc
    h1, hm, h2 = 30 * sc, 8 * sc, 30 * sc
    c.create_oval(cx - Wc / 2 - 22 * sc, by - 6 * sc, cx + Wc / 2 + 22 * sc, by + 14 * sc, fill="#f8fafc",
                  outline="#94a3b8", width=2)
    if not sponge or fill <= 0:
        return by - h1 - hm - h2
    col = BATTERS[sponge]

    def cyl(yb, h, cc):
        if h < 1:
            return
        o = _dark(cc, 0.35)
        c.create_oval(cx - Wc / 2, yb - eh, cx + Wc / 2, yb + eh, fill=cc, outline=o, width=2)
        c.create_rectangle(cx - Wc / 2, yb - h, cx + Wc / 2, yb, fill=cc, outline="")
        c.create_line(cx - Wc / 2, yb - h, cx - Wc / 2, yb, fill=o, width=2)
        c.create_line(cx + Wc / 2, yb - h, cx + Wc / 2, yb, fill=o, width=2)
        c.create_oval(cx - Wc / 2, yb - h - eh, cx + Wc / 2, yb - h + eh, fill=mix(cc, "#ffffff", 0.18), outline=o, width=2)

    p1 = clamp(fill / 0.44, 0, 1)
    cyl(by, h1 * p1, col)
    if fill > 0.44:
        cyl(by - h1, hm * clamp((fill - 0.44) / 0.12, 0, 1), "#fffaf0")
    p2 = clamp((fill - 0.56) / 0.44, 0, 1)
    if fill > 0.56:
        cyl(by - h1 - hm, h2 * p2, col)
    ytop = by - h1 - hm - h2
    if frost and fk > 0:
        fc = CREAMS[frost]
        o = _dark(fc, 0.3) if fc != "#ffffff" else "#94a3b8"
        if fk > 0.4:
            kk = (fk - 0.4) / 0.6
            n = 7
            for i in range(n):
                x = cx - Wc / 2 + Wc * (i + 0.5) / n
                t = (x - cx) / (Wc / 2)
                y0 = ytop + eh * math.sqrt(max(0.0, 1 - t * t)) - 2 * sc
                L = (9 + (i * 5) % 14) * sc * kk
                r = Wc / n * 0.46
                c.create_rectangle(x - r, y0, x + r, y0 + L, fill=fc, outline="")
                c.create_oval(x - r, y0 + L - r, x + r, y0 + L + r, fill=fc, outline=o, width=2)
                c.create_line(x - r, y0, x - r, y0 + L, fill=o, width=2)
                c.create_line(x + r, y0, x + r, y0 + L, fill=o, width=2)
        rx = Wc / 2 * (0.12 + 0.88 * ease_out(fk))
        c.create_oval(cx - rx, ytop - eh * rx / (Wc / 2), cx + rx, ytop + eh * rx / (Wc / 2), fill=fc, outline=o, width=2)
        c.create_oval(cx - rx * 0.55, ytop - eh * 0.35, cx + rx * 0.1, ytop + eh * 0.1,
                      fill=mix(fc, "#ffffff", 0.55), outline="")
    if topping:
        draw_topping(c, topping, cx, ytop - 4 * sc - drop, sc * 0.95)
    return ytop


def draw_mold(c, cx, by, sc=1.0, lift=0.0, W=130):
    Wm = W * sc + 18
    top = by - 138 * sc - lift
    bot = by - lift
    x0, x1 = cx - Wm / 2, cx + Wm / 2
    ey = 12 * sc
    c.create_oval(x0, bot - ey, x1, bot + ey, outline="#5b8db3", width=3)
    for xx in (x0, x1):
        c.create_line(xx, top, xx, bot, fill="#5b8db3", width=5)
        c.create_line(xx, top, xx, bot, fill="#e3f4ff", width=2)
    c.create_oval(x0, top - ey, x1, top + ey, outline="#5b8db3", width=5)
    c.create_oval(x0 + 1, top - ey + 1, x1 - 1, top + ey - 1, outline="#e3f4ff", width=2)
    c.create_line(x0 + 14, top + 22, x0 + 14, bot - 26, fill="white", width=5, capstyle="round")
    c.create_line(x0 + 26, top + 30, x0 + 26, top + 62, fill="white", width=3, capstyle="round")


class CakeGame:
    W, H, ROUNDS = 480, 620, 3
    SHOW = [7.0, 6.0, 5.0]
    CX, BY = 240, 300

    def __init__(self, mojo):
        self.m = mojo
        self.win = mojo.win("کیک‌پزی", self.W, self.H, game=True)
        self.cv = tk.Canvas(self.win, width=self.W, height=self.H, bg=CREAM, highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<Motion>", self.on_move)
        self.cv.bind("<Leave>", lambda e: setattr(self, "hover", None))
        self.cv.bind("<Button-1>", self.on_click)
        self.hover = None
        self.hits = []
        self.tile_t, self.tile_pos, self.res, self.fly, self.ok = 0, {}, [False] * 3, None, None
        self.coin_t = None
        self.round = 0
        self.t = 0
        self.score = 0
        self.new_round()
        self.tick()

    # ───── حالت‌ها ─────
    def set_phase(self, ph):
        self.phase, self.pt = ph, 0

    def new_round(self):
        self.round += 1
        self.order = {"batter": random.choice(list(BATTERS)), "cream": random.choice(list(CREAMS)),
                      "topping": random.choice(TOPPINGS)}
        self.sel = {}
        self.step = 0
        self.fly = None
        self.ok = None
        self.set_phase("board_in")
        self.m.snd.play("whoosh", force=True)
        self.m.say("سفارش جدید! خوب نگاه کن!", 2500)

    def tick(self):
        if not alive(self.win):
            return
        self.t += 1
        self.pt += 1
        try:
            self.advance()
            self.draw()
        except Exception:
            log_exc()
        self.win.after(33, self.tick)

    def advance(self):
        ph, pt = self.phase, self.pt
        if ph == "board_in" and pt >= 24:
            self.set_phase("board")
            self.m.snd.play("thud", force=True)
        elif ph == "board" and pt >= self.SHOW[self.round - 1] * 30:
            self.set_phase("board_out")
            self.m.snd.play("whoosh", force=True)
        elif ph == "board_out" and pt >= 20:
            self.set_phase("mold_in")
        elif ph == "mold_in" and pt >= 22:
            self.set_phase("pick")
            self.m.say("حالا خودت بساز!", 2200)
        elif ph == "pour" and pt >= 32:
            self.step = 1
            self.set_phase("pick")
        elif ph == "frost" and pt >= 32:
            self.step = 2
            self.set_phase("pick")
        elif ph == "drop" and pt >= 28:
            self.set_phase("send")
            self.m.snd.play("whoosh", force=True)
        elif ph == "send" and pt >= 30:
            self.verdict()

    # ───── ورودی ─────
    def on_move(self, e):
        self.hover = None
        for key, (x0, y0, x1, y1) in self.hits:
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.hover = key
                break
        self.cv.config(cursor="hand2" if self.hover is not None else "")

    def on_click(self, e):
        self.on_move(e)
        h = self.hover
        if h is None:
            return
        if h == "again":
            self.round, self.score = 0, 0
            self.new_round()
        elif self.phase == "pick" and isinstance(h, int):
            self.choose(h)

    def options(self):
        k = KINDS[self.step]
        return k, (list(BATTERS) if k == "batter" else list(CREAMS) if k == "cream" else list(TOPPINGS))

    def choose(self, idx):
        kind, opts = self.options()
        if idx >= len(opts) or self.tile_t < 14:
            return
        val = opts[idx]
        self.sel[kind] = val
        self.fly = {"kind": kind, "val": val, "from": self.tile_pos.get(idx, (self.CX, 480)), "t0": self.t}
        self.m.snd.play("pop", force=True)
        self.m.pulse(0.1, -0.1)
        self.set_phase({"batter": "pour", "cream": "frost", "topping": "drop"}[kind])
        if kind == "topping":
            self.m.snd.play("boing", force=True)

    def verdict(self):
        res = [self.sel.get(k) == self.order[k] for k in KINDS]
        self.res = res
        self.ok = all(res)
        self.set_phase("verdict")
        m = self.m
        if self.ok:
            self.score += 1
            m.snd.play("yay", force=True)
            style = dict(self.sel)
            m.queue.insert(0, lambda: m.eat("love", random.choice(
                ["اوووم! کیک عالیه! همینو می‌خواستم!", "بهترین کیک عمرم!", "ممم... شیرین و درست!"]), "کیک", style))
            if self.round >= self.ROUNDS:
                m.S["stats"]["games"] += 1
                m.S["stats"]["wins"] += 1
                m.add_xp(8)
                m.add_coins(COIN_WIN)
                self.coin_t = self.t
                m.queue.append(lambda: m.react(f"هر سه تا سفارش رو درست درآوردی! {fa(COIN_WIN)} سکه گرفتی؛ بیا فروشگاه!", "happy", "dance", 110))
            else:
                self.win.after(3200, self.next_round_if_alive)
        else:
            m.snd.play("sad", force=True)
            m.S["stats"]["games"] += 1
            m.add_xp(1)
            m.queue_react("وای نه! کیک خراب شد... مشتری ناراضی رفت!", "sad", "idle", 90)

    def next_round_if_alive(self):
        if alive(self.win) and self.phase == "verdict" and self.ok and self.round < self.ROUNDS:
            self.new_round()

    # ───── نقاشی ─────
    def draw(self):
        c = self.cv
        c.delete("all")
        self.hits = []
        self.tile_pos = getattr(self, "tile_pos", {})
        ph, pt, CX, BY = self.phase, self.pt, self.CX, self.BY
        self.draw_header()
        if ph in ("board_in", "board", "board_out"):
            if ph == "board_in":
                y = -250 + 350 * bounce_out(pt / 24.0)
            elif ph == "board":
                y = 100.0
            else:
                y = 100 + 560 * ease_in(pt / 20.0)
            self.draw_board(CX, y, ph == "board")
            return
        # قالب و کیک
        sc = 1.1
        lift = 0.0
        mx = CX
        if ph == "mold_in":
            mx = CX + 420 * (1 - ease_out(pt / 22.0))
        if ph == "send":
            lift = 280 * ease_in(pt / 30.0)
        if ph == "verdict":
            self.draw_verdict()
            return
        fill, fk, drop = 0.0, 0.0, 0.0
        if ph == "pour":
            fill = ease_out(pt / 32.0)
        elif self.sel.get("batter"):
            fill = 1.0
        if ph == "frost":
            fk = ease_out(pt / 32.0)
        elif self.sel.get("cream"):
            fk = 1.0
        top = self.sel.get("topping")
        if ph == "drop":
            drop = 150 * (1 - bounce_out(pt / 28.0))
        cx_cake = mx
        cake_draw(c, cx_cake, BY, sc, self.sel.get("batter"), fill, self.sel.get("cream"), fk, top, drop)
        if ph == "send" and False:
            pass
        draw_mold(c, mx, BY, sc, lift)
        if ph == "pick":
            self.draw_tiles()
        self.draw_fly()

    def draw_header(self):
        c, CX = self.cv, self.CX
        for i in range(3):
            x, y = CX + (i - 1) * 96, 36
            cur = (self.phase in ("pick", "pour", "frost", "drop") and i == self.step) or (
                self.phase == "pick" and i == self.step)
            ring = TEAL if cur else "#d6c9a6"
            if self.phase == "verdict" and self.ok is not None:
                ring = "#16a34a" if self.res[i] else "#dc2626"
            r = 25 + (2 * math.sin(self.t / 4.0) if cur else 0)
            c.create_oval(x - r, y - r, x + r, y + r, fill="white", outline=ring, width=4)
            k = KINDS[i]
            v = self.sel.get(k)
            if v and not (self.fly and self.fly["kind"] == k and self.t - self.fly["t0"] < 14):
                draw_choice_icon(c, k, v, x, y + (3 if k == "topping" else 0), 0.55)
            else:
                c.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#e7dcc0", outline="")
            if i < 2:
                c.create_line(x + 30, y, x + 66, y, fill="#d6c9a6", width=3, dash=(4, 3))
        ph = self.phase
        if ph in ("board_in", "board", "board_out", "mold_in"):
            txt = "سفارش مشتری رو یادت بمونه!"
        elif ph == "verdict":
            txt = "درسته! آفرین!" if self.ok else "اشتباه شد!"
        elif ph in ("send",):
            txt = "کیک رو می‌فرستیم..."
        else:
            txt = PROMPTS[min(self.step, 2)]
        c.create_text(CX, 86, text=txt, font=("Segoe UI", 15, "bold"),
                      fill=("#16a34a" if self.ok else "#dc2626") if ph == "verdict" else INK)

    def draw_board(self, cx, y, timer):
        c = self.cv
        w, h = 310, 236
        for sx in (-1, 1):
            c.create_line(cx + sx * (w / 2 - 34), y, cx + sx * (w / 2 - 34), y - 400, fill="#7c4a1c", width=5)
        x0, y0, x1, y1 = cx - w / 2, y, cx + w / 2, y + h
        c.create_rectangle(x0 + 6, y0 + 8, x1 + 6, y1 + 8, fill="#d9ccaa", outline="")
        c.create_rectangle(x0, y0, x1, y1, fill=WOOD, outline=WOOD_D, width=4)
        c.create_rectangle(x0 + 10, y0 + 10, x1 - 10, y1 - 10, fill=CREAM, outline=WOOD_D, width=2)
        for sx in (x0 + 5, x1 - 5):
            c.create_oval(sx - 3, y0 + 5, sx + 3, y0 + 11, fill=WOOD_D, outline="")
        c.create_text(cx, y0 + 28, text=f"سفارش {fa(self.round)} از {fa(self.ROUNDS)}", font=("Segoe UI", 11, "bold"), fill=INK)
        o = self.order
        cake_draw(c, cx, y1 - 36, 0.95, o["batter"], 1.0, o["cream"], 1.0, o["topping"], 0.0)
        if timer:
            frac = clamp(1 - self.pt / (self.SHOW[self.round - 1] * 30.0), 0, 1)
            c.create_rectangle(x0 + 24, y1 - 22, x1 - 24, y1 - 15, fill="#e7dcc0", outline="")
            c.create_rectangle(x0 + 24, y1 - 22, x0 + 24 + (w - 48) * frac, y1 - 15,
                               fill="#ef4444" if frac < 0.35 else "#f59e0b", outline="")
            c.create_text(x1 - 34, y0 + 30, text=fa(int(math.ceil(frac * self.SHOW[self.round - 1]))),
                          font=("Segoe UI", 18, "bold"), fill="#ef4444")

    def draw_tiles(self):
        c = self.cv
        kind, opts = self.options()
        n = len(opts)
        cols = 2 if n == 4 else 3
        rows = (n + cols - 1) // cols
        tw, th = 126, 108
        gx, gy = 144, 122
        y0 = 372
        self.tile_t = self.pt
        self.tile_pos = {}
        for i, val in enumerate(opts):
            r, cc = divmod(i, cols)
            cnt = cols if r < rows - 1 else n - cols * (rows - 1)
            cx = self.CX + (cc - (cnt - 1) / 2.0) * gx
            cy = y0 + 54 + r * gy * 0.96
            k = clamp((self.pt - i * 2) / 14.0, 0, 1)
            cy += (1 - ease_out(k)) * 300
            hov = self.hover == i
            s = 1.07 if hov else 1.0
            hw, hh = tw / 2 * s, th / 2 * s
            self.hits.append((i, (cx - hw, cy - hh, cx + hw, cy + hh)))
            self.tile_pos[i] = (cx, cy)
            c.create_rectangle(cx - hw + 4, cy - hh + 6, cx + hw + 4, cy + hh + 6, fill="#e2d6b5", outline="")
            c.create_rectangle(cx - hw, cy - hh, cx + hw, cy + hh, fill="white", outline=TEAL if hov else "#d6c9a6",
                               width=4 if hov else 3)
            draw_choice_icon(c, kind, val, cx, cy + (4 if kind == "topping" else 0), 1.45 * s)

    def draw_fly(self):
        f = self.fly
        if not f:
            return
        k = (self.t - f["t0"]) / 14.0
        if k >= 1:
            return
        i = KINDS.index(f["kind"])
        tx, ty = self.CX + (i - 1) * 96, 36
        e = ease_out(k)
        x = lerp(f["from"][0], tx, e)
        y = lerp(f["from"][1], ty, e) - math.sin(math.pi * e) * 40
        draw_choice_icon(self.cv, f["kind"], f["val"], x, y, lerp(1.4, 0.55, e))

    def draw_verdict(self):
        c, CX = self.cv, self.CX
        o = self.order
        pk = min(1.0, self.pt / 14.0)
        # کیک تو (چپ) و سفارش (راست)
        bx = 130
        cake_draw(c, bx, 300, 0.95, self.sel.get("batter"), 1.0, self.sel.get("cream"), 1.0, self.sel.get("topping"), 0.0)
        c.create_text(bx, 330, text="کیک تو", font=("Segoe UI", 11, "bold"), fill="#64748b")
        ox = 350
        c.create_rectangle(ox - 90, 118, ox + 90, 322, fill=CREAM, outline=WOOD_D, width=4)
        c.create_rectangle(ox - 96, 112, ox + 96, 118, fill=WOOD, outline=WOOD_D)
        cake_draw(c, ox, 296, 0.8, o["batter"], 1.0, o["cream"], 1.0, o["topping"], 0.0)
        c.create_text(ox, 338, text="سفارش مشتری", font=("Segoe UI", 11, "bold"), fill="#64748b")
        if self.ok and self.round >= self.ROUNDS and self.coin_t is not None:
            k = bounce_out((self.t - self.coin_t) / 20.0)
            cyy = 150 - 40 * (1 - k)
            draw_coin(c, 70, cyy, 20)
            c.create_text(100, cyy, text=f"+{fa(COIN_WIN)} سکه", anchor="w", font=("Segoe UI", 15, "bold"), fill="#b45309")
        # مقایسه‌ی سه مرحله
        for i, k in enumerate(KINDS):
            x = CX + (i - 1) * 140
            good = self.res[i]
            c.create_rectangle(x - 56, 366, x + 56, 560, fill="white", outline="#16a34a" if good else "#dc2626", width=3)
            c.create_text(x, 380, text="سفارش", font=("Segoe UI", 8), fill="#94a3b8")
            c.create_text(x, 546, text="تو", font=("Segoe UI", 8), fill="#94a3b8")
            draw_choice_icon(c, k, o[k], x, 416 + (4 if k == "topping" else 0), 1.0)
            c.create_text(x, 466, text="✓" if good else "✗", font=("Segoe UI", 20, "bold"),
                          fill="#16a34a" if good else "#dc2626")
            if good:
                draw_choice_icon(c, k, self.sel[k], x, 512 + (4 if k == "topping" else 0), 0.8)
            else:
                draw_choice_icon(c, k, self.sel[k], x, 512 + (4 if k == "topping" else 0), 0.8)
        if (not self.ok) or self.round >= self.ROUNDS:
            hov = self.hover == "again"
            bx0, by0, bx1, by1 = CX - 100, 574, CX + 100, 610
            self.hits.append(("again", (bx0, by0, bx1, by1)))
            c.create_rectangle(bx0, by0, bx1, by1, fill="#0f766e" if hov else TEAL, outline="")
            c.create_text(CX, 592, text="دوباره بازی کنیم؟", font=("Segoe UI", 12, "bold"), fill="white")



def draw_coin(c, cx, cy, r):
    c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#fbbf24", outline="#b45309", width=2)
    c.create_oval(cx - r * 0.68, cy - r * 0.68, cx + r * 0.68, cy + r * 0.68, outline="#f59e0b", width=max(1, int(r / 7)))
    pts = []
    for k in range(10):
        rr = r * (0.42 if k % 2 == 0 else 0.18)
        th = -math.pi / 2 + k * math.pi / 5
        pts += [cx + math.cos(th) * rr, cy + math.sin(th) * rr]
    c.create_polygon(pts, fill="#f59e0b", outline="")
    c.create_arc(cx - r * 0.8, cy - r * 0.8, cx + r * 0.8, cy + r * 0.8, start=105, extent=50, style="arc",
                 outline="#fffbeb", width=max(1, int(r / 6)))


def draw_gift_box(c, cx, cy, s, tag):
    """جعبه‌ی کادویی با برچسب (تمبر) کوچیک رنگی"""
    c.create_rectangle(cx - 24 * s, cy - 4 * s, cx + 24 * s, cy + 24 * s, fill="#d6a76b", outline="#8a5a22", width=2)
    c.create_rectangle(cx - 27 * s, cy - 15 * s, cx + 27 * s, cy - 3 * s, fill="#e7bd82", outline="#8a5a22", width=2)
    c.create_rectangle(cx - 4.5 * s, cy - 15 * s, cx + 4.5 * s, cy + 24 * s, fill="#ef4444", outline="#7f1d1d", width=1)
    c.create_oval(cx - 15 * s, cy - 28 * s, cx - 1 * s, cy - 14 * s, outline="#ef4444", width=max(2, int(3 * s)))
    c.create_oval(cx + 1 * s, cy - 28 * s, cx + 15 * s, cy - 14 * s, outline="#ef4444", width=max(2, int(3 * s)))
    c.create_oval(cx - 3.5 * s, cy - 18 * s, cx + 3.5 * s, cy - 11 * s, fill="#dc2626", outline="#7f1d1d")
    # برچسب کج روی گوشه‌ی جعبه
    tx, ty = cx + 17 * s, cy + 12 * s
    ang = -0.35
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for (x, y) in ((-11, -9), (11, -9), (11, 9), (-11, 9)):
        pts += [tx + (x * ca - y * sa) * s, ty + (x * sa + y * ca) * s]
    c.create_polygon(pts, fill=tag, outline=_dark(tag, 0.4), width=2)
    hx, hy = tx + (-7 * ca + 0 * sa) * s, ty + (-7 * sa) * s
    c.create_oval(hx - 2 * s, hy - 2 * s, hx + 2 * s, hy + 2 * s, fill="white", outline="")
    sp = []
    for k in range(10):
        rr = (5 if k % 2 == 0 else 2.2) * s
        th = -math.pi / 2 + k * math.pi / 5
        sp += [tx + 2 * s + math.cos(th) * rr, ty + math.sin(th) * rr]
    c.create_polygon(sp, fill="white", outline="")


class Sign:
    def __init__(self, win, w, h, cb, hint, timeout):
        self.win, self.w, self.h, self.cb, self.hint, self.timeout = win, w, h, cb, hint, timeout
        self.done, self.result, self.hinted = False, None, False
        self.x, self.y, self.ty, self.vy, self.dropping, self.stand_x = 0.0, -float(h), 0.0, 0.0, True, 0.0


class Mojo:
    def __init__(self, selftest=False):
        self.S = load_state()
        for k in list(self.S["facts"]):
            self.S["facts"][k] = bmp(self.S["facts"][k])
        self.snd = Sounds(self.S.get("sound", 2))
        self._blip_id = 0
        self.cur_event = None
        self.ensure_today()
        self.root = tk.Tk()
        self.root.title("Mojo")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-transparentcolor", TRANSP)
        except tk.TclError:
            pass
        self.root.configure(bg=TRANSP)
        self.cv = tk.Canvas(self.root, width=CW, height=CH, bg=TRANSP, highlightthickness=0, bd=0)
        self.cv.pack()

        self.t = 0
        self._area, self._area_t = None, 0
        self.refresh_area()
        l, tp, r, b = self.area()
        self.x, self.y = r - CW - 40, b - FOOT
        self.last_geo = None
        self.face, self.anim, self.expr = -1, "idle", "happy"
        self.sx = self.sy = 1.0
        self.S["look"] = {**DEFAULT["look"], **(self.S.get("look") or {})}
        oc = {x.lower() for x in self.S.get("owned_colors", [])}
        for v in self.S["look"].values():
            oc.add(v.lower())
        self.S["owned_colors"] = sorted(oc)
        self.jet, self.chute = None, None
        self.preview = None
        self.set_color(self.body_col())
        self.prop = None
        self.bubble, self.mouth_until = None, 0
        self.gen, self.queue = None, []
        self.sign, self.games, self.catch = None, [], None
        self.on_window, self.win_lim, self.floor = None, None, None
        self.dragging, self._drag = False, None
        self.pokes = []
        self.blink = 0
        self.q = queue.Queue()
        self.chat_win, self.chat_hist = None, []
        self.last_event = None
        self.next_event = time.time() + random.uniform(50, 80)
        self.study = None
        self.egg, self.onboarding = None, False
        self.splats = []
        self.food = None
        self.throwing = False
        self.v_auto = tk.BooleanVar(value=autostart_enabled())
        self.v_mouse = tk.BooleanVar(value=self.S["mouse_ok"])
        self.v_window = tk.BooleanVar(value=self.S["window_ok"])
        self.v_chaos = tk.IntVar(value=self.S["chaos"])
        self.v_sound = tk.IntVar(value=self.S["sound"])
        self.v_track = tk.BooleanVar(value=self.S.get("track_ok", False))
        self.usage_t = time.time()
        self.usage_save = time.time()

        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.popup)

        if not selftest:
            if self.S["first_run"]:
                self.onboarding = True
                self.x, self.y = -3000.0, -3000.0
                self.queue.append(self.ev_hatch)
            else:
                self.queue.append(self.ev_greet)
            self.root.after(33, self.tick)
            self.root.after(1000, self.slow)

    def save(self):
        save_state(self.S)

    def refresh_area(self):
        wa = work_area()
        if wa and wa[2] - wa[0] > 200:
            self._area = wa
        else:
            self._area = (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())

    def area(self):
        return self._area

    def ground(self):
        return self._area[3] - 2

    def fx(self):
        return self.x + CXC

    def fy(self):
        return self.y + FOOT

    def put(self, fx, fy):
        self.x, self.y = fx - CXC, fy - FOOT

    def set_color(self, c):
        self.color = c
        self.edge = mix(c, "#062b2b", 0.6)
        self.hl = mix(c, "#ffffff", 0.55)
        self.belly = mix(c, "#ffffff", 0.3)

    def pulse(self, dx, dy):
        self.sx = clamp(self.sx + dx, 0.6, 1.5)
        self.sy = clamp(self.sy + dy, 0.6, 1.5)

    def say(self, text, ms=None, delay=0):
        text = short(text)
        tid = self.cv.create_text(0, 0, text=text, font=BF, width=230, justify="center")
        bb = self.cv.bbox(tid)
        self.cv.delete(tid)
        w, h = (bb[2] - bb[0], bb[3] - bb[1]) if bb else (100, 20)
        dur = ms or max(3500, min(11000, len(text) * 85))
        self.bubble = {"text": text, "w": w, "h": h, "until": time.time() + dur / 1000.0}
        self.mouth_until = self.t + int(dur / 33 * 0.6)
        self.talk_blips(text, delay)

    def talk_blips(self, text, delay=0):
        self._blip_id += 1
        if not (self.snd.level and winsound):
            return
        my = self._blip_id
        letters = [ch for ch in text if ch.isalpha()][:26]

        def go(i):
            if my != self._blip_id or i >= len(letters) or not alive(self.root):
                return
            self.snd.play(f"b{ord(letters[i]) % 6}", force=True)
            self.root.after(random.choice([70, 80, 95]), go, i + 2)

        self.root.after(max(1, int(delay)), go, 0)

    def busy(self):
        return bool((self.sign and not self.sign.done) or self.catch or any(alive(w) for w in self.games))

    def level(self):
        return self.S["xp"] // 100 + 1

    def add_xp(self, n):
        old = self.level()
        self.S["xp"] += n
        self.save()
        if self.level() > old:
            self.snd.play("yay")
            self.queue.insert(0, lambda: self.react(f"سطحم رفت بالا! الان سطح {fa(self.level())} هستیم!", "happy", "dance", 80))

    def ensure_today(self):
        d = today_str()
        if self.S.get("today", {}).get("date") != d:
            self.S["today"] = {"date": d, "rps_wins": 0, "ttt_wins": 0, "math_best": 0, "reaction_best": 9999,
                               "guess_best": 99, "catches": 0, "drawings": 0, "quiz_right": 0}

    def current_streak(self):
        y = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        return self.S["streak"] if self.S["last_done"] in (today_str(), y) else 0

    def today_challenge(self):
        self.ensure_today()
        t = self.S["today"]
        if "ch" not in t:
            pool = list(CHALLENGES)
            for k, tpl in PERSONAL_CH.items():
                v = self.S["facts"].get(k)
                if v:
                    pool += [(tpl.format(v=v), None, None, None)] * 2
            t["ch"] = list(random.Random(today_str()).choice(pool))
            self.save()
        return tuple(t["ch"])

    def record(self, key, val):
        self.ensure_today()
        t = self.S["today"]
        if key in ("rps_wins", "ttt_wins", "catches", "drawings", "quiz_right"):
            t[key] += val
        elif key in ("math_best",):
            t[key] = max(t[key], val)
        else:
            t[key] = min(t[key], val)
        self.save()
        self.check_auto_challenge()

    def check_auto_challenge(self):
        if self.S["last_done"] == today_str():
            return
        _, key, op, thr = self.today_challenge()
        if not key:
            return
        v = self.S["today"][key]
        if (v >= thr) if op == ">=" else (v <= thr):
            self.complete_challenge()

    def complete_challenge(self):
        d = today_str()
        if self.S["last_done"] == d:
            return
        y = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        self.S["streak"] = self.S["streak"] + 1 if self.S["last_done"] == y else 1
        self.S["best_streak"] = max(self.S["best_streak"], self.S["streak"])
        self.S["last_done"] = d
        gain = 30 + min(self.S["streak"], 10) * 3
        self.snd.play("yay")
        self.save()
        self.add_xp(gain)
        self.queue.insert(0, lambda: self.react(
            f"چالش امروز انجام شد! {fa(gain)} امتیاز. استریک: {fa(self.S['streak'])} روز", "happy", "dance", 120))

    def draw(self):
        c, t = self.cv, self.t
        c.delete("all")
        anim, expr, face = self.anim, self.expr, self.face
        body, edge = self.color, self.edge
        cx, base = CXC, FOOT
        sx, sy = self.sx, self.sy
        br = math.sin(t / 9.0) * 0.025
        if anim == "sleep":
            br = math.sin(t / 20.0) * 0.05
            sy *= 0.82
        elif anim == "sit":
            sy *= 0.9
        sy *= 1 + br
        sx *= 1 - br
        hop = 0.0
        if anim == "dance":
            hop = -abs(math.sin(t / 3.5)) * 16
        elif anim == "run":
            hop = -abs(math.sin(t / 2.6)) * 9
        elif anim == "walk":
            hop = -abs(math.sin(t / 4.2)) * 6
        airborne = anim in ("jump", "fall", "fly", "held", "chute")
        bw, bh = BW * sx, BH * sy
        yc = base - 14 - bh + hop
        if anim == "sit":
            yc += 5
        if anim == "sleep":
            yc += 3
        if anim == "read":
            yc -= 3

        if not airborne:
            c.create_oval(cx - bw * 0.95, base - 4, cx + bw * 0.95, base + 6, fill="#2b2f36", outline="")
        ph = math.sin(t / (2.6 if anim == "run" else 4.2))
        fy = base - 8 + hop
        for side in (-1, 1):
            lift, off = 0.0, 0.0
            if anim in ("walk", "run"):
                lift = max(0.0, ph * side) * 8
                off = ph * side * 6
            elif anim == "dance":
                lift = max(0.0, math.sin(t / 3.5 + (0 if side < 0 else math.pi))) * 8
            elif anim in ("jump", "fall", "fly"):
                lift = 6
            elif anim == "chute":
                lift = -2 + math.sin(t / 5.0) * 2
            elif anim == "held":
                off, lift = math.sin(t / 3.0 + side) * 4, -6 + math.sin(t / 3.0 + side) * 3
            if anim in ("sit", "read"):
                c.create_oval(cx + side * bw * 0.85 - 11, base - 14, cx + side * bw * 0.85 + 11, base - 2,
                              fill=body, outline=edge, width=3)
                continue
            lx = cx + side * 20 * sx + off
            c.create_oval(lx - 12, fy - 6 - lift, lx + 12, fy + 6 - lift, fill=body, outline=edge, width=3)
        top = yc - bh
        for i in (-1, 0, 1):
            sway = math.sin(t / 7.0 + i) * 4 + (face * 3)
            x0 = cx + i * 9 * sx
            c.create_line(x0, top + 4, x0 + sway, top - 10, x0 + sway * 1.6 + i * 3, top - 20,
                          smooth=True, width=4, fill=edge, capstyle="round")
        jt = self.jet
        if jt:
            wk = clamp(jt["wear"] / 12.0, 0.0, 1.0)
            for side in (-1, 1):
                jx = cx + side * bw * (1.25 - 0.33 * wk)
                y0, y1 = yc - bh * 0.55 * wk, yc + bh * 0.5 * wk
                wd = 11 * wk
                if wd < 1:
                    continue
                c.create_rectangle(jx - wd, y0, jx + wd, y1, fill="#cbd5e1", outline="#475569", width=2)
                c.create_rectangle(jx - wd, y0 + 10 * wk, jx + wd, y0 + 16 * wk, fill="#ef4444", outline="")
                c.create_polygon(jx - wd, y0, jx + wd, y0, jx, y0 - 13 * wk, fill="#ef4444", outline="#7f1d1d", width=2)
                c.create_polygon(jx - wd + 3, y1, jx + wd - 3, y1, jx + wd - 6, y1 + 8 * wk, jx - wd + 6, y1 + 8 * wk,
                                 fill="#475569", outline="")
                if jt["on"]:
                    ln = (26 + 14 * abs(math.sin(t * 0.9 + side))) * (1.4 if anim == "fly" else 0.9)
                    c.create_polygon(jx - wd + 3, y1 + 8, jx + wd - 3, y1 + 8, jx, y1 + 8 + ln, fill="#fb923c", outline="")
                    c.create_polygon(jx - wd + 7, y1 + 8, jx + wd - 7, y1 + 8, jx, y1 + 8 + ln * 0.62, fill="#fde047", outline="")
        pts = []
        for i in range(28):
            a = 2 * math.pi * i / 28
            wob = 1 + 0.03 * math.sin(t / 7.0 + i * 1.7)
            px = cx + bw * math.cos(a) * wob
            py = yc + bh * math.sin(a) * wob
            if math.sin(a) > 0.85:
                py = yc + bh * 0.85 * wob + (bh * 0.15)
            pts += [px, py]
        c.create_polygon(pts, smooth=True, fill=body, outline=edge, width=3)
        c.create_oval(cx - bw * 0.58, yc - bh * 0.72, cx - bw * 0.2, yc - bh * 0.38, fill=self.hl, outline="")
        c.create_oval(cx - bw * 0.42, yc + bh * 0.15, cx + bw * 0.42, yc + bh * 0.8, fill=self.belly, outline="")

        ey = yc - bh * 0.22
        exs = [(cx + face * 5 - 16 * sx, 13), (cx + face * 5 + 15 * sx, 10)]
        try:
            px, py = self.root.winfo_pointerxy()
            dxp = px - (self.x + cx)
            dyp = py - (self.y + ey)
        except Exception:
            dxp = dyp = 0
        dd = math.hypot(dxp, dyp) or 1.0
        ox, oy = dxp / dd * min(4.5, dd / 40), dyp / dd * min(4.5, dd / 40)
        if anim == "read":
            scan = (t * 0.045) % 1.0                # چشم‌ها خط به خط از راست به چپ می‌خونن
            ox, oy = (1 - scan * 2) * 2.6, 3.0
        closed = anim == "sleep" or self.blink > 0
        for ex, r in exs:
            if closed:
                c.create_arc(ex - r, ey - r * 0.4, ex + r, ey + r * 0.8, start=200, extent=140, style="arc",
                             outline=INK, width=3)
            elif expr == "happy" and (anim in ("dance", "wave") or (t % 400 < 120 and anim != "read")):
                c.create_arc(ex - r, ey - r * 0.2, ex + r, ey + r, start=20, extent=140, style="arc",
                             outline=INK, width=4)
            elif expr == "dizzy":
                c.create_oval(ex - r, ey - r, ex + r, ey + r, fill="white", outline=INK, width=2)
                sp_ = []
                for k_ in range(34):
                    a_ = k_ * 0.55 + t * 0.55
                    rr_ = r * 0.9 * k_ / 34
                    sp_ += [ex + math.cos(a_) * rr_, ey + math.sin(a_) * rr_]
                c.create_line(sp_, fill=INK, width=2, smooth=True)
            elif expr == "glitch":
                j = random.randint(-3, 3)
                c.create_line(ex - r + j, ey - r, ex + r + j, ey + r, fill="#e11d48", width=4)
                c.create_line(ex + r + j, ey - r, ex - r + j, ey + r, fill="#e11d48", width=4)
            else:
                rr = r + (3 if expr == "surprised" else 0)
                c.create_oval(ex - rr, ey - rr, ex + rr, ey + rr, fill="white", outline=INK, width=2)
                pr = rr * (0.35 if expr == "surprised" else 0.55)
                pxx, pyy = ex + ox * (rr / 10.0) * 1.6, ey + oy * (rr / 10.0) * 1.6
                c.create_oval(pxx - pr, pyy - pr, pxx + pr, pyy + pr, fill=self.lk("eye"), outline="")
                c.create_oval(pxx - pr * 0.1, pyy - pr * 0.75, pxx + pr * 0.45, pyy - pr * 0.1, fill="white", outline="")
                if expr in ("sneaky", "sleepy"):
                    c.create_rectangle(ex - rr - 1, ey - rr - 1, ex + rr + 1, ey - rr * 0.05, fill=body, outline="")
                    c.create_line(ex - rr, ey - rr * 0.05, ex + rr, ey - rr * 0.05, fill=INK, width=3)
                elif expr == "sad":
                    c.create_line(ex - rr, ey - rr - 4 + (0 if ex < cx else 6), ex + rr, ey - rr + 2 - (0 if ex < cx else 6),
                                  fill=INK, width=3)
        mx, my = cx + face * 4, yc + bh * 0.32
        talking = t < self.mouth_until and anim != "sleep"
        if anim == "sleep":
            c.create_oval(mx - 4, my - 3, mx + 4, my + 4 + math.sin(t / 20.0) * 2, outline=INK, width=2)
        elif talking:
            h = 4 + abs(math.sin(t / 2.0)) * 11
            c.create_oval(mx - 11, my - h / 2, mx + 11, my + h / 2, fill="#134e4a", outline=INK, width=2)
            c.create_oval(mx - 6, my + h / 2 - 5, mx + 6, my + h / 2 + 1, fill="#fb7185", outline="")
        elif expr == "eat":
            h = 3 + abs(math.sin(t / 2.5)) * 7
            c.create_oval(mx - 8, my - h, mx + 8, my + h, fill="#134e4a", outline=INK, width=2)
        elif expr == "surprised":
            c.create_oval(mx - 6, my - 7, mx + 6, my + 7, fill="#134e4a", outline=INK, width=2)
        elif expr == "sad":
            c.create_arc(mx - 10, my, mx + 10, my + 16, start=20, extent=140, style="arc", outline=INK, width=3)
        elif expr == "dizzy":
            zz = []
            for i in range(10):
                zz += [mx - 14 + i * 3, my + 3 + math.sin(t * 0.5 + i) * 3]
            c.create_line(zz, fill=INK, width=3, smooth=True)
        elif expr == "glitch":
            zz = []
            for i in range(9):
                zz += [mx - 16 + i * 4, my + (4 if i % 2 else -4) + random.randint(-2, 2)]
            c.create_line(zz, fill=INK, width=3)
        elif expr == "sneaky":
            c.create_arc(mx - 10, my - 6, mx + 14, my + 8, start=210, extent=130, style="arc", outline=INK, width=3)
        else:
            c.create_arc(mx - 13, my - 9, mx + 13, my + 9, start=200, extent=140, style="arc", outline=INK, width=3)
        if expr in ("happy", "eat") or talking:
            for s in (-1, 1):
                c.create_oval(cx + s * bw * 0.68 - 6, my - 6, cx + s * bw * 0.68 + 6, my + 1, fill=self.lk("cheek"), outline="")

        if expr == "dizzy":
            for i in range(3):
                a_ = t * 0.16 + i * 2.094
                sx_, sy_ = cx + math.cos(a_) * 38, top - 6 + math.sin(a_) * 9
                pts_ = []
                for k_ in range(10):
                    rr_ = 8 if k_ % 2 == 0 else 3.4
                    th_ = -math.pi / 2 + k_ * math.pi / 5
                    pts_ += [sx_ + math.cos(th_) * rr_, sy_ + math.sin(th_) * rr_]
                c.create_polygon(pts_, fill="#fde047", outline="#ca8a04", width=1)
        shy = yc + bh * 0.12
        arms = {-1: (cx - bw * 0.95 - 12, shy + 16 + math.sin(t / 9.0) * 2),
                1: (cx + bw * 0.95 + 12, shy + 16 + math.sin(t / 9.0 + 1) * 2)}
        if anim in ("walk", "run"):
            s = math.sin(t / (2.6 if anim == "run" else 4.2)) * 10
            arms = {-1: (cx - bw - 8, shy + 10 + s), 1: (cx + bw + 8, shy + 10 - s)}
        elif anim == "wave":
            arms[1] = (cx + bw + 16 + math.sin(t / 2.5) * 9, shy - 34)
        elif anim == "dance":
            s = math.sin(t / 3.5)
            arms = {-1: (cx - bw - 16, shy - 18 - s * 16), 1: (cx + bw + 16, shy - 18 + s * 16)}
        elif anim == "held":
            arms = {-1: (cx - bw - 8, shy - 40), 1: (cx + bw + 8, shy - 40)}
        elif anim == "fall" or anim == "jump":
            arms = {-1: (cx - bw - 14, shy - 16), 1: (cx + bw + 14, shy - 16)}
        elif anim == "chute":
            arms = {-1: (cx - bw - 6, shy - 52), 1: (cx + bw + 6, shy - 52)}
        elif anim == "fly":
            arms = {-1: (cx - bw - 14, shy - 4), 1: (cx + bw + 14, shy - 4)}
        elif anim == "cheer":
            arms = {-1: (cx - bw - 10, shy - 30), 1: (cx + bw + 10, shy - 30)}
        arm_ov = self.draw_study_scene(c, cx, base, yc, bw, bh, hop)
        if arm_ov:
            arms.update(arm_ov)
        fd = self.food
        fs = face
        food_at = None
        if fd and not fd.get("drop"):
            k = fd["k"]
            side_pos = (cx + fs * (bw + 12), shy + 20)
            mouth_pos = (mx + fs * 14, my + 16)
            arms[fs] = (lerp(side_pos[0], mouth_pos[0], k), lerp(side_pos[1], mouth_pos[1], k) - math.sin(math.pi * k) * 10)
            food_at = (arms[fs][0] - fs * 3, arms[fs][1] - 12)
            fd["pos"] = food_at
        prop_box = None
        if self.prop:
            tid = c.create_text(0, 0, text=self.prop, font=("Segoe UI", 9, "bold"), width=130)
            bb = c.bbox(tid)
            c.delete(tid)
            pw = (bb[2] - bb[0]) + 16 if bb else 60
            ph_ = (bb[3] - bb[1]) + 10 if bb else 22
            pcy = top - 34
            prop_box = (cx, pcy, pw, ph_)
            arms = {-1: (cx - pw / 2 + 6, pcy + ph_ / 2), 1: (cx + pw / 2 - 6, pcy + ph_ / 2)}
        ch = self.chute
        if ch:
            fold = clamp(ch.get("fold", 0) / 18.0, 0.0, 1.0)
            kopen = clamp(ch["t"] / 10.0, 0.0, 1.0)
            sway = ch.get("sway", 0.0)
            ccx, cyb = cx + sway, top - 38 + fold * (base - top + 30)
            Wc, Hc = 66 * kopen * (1 + fold * 0.3), 50 * kopen * (1 - fold * 0.85)
            cols_ = [ch["color"], "#ffffff"]
            if Wc > 3:
                xs = [-Wc + 2 * Wc * i / 6 for i in range(7)]
                for i in range(6):
                    ptsw = [(ccx + xs[i], cyb)]
                    for j in range(5):
                        xx = xs[i] + (xs[i + 1] - xs[i]) * j / 4
                        ptsw.append((ccx + xx, cyb - Hc * math.sqrt(max(0.0, 1 - (xx / Wc) ** 2))))
                    ptsw.append((ccx + xs[i + 1], cyb))
                    flat = [v for p in ptsw for v in p]
                    c.create_polygon(flat, fill=cols_[i % 2], outline="#7f1d1d" if i % 2 == 0 else "#94a3b8", width=2)
                if fold < 0.5:
                    for i in (0, 2, 4, 6):
                        px_, py_ = ccx + xs[i], cyb
                        tx_, ty_ = (arms[-1] if i < 3 else arms[1]) if i in (0, 6) else (cx + (-8 if i < 3 else 8), top + 6)
                        c.create_line(px_, py_, tx_, ty_, fill="#475569", width=1)
        for s in (-1, 1):
            sxp, syp = cx + s * bw * 0.85, shy + 6
            hx, hy = arms[s]
            c.create_line(sxp, syp, hx, hy, width=11, fill=edge, capstyle="round")
            c.create_line(sxp, syp, hx, hy, width=6, fill=body, capstyle="round")
            if food_at and s == fs:
                draw_food(c, fd["name"], food_at[0], food_at[1], 1.25 * (1 - 0.26 * fd["bites"]), -fs * 0.18, fd.get("style"))
            c.create_oval(hx - 6, hy - 6, hx + 6, hy + 6, fill=body, outline=edge, width=2)
        if fd:
            if fd.get("drop"):
                fd["vy"] += 1.4
                fd["pos"] = (fd["pos"][0] + fd.get("vx", 0), min(fd["pos"][1] + fd["vy"], base - 30))
                draw_food(c, fd["name"], fd["pos"][0], fd["pos"][1], 1.25 * (1 - 0.26 * fd["bites"]), fd.get("rot", 0.5), fd.get("style"))
            for cr in fd["crumbs"]:
                cr[0] += cr[2]
                cr[1] += cr[3]
                cr[3] += 0.8
                cr[4] -= 1
            fd["crumbs"] = [cr for cr in fd["crumbs"] if cr[4] > 0]
            for cr in fd["crumbs"]:
                c.create_rectangle(cr[0] - 2, cr[1] - 2, cr[0] + 2, cr[1] + 2, fill=cr[5], outline="")
        if prop_box:
            pcx, pcy, pw, ph_ = prop_box
            c.create_rectangle(pcx - pw / 2, pcy - ph_ / 2, pcx + pw / 2, pcy + ph_ / 2, fill=CREAM, outline=WOOD_D, width=3)
            c.create_text(pcx, pcy, text=self.prop, font=("Segoe UI", 9, "bold"), width=130, fill=INK)

        if anim == "sleep":
            for i in range(3):
                z = (t // 14 + i) % 3
                c.create_text(cx + 42 + i * 12, top - 6 - i * 15 - z * 2, text="Z", fill="#e2e8f0",
                              font=("Segoe UI", 10 + i * 4, "bold"))

        b = self.bubble
        if b and time.time() < b["until"]:
            bw2, bh2 = b["w"] + 24, b["h"] + 18
            l, tp, r, bt = self.area()
            ccx = clamp(cx, (l + 4 - self.x) + bw2 / 2, (r - 4 - self.x) - bw2 / 2)
            ccx = clamp(ccx, bw2 / 2 + 2, CW - bw2 / 2 - 2)
            y2 = top - (88 if self.prop else 125 if self.chute else 30)
            y1 = max(2, y2 - bh2)
            y2 = y1 + bh2
            x1, x2 = ccx - bw2 / 2, ccx + bw2 / 2
            c.create_rectangle(x1, y1, x2, y2, fill="white", outline=INK, width=2)
            tx = clamp(cx, x1 + 14, x2 - 14)
            c.create_polygon(tx - 8, y2 - 1, tx + 8, y2 - 1, tx, y2 + 12, fill="white", outline=INK, width=2)
            c.create_line(tx - 7, y2, tx + 7, y2, fill="white", width=3)
            c.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=b["text"], font=BF, width=230, justify="center", fill=INK)
        else:
            self.bubble = None

    def draw_study_scene(self, c, cx, base, yc, bw, bh, hop):
        st = self.study
        if not st:
            return None
        stage, t, face = st["stage"], self.t, self.face
        yn = base - 1
        yf = yn - BOOK_H
        ov = None
        if stage == "carry":
            bx = cx + face * (bw + 34) - BK_W / 2
            ytop = base - 8 - BK_H + hop
            draw_closed_book(c, bx, ytop, BK_W, BK_H)
            ov = {face: (bx + (0 if face > 0 else BK_W), ytop + BK_H * 0.55)}
        elif stage == "down":
            k = clamp((t - st["t0"]) / 22.0, 0.0, 1.0)
            e = k * k * (3 - 2 * k)
            bx = cx + face * (bw + 34) - BK_W / 2
            y0 = base - 8 - BK_H
            src = [(bx, y0), (bx + BK_W, y0), (bx + BK_W, y0 + BK_H), (bx, y0 + BK_H)]
            dst = [(cx - BOOK_WF / 2 - 6, yf - 4), (cx + BOOK_WF / 2 + 6, yf - 4),
                   (cx + BOOK_WN / 2 + 7, yn + 3), (cx - BOOK_WN / 2 - 7, yn + 3)]
            lift = math.sin(math.pi * e) * 26
            pts = []
            for (sx_, sy_), (dx_, dy_) in zip(src, dst):
                pts += [lerp(sx_, dx_, e), lerp(sy_, dy_, e) - lift]
            c.create_polygon(pts, fill=COVER, outline=COVER_D, width=3)
            gx0 = (bx + (0 if face > 0 else BK_W), y0 + BK_H * 0.55)
            gx1 = (cx + face * 64, yn - 12)
            ov = {face: (lerp(gx0[0], gx1[0], e), lerp(gx0[1], gx1[1], e) - lift)}
        elif stage in ("open", "read"):
            q = 1.0
            flip = None
            if stage == "open":
                q = clamp((t - st["t1"]) / 14.0, 0.0, 1.0)
            elif st.get("flip_t0") is not None:
                p = (t - st["flip_t0"]) / 16.0
                if 0.0 <= p <= 1.0:
                    flip = p
            draw_open_book(c, cx, yn, q, flip)
            ov = {-1: (cx - 64, yn - 12), 1: (cx + 64, yn - 12)}
        elif stage == "done":
            draw_closed_book(c, cx - (bw + 34) - BK_W / 2, base - 8 - BK_H, BK_W, BK_H)
        if stage in ("open", "read", "done") and (self.anim in ("read", "cheer") or stage == "open"):
            total = st["total"]
            if stage == "done":
                pct, left = 1.0, 0
            elif st.get("until") is None:
                pct, left = 0.0, total
            else:
                left = max(0.0, st["until"] - time.time())
                pct = clamp(1.0 - left / total, 0.0, 1.0) if total > 0 else 1.0
            sec = int(math.ceil(left))
            draw_hourglass(c, cx + 106, base, pct, fa(f"{sec // 60}:{sec % 60:02d}"), t)
        return ov

    def tick(self):
        try:
            self.step()
        except Exception:
            log_exc()
        self.root.after(33, self.tick)

    def step(self):
        self.t += 1
        while not self.q.empty():
            try:
                self.q.get_nowait()()
            except Exception:
                log_exc()
        if not self.dragging:
            if self.gen is None:
                self.gen = self.next_behavior()
            try:
                next(self.gen)
            except StopIteration:
                self.gen = None
            except Exception:
                log_exc()
                self.gen = None
        self.sx = 1 + (self.sx - 1) * 0.78
        self.sy = 1 + (self.sy - 1) * 0.78
        if self.blink > 0:
            self.blink -= 1
        elif random.random() < 0.012:
            self.blink = 5
        self.update_sign()
        self.egg_tick()
        self.splat_tick()
        geo = (int(self.x), int(self.y))
        if geo != self.last_geo:
            self.root.geometry(f"{CW}x{CH}+{geo[0]}+{geo[1]}")
            self.last_geo = geo
        self.draw()

    def slow(self):
        try:
            self.ensure_today()
            self.refresh_area()
            now = time.time()
            self.track_usage(now)
            for rm in list(self.S["reminders"]):
                if now >= rm["at"]:
                    self.S["reminders"].remove(rm)
                    self.save()
                    self.queue.append(lambda txt=rm["text"]: self.ev_alarm(txt))
            if self.study or self.onboarding or self.throwing:
                self.next_event = now + 15
            elif now >= self.S["mute_until"] and now >= self.next_event:
                if not self.queue and not self.busy() and not self.fullscreen_busy():
                    self.queue.append(self.pick_event())
                    lo, hi = {1: (180, 420), 2: (80, 220), 3: (40, 110)}[self.S["chaos"]]
                    self.next_event = now + random.uniform(lo, hi)
                else:
                    self.next_event = now + 15
        except Exception:
            log_exc()
        self.root.after(1000, self.slow)

    def track_usage(self, now):
        dtm = clamp(now - self.usage_t, 0.0, 3.0)
        self.usage_t = now
        if not self.S.get("track_ok") or dtm <= 0:
            return
        if idle_seconds() > 120:
            return
        info = fg_process()
        if not info:
            return
        app, title = info
        if title.startswith("Mojo") or title in ("", "Program Manager"):
            return
        day = self.S["usage"].setdefault(today_str(), {})
        day[app] = round(day.get(app, 0) + dtm, 2)
        if now - self.usage_save > 60:
            self.usage_save = now
            keep = sorted(self.S["usage"])[-60:]
            self.S["usage"] = {k: self.S["usage"][k] for k in keep}
            self.save()

    def usage_totals(self, days=1):
        tot = {}
        for i in range(days):
            d = (dt.date.today() - dt.timedelta(days=i)).isoformat()
            for app, sec in self.S["usage"].get(d, {}).items():
                tot[app] = tot.get(app, 0) + sec
        return sorted(tot.items(), key=lambda kv: -kv[1])

    def usage_line(self, app, sec, scope="امروز"):
        if sec < 20:
            return f"{scope} تقریباً از {app} استفاده نکردی."
        return f"{scope} {fmt_dur(sec)} از {app} استفاده کردی."

    def ev_usage(self):
        top = self.usage_totals(1)
        if not top or sum(v for _, v in top) < 600:
            return
        yield from self.intro_line("هی! یه آمار جالب دارم...", 40)
        app, sec = top[0]
        self.say(f"{self.usage_line(app, sec)} این پرمصرف‌ترین برنامه‌ت بود!", 6500)
        yield from self.wait(190, interruptible=False)
        if len(top) > 1:
            self.say(self.usage_line(top[1][0], top[1][1], "بعدش") , 5000)
            yield from self.wait(150, interruptible=False)

    def usage_day(self, off=0):
        d = dt.date.today() + dt.timedelta(days=off)
        data = self.S["usage"].get(d.isoformat(), {})
        return d, sorted(data.items(), key=lambda kv: -kv[1])

    def show_usage(self):
        if not self.S.get("track_ok"):
            w = self.win("آمار استفاده", 380, 250)
            self.L(w, "برای اینکه بتونم بگم چقدر از هر برنامه استفاده کردی، باید اجازه بدی برنامه‌ی فعال رو "
                      "ببینم. فقط اسم برنامه و مدتش روی همین کامپیوتر ذخیره می‌شه (نه محتوا، نه عنوان پنجره) "
                      "و هر وقت خواستی از تنظیمات خاموشش می‌کنی.", 10, wrap=340).pack(pady=14, padx=10)

            def on():
                self.S["track_ok"] = True
                self.v_track.set(True)
                self.save()
                w.destroy()
                self.say("باشه! از همین الان حساب می‌کنم. بعداً بپرس!", 4000)

            self.B(w, "اجازه می‌دم", on).pack(pady=6)
            self.B(w, "نه", w.destroy, bg="#64748b").pack()
            return
        if getattr(self, "usage_win", None) and alive(self.usage_win):
            self.usage_win.lift()
            return
        w = self.usage_win = self.win("آمار استفاده", 400, 630)
        st = {"off": 0}
        BAR, BAR_TOP, MUTED = "#14b8a6", "#f59e0b", "#64748b"
        tk.Label(w, text="📊 زمان استفاده از برنامه‌ها", bg=CREAM, fg=INK, font=("Segoe UI", 13, "bold")).pack(pady=(12, 6))
        nav = tk.Frame(w, bg=CREAM)
        nav.pack(fill="x", padx=14)
        bprev = tk.Button(nav, text="→ روز قبل", font=("Segoe UI", 10, "bold"), bg=TEAL, fg="white", bd=0,
                          activebackground="#0f766e", activeforeground="white", padx=10, pady=4, cursor="hand2")
        bnext = tk.Button(nav, text="روز بعد ←", font=("Segoe UI", 10, "bold"), bg=TEAL, fg="white", bd=0,
                          activebackground="#0f766e", activeforeground="white", padx=10, pady=4, cursor="hand2")
        bprev.pack(side="right")
        bnext.pack(side="left")
        mid = tk.Frame(nav, bg=CREAM)
        mid.pack(expand=True)
        lday = tk.Label(mid, bg=CREAM, fg=INK, font=("Segoe UI", 13, "bold"))
        lday.pack()
        ldate = tk.Label(mid, bg=CREAM, fg=MUTED, font=("Segoe UI", 9))
        ldate.pack()
        card = tk.Frame(w, bg="white", highlightbackground=WOOD, highlightthickness=2)
        card.pack(fill="x", padx=14, pady=(12, 8))
        ltot = tk.Label(card, bg="white", fg=INK, font=("Segoe UI", 16, "bold"))
        ltot.pack(pady=(8, 0))
        tk.Label(card, text="مجموع کار با کامپیوتر", bg="white", fg=MUTED, font=("Segoe UI", 9)).pack(pady=(0, 8))
        body = tk.Frame(w, bg=CREAM)
        body.pack(fill="both", expand=True, padx=14)
        tk.Label(w, text="روی هر برنامه بزنی، موجو بلند می‌گه 😉", bg=CREAM, fg=MUTED, font=("Segoe UI", 9)
                 ).pack(pady=(4, 10))

        def tell(app, sec):
            d = self.usage_day(st["off"])[0]
            scope = "امروز" if st["off"] == 0 else "دیروز" if st["off"] == -1 else "اون روز"
            self.say(self.usage_line(app, sec, scope), 7000)
            self.pulse(0.1, -0.1)

        def refresh():
            off = st["off"]
            d, items = self.usage_day(off)
            jy, jm, jd = to_jalali(d.year, d.month, d.day)
            lday.config(text="امروز" if off == 0 else "دیروز" if off == -1 else WEEKDAYS[d.weekday()])
            ldate.config(text=f"{WEEKDAYS[d.weekday()]} {fa(jd)} {MONTHS[jm - 1]} {fa(jy)}" if off in (0, -1)
                         else f"{fa(jd)} {MONTHS[jm - 1]} {fa(jy)}")
            bnext.config(state="normal" if off < 0 else "disabled", bg=TEAL if off < 0 else "#cbd5e1")
            bprev.config(state="normal" if off > -59 else "disabled", bg=TEAL if off > -59 else "#cbd5e1")
            tot = sum(v for _, v in items)
            ltot.config(text=fmt_dur(tot) if tot >= 45 else "—")
            for ch in body.winfo_children():
                ch.destroy()
            if not items:
                tk.Label(body, text="برای این روز چیزی ثبت نشده.", bg=CREAM, fg=MUTED, font=("Segoe UI", 11)
                         ).pack(pady=30)
                return
            top = items[0][1] or 1
            for i, (app, sec) in enumerate(items[:8]):
                row = tk.Frame(body, bg=CREAM, cursor="hand2")
                row.pack(fill="x", pady=4)
                top_l = tk.Frame(row, bg=CREAM)
                top_l.pack(fill="x")
                n_ = tk.Label(top_l, text=bmp(app), bg=CREAM, fg=INK, font=("Segoe UI", 11, "bold"), anchor="w")
                n_.pack(side="left")
                t_ = tk.Label(top_l, text=fmt_dur(sec), bg=CREAM, fg="#475569", font=("Segoe UI", 10))
                t_.pack(side="right")
                bar = tk.Canvas(row, height=10, bg="#e7dcc0", highlightthickness=0, bd=0)
                bar.pack(fill="x", pady=(2, 0))
                bar.bind("<Configure>", lambda e, c=bar, v=sec, col=(BAR_TOP if i == 0 else BAR):
                         (c.delete("all"), c.create_rectangle(0, 0, max(4, e.width * v / top), 10, fill=col, outline="")))
                for wd in (row, top_l, n_, t_, bar):
                    wd.bind("<Button-1>", lambda e, a=app, v=sec: tell(a, v))
            if len(items) > 8:
                rest = sum(v for _, v in items[8:])
                tk.Label(body, text=f"و {fa(len(items) - 8)} برنامه‌ی دیگه ({fmt_dur(rest)})", bg=CREAM, fg=MUTED,
                         font=("Segoe UI", 9)).pack(pady=4)

        def step_day(dlt):
            n = st["off"] + dlt
            if -59 <= n <= 0:
                st["off"] = n
                refresh()

        bprev.config(command=lambda: step_day(-1))
        bnext.config(command=lambda: step_day(1))
        refresh()

    def palette(self):
        import colorsys
        cols = []
        for sat, val in ((0.35, 1.0), (0.65, 0.98), (0.85, 0.82), (0.8, 0.5)):
            for hdeg in range(0, 360, 30):
                r, g, b = colorsys.hsv_to_rgb(hdeg / 360.0, sat, val)
                cols.append("#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255)))
        cols += ["#ffffff", "#e2e8f0", "#94a3b8", "#475569", "#1e293b", "#000000", "#3b2a14", "#fda4af",
                 "#5eead4", "#fb7185", "#f472b6", "#a78bfa"]
        return cols

    def body_col(self):
        p = self.preview
        return p["col"] if p and p["part"] == "body" else self.S["look"]["body"]

    def lk(self, part):
        p = self.preview
        return p["col"] if p and p["part"] == part else self.S["look"][part]

    def set_preview(self, part, col):
        self.preview = {"part": part, "col": col}
        if part == "body":
            self.set_color(col)
        self.pulse(0.12, -0.12)

    def stop_preview(self):
        if self.preview:
            self.preview = None
            self.set_color(self.body_col())

    def owned_colors(self):
        return {x.lower() for x in self.S.get("owned_colors", [])} | {v.lower() for v in DEFAULT["look"].values()}

    def add_coins(self, n):
        self.S["coins"] = max(0, int(self.S.get("coins", 0)) + int(n))
        self.save()
        f = getattr(self, "_color_render", None)
        if f and getattr(self, "color_win", None) and alive(self.color_win):
            f()

    def show_colors(self):
        if getattr(self, "color_win", None) and alive(self.color_win):
            self.color_win.lift()
            return
        w = self.color_win = self.win("رنگ‌ها و فروشگاه", 450, 680)
        look = self.S["look"]
        st = {"tab": "colors", "part": "body", "pend": None}
        parts = [("body", "بدن"), ("eye", "چشم"), ("cheek", "لپ")]
        bar = tk.Frame(w, bg=CREAM)
        bar.pack(fill="x", padx=12, pady=(10, 4))
        bal = tk.Canvas(bar, width=130, height=34, bg=CREAM, highlightthickness=0)
        bal.pack(side="left")
        tabs = {}
        for key, name in (("shop", "فروشگاه"), ("colors", "رنگ‌ها")):
            b_ = tk.Button(bar, text=name, font=("Segoe UI", 11, "bold"), bd=0, padx=14, pady=5, cursor="hand2",
                           command=lambda k=key: (self.stop_preview(), st.update(tab=k, pend=None), render()))
            b_.pack(side="right", padx=3)
            tabs[key] = b_
        content = tk.Frame(w, bg=CREAM)
        content.pack(fill="both", expand=True, padx=10)

        def draw_balance():
            bal.delete("all")
            draw_coin(bal, 16, 17, 13)
            bal.create_text(36, 17, text=fa(self.S.get("coins", 0)), anchor="w", font=("Segoe UI", 15, "bold"), fill=INK)

        def say_poor():
            self.say("سکه‌ت کمه! با بردن توی کیک‌پزی سکه جمع کن.", 3500)
            self.snd.play("sad", force=True)

        def apply(col):
            self.stop_preview()
            look[st["part"]] = col
            if st["part"] == "body":
                self.set_color(col)
            self.save()
            self.pulse(0.1, -0.1)
            render()

        def buy_color():
            p = st["pend"]
            if not p:
                return
            if self.S["coins"] < p["price"]:
                say_poor()
                return
            self.S["coins"] -= p["price"]
            oc = self.owned_colors()
            oc.add(p["col"].lower())
            self.S["owned_colors"] = sorted(oc)
            st["pend"] = None
            self.snd.play("ding", force=True)
            self.say("این رنگ از حالا مال توئه؛ همیشه رایگان!", 3000)
            apply(p["col"])

        def build_colors():
            tk.Label(content, text="رنگی که یه بار بخری، برای همیشه رایگانه.", bg=CREAM, fg="#64748b",
                     font=("Segoe UI", 9)).pack(pady=(6, 2))
            row = tk.Frame(content, bg=CREAM)
            row.pack(pady=6)
            for k, name in parts:
                on = k == st["part"]
                tk.Button(row, text=name, font=("Segoe UI", 11, "bold"), bd=0, padx=16, pady=4, cursor="hand2",
                          bg=TEAL if on else "#cbd5e1", fg="white" if on else INK,
                          command=lambda k=k: (self.stop_preview(), st.update(part=k, pend=None), render())).pack(side="right", padx=4)
            grid = tk.Frame(content, bg=CREAM)
            grid.pack(pady=4)
            oc = self.owned_colors()
            cur = look[st["part"]].lower()
            for i, col in enumerate(self.palette()):
                cv = tk.Canvas(grid, width=44, height=34, bg=CREAM, highlightthickness=0, cursor="hand2")
                cv.grid(row=i // 8, column=i % 8, padx=1, pady=1)
                sel = col.lower() == cur
                pend = st["pend"] and st["pend"]["col"].lower() == col.lower()
                cv.create_rectangle(3, 3, 41, 31, fill=col, outline=INK if (sel or pend) else "#d6c9a6", width=3 if (sel or pend) else 1)
                if col.lower() not in oc:
                    draw_coin(cv, 34, 25, 7)
                cv.bind("<Button-1>", lambda e, c=col: apply(c) if c.lower() in oc else (
                    st.update(pend={"col": c, "price": COLOR_PRICE}), self.set_preview(st["part"], c), render()))
            p = st["pend"]
            if p:
                tk.Label(content, text="👀 همین الان روی موجو می‌بینیش؛ تا نخری ذخیره نمی‌شه.", bg=CREAM, fg="#0369a1",
                         font=("Segoe UI", 9, "bold")).pack(pady=(4, 0))
                box = tk.Frame(content, bg="white", highlightbackground=WOOD, highlightthickness=2)
                box.pack(fill="x", padx=14, pady=8)
                cc = tk.Canvas(box, width=44, height=34, bg="white", highlightthickness=0)
                cc.pack(side="left", padx=8, pady=8)
                cc.create_rectangle(3, 3, 41, 31, fill=p["col"], outline=INK, width=2)
                pc = tk.Canvas(box, width=90, height=34, bg="white", highlightthickness=0)
                pc.pack(side="left")
                draw_coin(pc, 16, 17, 12)
                pc.create_text(36, 17, text=fa(p["price"]), anchor="w", font=("Segoe UI", 14, "bold"), fill=INK)
                can = self.S["coins"] >= p["price"]
                tk.Button(box, text="بیخیال", font=("Segoe UI", 10, "bold"), bg="#94a3b8", fg="white", bd=0, padx=10, pady=5,
                          cursor="hand2", command=lambda: (self.stop_preview(), st.update(pend=None), render())).pack(side="right", padx=6)
                tk.Button(box, text="خرید" if can else "سکه‌ت کمه", font=("Segoe UI", 11, "bold"),
                          bg="#16a34a" if can else "#cbd5e1", fg="white" if can else "#64748b", bd=0, padx=14, pady=5,
                          cursor="hand2", command=buy_color).pack(side="right")
            row2 = tk.Frame(content, bg=CREAM)
            row2.pack(pady=8)

            def custom():
                from tkinter import colorchooser
                res = colorchooser.askcolor(color=look[st["part"]], parent=w, title="رنگ دلخواه")
                if res and res[1]:
                    col = res[1].lower()
                    if col in self.owned_colors():
                        apply(col)
                    else:
                        st["pend"] = {"col": col, "price": CUSTOM_PRICE}
                        self.set_preview(st["part"], col)
                        render()

            def reset():
                self.stop_preview()
                look.update(DEFAULT["look"])
                self.set_color(look["body"])
                self.save()
                st["pend"] = None
                render()

            self.B(row2, "رنگ دلخواه (۲۰ سکه)", custom, bg="#0369a1").pack(side="left", padx=4)
            self.B(row2, "برگردون به اولی", reset, bg="#64748b").pack(side="left", padx=4)

        def build_shop():
            tk.Label(content, text="با سکه‌هایی که توی کیک‌پزی می‌بری، برای موجو چیز بخر!", bg=CREAM, fg="#64748b",
                     font=("Segoe UI", 9)).pack(pady=(6, 8))
            for it in SHOP_ITEMS:
                owned = self.S.get("owned", {}).get(it["id"])
                card = tk.Frame(content, bg="white", highlightbackground=WOOD, highlightthickness=2)
                card.pack(fill="x", padx=6, pady=5)
                ic = tk.Canvas(card, width=76, height=76, bg="white", highlightthickness=0)
                ic.pack(side="left", padx=(8, 4), pady=8)
                draw_gift_box(ic, 38, 40, 1.15, it["tag"])
                mid = tk.Frame(card, bg="white")
                mid.pack(side="left", fill="both", expand=True, padx=4)
                tk.Label(mid, text=it["name"], bg="white", fg=INK, font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", pady=(10, 0))
                tk.Label(mid, text=it["desc"], bg="white", fg="#64748b", font=("Segoe UI", 9), anchor="w", justify="left",
                         wraplength=165).pack(fill="x", pady=(2, 8))
                right = tk.Frame(card, bg="white")
                right.pack(side="right", padx=8)
                pc = tk.Canvas(right, width=84, height=30, bg="white", highlightthickness=0)
                pc.pack(pady=(14, 4))
                draw_coin(pc, 14, 15, 11)
                pc.create_text(32, 15, text=fa(it["price"]), anchor="w", font=("Segoe UI", 14, "bold"), fill=INK)
                can = self.S["coins"] >= it["price"]
                if owned:
                    tk.Label(right, text="✓ داری", bg="#e2e8f0", fg="#475569", font=("Segoe UI", 10, "bold"), padx=14, pady=5).pack(pady=(0, 10))
                else:
                    tk.Button(right, text="خرید", font=("Segoe UI", 11, "bold"), bg="#16a34a" if can else "#cbd5e1",
                              fg="white" if can else "#64748b", bd=0, padx=22, pady=5, cursor="hand2",
                              command=lambda i=it: buy_item(i)).pack(pady=(0, 10))

        def buy_item(it):
            if self.S["coins"] < it["price"]:
                say_poor()
                return
            self.S["coins"] -= it["price"]
            self.S.setdefault("owned", {})[it["id"]] = True
            self.save()
            self.snd.play("yay", force=True)
            if it["id"] == "jetpack":
                self.say("جت‌پک!! الان امتحانش می‌کنم!", 3500)
                self.queue.append(self.ev_fly)
            else:
                self.say("چتر نجات! حالا از هر ارتفاعی بندازیم، نرم میام پایین!", 4000)
            render()

        def render():
            if not alive(w):
                return
            for ch in content.winfo_children():
                ch.destroy()
            for k, b_ in tabs.items():
                on = k == st["tab"]
                b_.config(bg=TEAL if on else "#cbd5e1", fg="white" if on else INK)
            draw_balance()
            (build_colors if st["tab"] == "colors" else build_shop)()

        self._color_render = render
        w.bind("<Destroy>", lambda e: self.stop_preview() if e.widget is w else None)
        render()

    def toggle_track(self):
        self.S["track_ok"] = self.v_track.get()
        self.save()
        self.say("باشه، از الان آمار برنامه‌ها رو ثبت می‌کنم." if self.v_track.get() else "آمار برنامه‌ها خاموش شد.", 3500)

    def fullscreen_busy(self):
        info = fg_window()
        if not info:
            return False
        _, (l, t, r, b), title = info
        if title.startswith("Mojo") or title == "Program Manager":
            return False
        return l <= 0 and t <= 0 and r >= self.root.winfo_screenwidth() and b >= self.root.winfo_screenheight()

    def limits(self):
        if self.on_window and self.win_lim:
            return self.win_lim
        l, t, r, b = self.area()
        return l + 40, r - 40

    def wait(self, n, interruptible=True):
        for _ in range(int(n)):
            if interruptible and self.queue:
                return
            yield

    def walk_to(self, tx, speed=3.0, anim="walk", free=False, interruptible=True):
        lo, hi = self.limits()
        if not free:
            tx = clamp(tx, lo, hi)
        self.anim = anim
        guard = 0
        while abs(self.fx() - tx) > max(2.0, speed * 0.6):
            if interruptible and self.queue:
                break
            d = 1 if tx > self.fx() else -1
            self.face = d
            self.x += d * min(speed, abs(tx - self.fx()))
            guard += 1
            if guard > 1200:
                break
            yield
        self.anim = "idle"

    def jump_to(self, tx, ty, peak=70):
        x0, y0 = self.fx(), self.fy()
        n = int(clamp(14 + math.hypot(tx - x0, ty - y0) / 18, 16, 40))
        if tx != x0:
            self.face = 1 if tx > x0 else -1
        self.anim = "jump"
        self.pulse(-0.2, 0.3)
        self.snd.play("boing")
        for i in range(1, n + 1):
            s = i / n
            self.put(x0 + (tx - x0) * s, y0 + (ty - y0) * s - 4 * peak * s * (1 - s))
            yield
        self.put(tx, ty)
        self.anim = "idle"
        self.pulse(0.3, -0.3)
        self.snd.play("land")

    def fall(self, floor=None):
        floor = self.ground() if floor is None else floor
        vy = 0.0
        self.anim = "fall"
        while self.fy() < floor:
            vy += 1.3
            self.y += vy
            if self.fy() > floor:
                self.y = floor - FOOT
            yield
        self.anim = "idle"
        self.pulse(0.35, -0.35)
        self.snd.play("land")
        self.floor = self.on_window = self.win_lim = None

    def get_down(self):
        g = self.ground()
        if self.fy() < g - 3:
            for _ in range(8):
                self.x += self.face * 3
                yield
            self.on_window = self.floor = self.win_lim = None
            yield from self.fall(g)
        self.put(self.fx(), g)

    def reset_look(self):
        if self.study:
            return
        self.anim, self.expr, self.prop = "idle", "happy", None
        self.food = None
        self.jet, self.chute = None, None
        self.set_color(self.body_col())

    def stop_gen(self):
        if self.gen:
            try:
                self.gen.close()
            except Exception:
                pass
            self.gen = None
        self.catch = None
        self.reset_look()

    def interrupt(self):
        self.stop_gen()

    def react(self, text, expr="happy", anim="idle", frames=70, prop=None):
        self.expr, self.anim, self.prop = expr, anim, prop
        if anim == "dance":
            self.pulse(-0.1, 0.2)
        sn = {"happy": "happy", "sad": "sad", "surprised": "squeak"}.get(expr)
        if sn:
            self.snd.play(sn, force=True)
        self.say(text, delay=550 if sn else 0)
        yield from self.wait(frames, interruptible=False)
        self.reset_look()

    def queue_react(self, *a, **k):
        self.queue.insert(0, lambda: self.react(*a, **k))

    def next_behavior(self):
        if self.study and not self.queue:
            return self.do_study()
        if self.queue:
            fn = self.queue.pop(0)
            self.cur_event = getattr(fn, "__name__", None)
            r = fn()
            return r if r is not None else iter(())
        self.cur_event = None
        return self.idle_choice()

    def quip(self):
        S, f = self.S, self.S["facts"]
        pool = list(QUIPS) + list(JOKES) + ["می‌دونستی؟ " + x for x in FACTS]
        for k, v in f.items():
            if k in FACT_LINES and v:
                pool.append(FACT_LINES[k].format(v=v))
        if S["user_name"]:
            pool.append(f"{S['user_name']}، امروز خیلی بامزه‌ای!")
        return random.choice(pool)

    def idle_choice(self):
        if self.sign and not self.sign.done:
            return self.attend_sign(self.sign)
        hour = dt.datetime.now().hour
        opts = [(self.b_stand, 3), (self.b_wander, 3.5), (self.b_hop, 1.2), (self.b_dance, 1),
                (self.b_sit, 1), (self.b_chatter, 1.5), (self.b_stalk, 0.8)]
        if self.S["window_ok"] and self.pick_window():
            opts.append((self.b_window, 1.6))
        if 1 <= hour < 6:
            opts.append((self.b_nap, 3))
        return wchoice(opts)()

    def b_stand(self):
        self.anim, self.expr = "idle", random.choice(["happy", "happy", "sneaky"])
        yield from self.wait(random.randint(60, 150))
        self.reset_look()

    def b_wander(self):
        l, t, r, b = self.area()
        lo, hi = self.limits()
        yield from self.walk_to(random.uniform(lo, hi), speed=random.choice([2.0, 3.0, 4.5]))
        yield from self.wait(random.randint(10, 40))

    def b_hop(self):
        for _ in range(random.randint(1, 3)):
            yield from self.jump_to(self.fx(), self.fy(), peak=random.randint(35, 70))
            yield from self.wait(6)

    def b_dance(self):
        self.expr, self.anim = "happy", "dance"
        yield from self.wait(random.randint(90, 170))
        self.reset_look()

    def b_sit(self):
        self.anim, self.expr = "sit", "happy"
        yield from self.wait(random.randint(90, 220))
        self.reset_look()

    def b_chatter(self):
        self.say(self.quip())
        self.anim = random.choice(["wave", "idle"])
        yield from self.wait(100)
        self.reset_look()

    def b_nap(self):
        self.anim = "sleep"
        self.say("خوابم میاد... zzz", 3000)
        yield from self.wait(random.randint(250, 450))
        self.reset_look()
        self.say("هوم... خوب خوابیدم.")

    def b_stalk(self):
        yield from self.get_down()
        px, _ = self.root.winfo_pointerxy()
        self.expr = "sneaky"
        yield from self.walk_to(px + random.choice([-1, 1]) * 90, speed=4.0, anim="run")
        self.face = 1 if px > self.fx() else -1
        if random.random() < 0.7:
            self.say(random.choice(["ماوس‌ت رو می‌بینم...", "دارم تعقیبش می‌کنم.", "بگیرمش؟ نه... بعداً."]))
        yield from self.wait(70)
        self.reset_look()

    def pick_window(self):
        info = fg_window()
        if not info:
            return None
        h, (l, t, r, b), title = info
        if not title or title.startswith("Mojo") or title == "Program Manager":
            return None
        al, at, ar, ab = self.area()
        if r - l < 350 or t < at + 120 or t > ab - 220:
            return None
        return info

    def b_window(self, spy=False):
        info = self.pick_window()
        if not info:
            return
        yield from self.get_down()
        hwnd, (l, t, r, b), title = info
        al, at, ar, ab = self.area()
        tx = clamp(random.uniform(l + 50, r - 50), al + 40, ar - 40)
        yield from self.walk_to(tx, speed=4.5, anim="run")
        yield from self.jump_to(tx, t, peak=130)
        self.on_window, self.floor, self.win_lim = hwnd, t, (l + 30, r - 30)
        rel = self.fx() - l
        self.anim, self.expr = "sit", "happy"
        if spy or random.random() < 0.35:
            nm = short(title, 28)
            self.say(f"«{nm}»؟ جاسوسی نمی‌کنما!" if spy else f"اینجا خوب می‌شه نشست!")
        end = self.t + random.randint(260, 520)
        while self.t < end and not self.queue:
            if self.t % 8 == 0:
                cur = win_rect(hwnd)
                if cur is None:
                    break
                nl, nt, nr, nb = cur
                self.put(nl + rel, nt)
                self.floor, self.win_lim = nt, (nl + 30, nr - 30)
                if nt < al + 100:
                    break
            yield
        self.reset_look()
        self.on_window = self.win_lim = self.floor = None
        yield from self.fall()

    def L(self, parent, text="", size=11, fg=INK, bold=False, wrap=300, **kw):
        return tk.Label(parent, text=bmp(text), bg=kw.pop("bg", CREAM), fg=fg,
                        font=("Segoe UI", size, "bold" if bold else "normal"), wraplength=wrap,
                        justify="center", **kw)

    def B(self, parent, text, cmd, bg=TEAL, **kw):
        return tk.Button(parent, text=bmp(text), command=cmd, bg=bg, fg="white", activebackground=WOOD_D,
                         activeforeground="white", relief="flat", font=F, padx=10, pady=3, cursor="hand2", **kw)

    def open_sign(self, title, w, h, build, cb=None, hint="", timeout=150):
        if self.sign and not self.sign.done:
            self.close_sign(self.sign, "replaced")
        l, t, r, b = self.area()
        win = tk.Toplevel(self.root)
        win.title("Mojo sign")
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=WOOD_D)
        sg = Sign(win, w, h, cb, hint, timeout)
        fxp = self.fx()
        x = l + 30
        for _ in range(14):
            x = random.randint(int(l + 30), max(int(l + 30), int(r - w - 30)))
            if abs((x + w / 2) - fxp) > w / 2 + 110:
                break
        sg.x = float(x)
        sg.ty = float(max(t + 10, b - h))
        left_spot, right_spot = x - 80, x + w + 80
        sg.stand_x = left_spot if left_spot > l + 50 else min(right_spot, r - 50)
        inner = tk.Frame(win, bg=CREAM)
        inner.pack(fill="both", expand=True, padx=6, pady=6)
        head = tk.Frame(inner, bg=WOOD)
        head.pack(fill="x")
        tl = tk.Label(head, text=bmp(title), bg=WOOD, fg=CREAM, font=("Segoe UI", 11, "bold"),
                      wraplength=w - 80, justify="center", pady=6)
        tl.pack(side="left", fill="x", expand=True)
        xb = tk.Label(head, text="✕", bg=WOOD, fg=CREAM, font=("Segoe UI", 11, "bold"), padx=10, cursor="hand2")
        xb.pack(side="right")
        xb.bind("<Button-1>", lambda e: self.close_sign(sg, "skip"))
        drag = {}

        def dp(e):
            drag["o"] = (e.x_root - sg.x, e.y_root - sg.y)
            sg.dropping = False

        def dm(e):
            if "o" in drag:
                sg.x, sg.y = e.x_root - drag["o"][0], e.y_root - drag["o"][1]
                win.geometry(f"+{int(sg.x)}+{int(sg.y)}")

        tl.bind("<ButtonPress-1>", dp)
        tl.bind("<B1-Motion>", dm)
        body = tk.Frame(inner, bg=CREAM)
        body.pack(fill="both", expand=True, padx=10, pady=8)
        win.geometry(f"{w}x{h}+{int(sg.x)}+{int(sg.y)}")
        try:
            build(body, sg)
        except Exception:
            log_exc()
        sg.ev = self.cur_event
        self.snd.play("ding", force=True)
        self.sign = sg
        return sg

    def update_sign(self):
        sg = self.sign
        if not sg or sg.done or not sg.dropping:
            return
        if not alive(sg.win):
            sg.done = True
            return
        sg.vy += 2.4
        sg.y += sg.vy
        if sg.y >= sg.ty:
            sg.y = sg.ty
            sg.vy = -sg.vy * 0.38
            if abs(sg.vy) < 3:
                sg.dropping, sg.vy = False, 0.0
                self.snd.play("thud", force=True)
        sg.win.geometry(f"+{int(sg.x)}+{int(sg.y)}")

    def close_sign(self, sg, res):
        if sg.done:
            return
        sg.done, sg.result = True, res
        try:
            sg.win.destroy()
        except tk.TclError:
            pass
        if self.sign is sg:
            self.sign = None
        ev = getattr(sg, "ev", None)
        if ev and ev.startswith("ev_") and res != "replaced":
            st = self.S["ev_stats"].setdefault(ev, [0, 0])
            st[0] += 1
            if res not in ("skip", "timeout"):
                st[1] += 1
            if st[0] >= 40:
                st[0], st[1] = st[0] // 2, st[1] // 2
            self.save()
        if sg.cb:
            try:
                sg.cb(res)
            except Exception:
                log_exc()

    def attend_sign(self, sg):
        yield from self.get_down()
        yield from self.walk_to(sg.stand_x, speed=6.0, anim="run", interruptible=False)
        self.face = 1 if sg.x + sg.w / 2 > self.fx() else -1
        start = self.t
        self.anim, self.expr = "idle", "happy"
        while not sg.done:
            age = self.t - start
            if not sg.hinted and age > 28 * 30 and sg.hint:
                sg.hinted = True
                self.say(sg.hint)
            if age > sg.timeout * 30:
                self.close_sign(sg, "timeout")
                break
            if age % 150 == 149:
                yield from self.jump_to(self.fx(), self.fy(), peak=30)
            if self.queue and age > 20:
                break
            yield
        self.reset_look()

    def adapt(self, fn):
        shown, eng = self.S["ev_stats"].get(fn.__name__, [0, 0])
        return clamp((eng + 1.5) / (shown + 3) * 2, 0.35, 1.8)

    def eligible_items(self, force=False):
        now = time.time()
        return [it for it in self.S["library"] if force or it.get("next", 0) <= now]

    def pick_event(self):
        if self.eligible_items():
            self.last_event = "ev_invite"
            return self.ev_invite
        S, facts, now = self.S, self.S["facts"], time.time()
        cand = [(self.ev_draw, 2.2), (self.ev_mood, 1), (self.ev_quiz, 1.2),
                (self.ev_play, 1.3), (self.ev_chase, 1.1), (self.ev_peek, 1.6), (self.ev_parade, 1.6),
                (self.ev_feed, 1.1), (self.ev_glitch, 0.7), (self.ev_health, 1)]
        if S.get("track_ok") and sys.platform == "win32":
            cand.append((self.ev_usage, 0.9))
        if S.get("owned", {}).get("jetpack"):
            cand.append((self.ev_fly, 1.4))
        if [k for k in ASKS if k not in facts]:
            cand.append((self.ev_ask, 3.2))
        have = {it["kind"] for it in S["library"]}
        if [k for k in SHOW_KINDS if k not in have and now - S["no_kinds"].get(k, 0) > 7 * 86400]:
            cand.append((self.ev_showme, 1.8))
        if [k for k in GIFTS if facts.get(k) and now - S["gifts"].get(k, 0) > 3 * 86400]:
            cand.append((self.ev_gift, 2.0))
        if S["mouse_ok"] and sys.platform == "win32":
            cand.append((self.ev_steal, 1.2))
        if S["window_ok"] and self.pick_window():
            cand.append((self.ev_spy, 1.2))
        cand = [(f, w) for f, w in cand if f.__name__ != self.last_event] or cand
        f = wchoice([(f, w * self.adapt(f)) for f, w in cand])
        self.last_event = f.__name__
        return f

    def intro_line(self, text, frames=60):
        self.expr, self.anim = "happy", "wave"
        self.say(text)
        yield from self.wait(frames, interruptible=False)
        self.anim = "idle"

    # ───────────── تخم‌مرغ اولین اجرا ─────────────
    def egg_make(self):
        l, t, r, b = self.area()
        wx = int((l + r) / 2 - ECX)
        wy = int(max(t, t + (b - t) * 0.46 - ECY))
        win = tk.Toplevel(self.root)
        win.title("Mojo egg")
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-transparentcolor", TRANSP)
        except tk.TclError:
            pass
        win.configure(bg=TRANSP)
        win.geometry(f"{EW}x{EH}+{wx}+{wy}")
        cv = tk.Canvas(win, width=EW, height=EH, bg=TRANSP, highlightthickness=0, bd=0, cursor="hand2")
        cv.pack()
        cv.bind("<ButtonPress-1>", lambda e: self.egg_click())
        self.egg = {"win": win, "cv": cv, "wx": wx, "wy": wy, "clicks": 0, "crack": 0, "glow": False,
                    "shake": 0.0, "hint": True, "t": 0, "idle": 0, "burst_t": None, "shards": [], "ang": 0.0}

    def egg_click(self):
        e = self.egg
        if not e or e["burst_t"] is not None:
            return
        e["clicks"] += 1
        k = e["clicks"]
        e["hint"], e["idle"] = False, 0
        e["crack"] = min(k - 1, 3)
        e["glow"] = k >= 5
        e["shake"] = {1: 10.0, 2: 16.0, 3: 20.0, 4: 26.0, 5: 34.0}.get(k, 34.0)
        self.snd.play("thud" if k == 1 else "pop", force=True)
        if k >= EGG_CLICKS:
            self.egg_burst()

    def egg_burst(self):
        e = self.egg
        e["burst_t"] = 0
        e["ang"] = 0.0
        shards = []
        for _ in range(13):
            u, v = random.uniform(-0.8, 0.8), random.uniform(-0.9, 0.5)
            px, py = ECX + u * ERX, ECY + v * ERY
            n = random.choice((3, 4))
            sz = random.uniform(9, 22)
            rel = [(math.cos(2 * math.pi * i / n + random.uniform(-0.4, 0.4)) * sz * random.uniform(0.6, 1.1),
                    math.sin(2 * math.pi * i / n + random.uniform(-0.4, 0.4)) * sz * random.uniform(0.6, 1.1))
                   for i in range(n)]
            shards.append({"x": px, "y": py, "vx": u * 7 + random.uniform(-2, 2), "vy": random.uniform(-13, -5),
                           "a": random.uniform(0, 6.28), "va": random.uniform(-0.4, 0.4), "rel": rel,
                           "fill": random.choice((self.color, self.color, self.hl, self.belly))})
        e["shards"] = shards
        self.snd.play("pop", force=True)
        self.snd.play("whoosh", force=True)

    def egg_pts(self, ang, steps=48, vmin=None):
        pts = []
        pxp, pyp = ECX, ECY + ERY
        ca, sa = math.cos(ang), math.sin(ang)
        for i in range(steps):
            th = 2 * math.pi * i / steps
            u, v = math.sin(th) * (1 - 0.15 * math.cos(th)), -math.cos(th)
            if vmin is not None and v < vmin:
                continue
            x, y = ECX + u * ERX, ECY + v * ERY
            dx, dy = x - pxp, y - pyp
            pts.append((pxp + dx * ca - dy * sa, pyp + dx * sa + dy * ca))
        return pts

    def egg_tick(self):
        e = self.egg
        if not e:
            return
        try:
            self.egg_draw(e)
        except Exception:
            log_exc()
            self.egg_close()

    def egg_close(self):
        e, self.egg = self.egg, None
        if e:
            try:
                e["win"].destroy()
            except tk.TclError:
                pass

    def egg_draw(self, e):
        c = e["cv"]
        if not alive(e["win"]):
            self.egg = None
            return
        e["t"] += 1
        t = e["t"]
        c.delete("all")
        col, edge = self.color, self.edge
        gy = ECY + ERY + 8
        bt = e["burst_t"]
        pxp, pyp = ECX, ECY + ERY
        # سایه
        c.create_oval(ECX - ERX * 0.95, gy - 9, ECX + ERX * 0.95, gy + 9, fill="#0b2f2c", outline="", stipple="gray50")
        if bt is None:
            e["idle"] += 1
            if e["idle"] > 90 and e["idle"] % 110 == 0 and e["clicks"] < 5:
                e["shake"] = max(e["shake"], 9.0)
            amp = e["shake"] if e["clicks"] < 5 else max(e["shake"], 7.0)
            e["ang"] = math.sin(t * 1.35) * amp * 0.011
            e["shake"] *= 0.9
            ang = e["ang"]
            ca, sa = math.cos(ang), math.sin(ang)

            def tr(u, v):
                x, y = ECX + u * ERX, ECY + v * ERY
                dx, dy = x - pxp, y - pyp
                return pxp + dx * ca - dy * sa, pyp + dx * sa + dy * ca

            pts = self.egg_pts(ang)
            c.create_polygon(pts, fill=col, outline=edge, width=3, smooth=True)
            sp = mix(col, "#0f766e", 0.3)
            for u, v, rr in ((-0.38, -0.12, 9), (0.42, 0.2, 11), (-0.2, 0.52, 7), (0.2, -0.52, 6), (-0.55, 0.36, 6),
                             (0.05, 0.1, 5)):
                x, y = tr(u, v)
                c.create_oval(x - rr, y - rr, x + rr, y + rr, fill=sp, outline="")
            hx, hy = tr(-0.42, -0.42)
            c.create_oval(hx - 8, hy - 15, hx + 8, hy + 15, fill=self.hl, outline="")
            hx2, hy2 = tr(-0.22, -0.7)
            c.create_oval(hx2 - 4, hy2 - 3, hx2 + 4, hy2 + 3, fill="white", outline="")
            cr = [[(-0.1, -0.62), (0.05, -0.45), (-0.08, -0.3), (0.06, -0.15)],
                  [(0.06, -0.15), (-0.25, -0.05), (-0.42, 0.1)], [(0.06, -0.15), (0.3, -0.02), (0.52, -0.1)],
                  [(-0.42, 0.1), (-0.2, 0.26), (-0.36, 0.48)], [(0.52, -0.1), (0.36, 0.12), (0.56, 0.32)],
                  [(0.0, -0.42), (0.26, -0.6)]]
            groups = {0: 0, 1: 1, 2: 3, 3: 6}
            nshow = groups[min(e["crack"], 3)]
            for i, line in enumerate(cr[:nshow]):
                pl = []
                for u, v in line:
                    pl += list(tr(u, v))
                if e["glow"]:
                    c.create_line(pl, fill="#fff7a8", width=7, capstyle="round", joinstyle="round")
                c.create_line(pl, fill="#0f4f4a", width=3, capstyle="round", joinstyle="round")
            if e["hint"]:
                c.create_text(ECX, gy + 32, text="بزن روش", font=("Segoe UI", 13), fill="#86aaa5")
        else:
            e["burst_t"] = bt = bt + 1
            # نیم‌پوسته‌ی پایین
            low = self.egg_pts(0.0, 60, vmin=0.32)
            if low:
                ul, ur = (low[0][0] - ECX) / ERX, (low[-1][0] - ECX) / ERX
                zz = []
                for k in range(1, 7):
                    u = ur + (ul - ur) * k / 7
                    zz.append((ECX + u * ERX, ECY + (0.32 - (0.17 if k % 2 else 0.0)) * ERY))
                c.create_polygon(low + zz, fill=col, outline=edge, width=3)
            for sh in e["shards"]:
                sh["vy"] += 0.9
                sh["x"] += sh["vx"]
                sh["y"] += sh["vy"]
                sh["a"] += sh["va"]
                if sh["y"] > gy - 4:
                    sh["y"] = gy - 4
                    sh["vy"] *= -0.3
                    sh["vx"] *= 0.6
                    sh["va"] *= 0.5
                ca, sa = math.cos(sh["a"]), math.sin(sh["a"])
                pl = []
                for dx, dy in sh["rel"]:
                    pl += [sh["x"] + dx * ca - dy * sa, sh["y"] + dx * sa + dy * ca]
                c.create_polygon(pl, fill=sh["fill"], outline=edge, width=2)
            if bt < 12:
                rr = 20 + bt * 9
                c.create_oval(ECX - rr, ECY - rr, ECX + rr, ECY + rr, outline="#fff7a8", width=max(1, 8 - bt // 2))
            if bt > 130:
                self.egg_close()

    def ob_line(self, text, frames=130, anim="wave", expr="happy"):
        self.expr, self.anim = expr, anim
        self.say(text, int(frames * 33) + 600)
        yield from self.wait(frames, interruptible=False)
        self.anim = "idle"

    def ev_hatch(self):
        self.onboarding = True
        self.x, self.y = -3000.0, -3000.0
        self.egg_make()
        # ۱) منتظر کلیک‌ها روی تخم
        while self.egg and self.egg["burst_t"] is None:
            yield
        e = self.egg
        if e:
            ex, ey = e["wx"] + ECX, e["wy"] + ECY + ERY - 8
        else:
            l, t, r, b = self.area()
            ex, ey = (l + r) / 2, (t + b) / 2
        for _ in range(5):
            yield
        # ۲) موجو از تخم می‌پره بیرون
        self.put(ex, ey)
        self.last_geo = None
        self.expr, self.face = "surprised", random.choice((-1, 1))
        self.pulse(-0.3, 0.4)
        l, t, r, b = self.area()
        tx = clamp(ex + self.face * 190, l + 60, r - 60)
        yield from self.jump_to(tx, ey - 30, peak=150)
        self.snd.play("yay", force=True)
        yield from self.fall()
        # ۳) معرفی
        yield from self.ob_line("سلاااام! من موجوام! تازه از تخم اومدم بیرون؛ ببخشید اگه یه کم لزجم!", 150)
        yield from self.ob_line("من یه موجود ژله‌ای‌ام که از امروز روی دسکتاپت زندگی می‌کنم. بذار چنتا از کارام رو بگم:", 140)
        feats = [
            ("می‌تونم باهات بازی کنم: حدس عدد، دوز، سنگ‌کاغذ‌قیچی، ریاضی سریع و کلی چیز دیگه!", "cheer"),
            ("هر روز یه چالش مخصوص خودت میدم و جوک و نکته‌ی جالب برات میارم!", "dance"),
            ("وقتی بخوای درس بخونی، کتاب میارم کنارت می‌شینم می‌خونم و با ساعت شنی بهت زمان رو نشون میدم.", "wave"),
            ("ازت می‌پرسم چی دوست داری و بعد برات هدیه پیدا می‌کنم. بازی مورد علاقه‌ت رو هم بهم نشون بدی، بعداً می‌پرسم بازیش کنیم یا نه!", "cheer"),
        ]
        for txt, an in feats:
            yield from self.ob_line(txt, 150, an)
            lo, hi = self.limits()
            yield from self.walk_to(random.uniform(lo, hi), speed=5.0, anim="run", interruptible=False)
            yield from self.jump_to(self.fx(), self.fy(), peak=40)
        # ۴) اسم
        yield from self.ob_line("ولی قبل از همه‌چیز... باید بشناسمت!", 90)
        res = {}

        def build(f, sg):
            self.L(f, "اسم تو چیه؟", 12).pack(pady=(4, 8))
            en = tk.Entry(f, font=("Segoe UI", 13), justify="center", width=16)
            en.pack()
            en.focus_set()

            def ok(_=None):
                v = bmp(en.get().strip())[:20]
                if v:
                    self.S["user_name"] = v
                    self.save()
                    self.close_sign(sg, "ok")

            en.bind("<Return>", ok)
            self.B(f, "این منم!", ok).pack(pady=10)

        sg = self.open_sign("اسمت چیه؟", 300, 210, build, None, hint="اسمتو بنویس تا بتونم صدات کنم.", timeout=900)
        yield from self.attend_sign(sg)
        n = self.S["user_name"] or "رفیق"
        # ۵) دسترسی‌ها
        yield from self.ob_line(f"خوشبختم {n}! یه چنتا اجازه هم لازم دارم تا خوب کار کنم. هرکدوم رو نخواستی تیک بزن بردار!", 150)
        vs = {k: tk.BooleanVar(value=True) for k in ("auto", "window", "mouse", "sound", "track")}

        def build2(f, sg):
            items = [("auto", "اجرا شدن خودکار با روشن شدن ویندوز"),
                     ("window", "نشستن روی پنجره‌ها (دیدن عنوان و جای پنجره‌ی فعال)"),
                     ("mouse", "قرض گرفتن ماوس برای شوخی‌های کوچیک"),
                     ("sound", "پخش صدا (غرغر و آهنگ‌های کوچیک)"),
                     ("track", "ثبت زمان استفاده از برنامه‌ها (فقط اسم برنامه و مدت؛ روی همین کامپیوتر)")]
            for k, txt in items:
                tk.Checkbutton(f, text=txt, variable=vs[k], bg=CREAM, activebackground=CREAM, fg=INK,
                               font=("Segoe UI", 10), anchor="w", justify="left", wraplength=320
                               ).pack(fill="x", padx=6, pady=2)
            self.L(f, "هر وقت خواستی از منوی «تنظیمات» عوضشون کن. بدون اجازه‌ت هیچی اجرا نمی‌کنم.", 9,
                   fg="#64748b", wrap=320).pack(pady=(8, 4))
            row = tk.Frame(f, bg=CREAM)
            row.pack(pady=4)
            self.B(row, "اجازه می‌دم", lambda: self.close_sign(sg, "ok")).pack(side="left", padx=4)
            self.B(row, "هیچکدوم", lambda: self.close_sign(sg, "none"), bg="#64748b").pack(side="left", padx=4)

        sg2 = self.open_sign("چنتا اجازه لازم دارم", 370, 380, build2, None, timeout=900)
        yield from self.attend_sign(sg2)
        if sg2.result == "ok":
            ok_ = {k: v.get() for k, v in vs.items()}
        else:
            ok_ = {k: False for k in vs}
            if sg2.result in ("skip", "timeout"):
                ok_["sound"] = True
        self.S["window_ok"], self.S["mouse_ok"] = ok_["window"], ok_["mouse"]
        self.v_window.set(ok_["window"])
        self.v_mouse.set(ok_["mouse"])
        self.S["track_ok"] = ok_["track"]
        self.v_track.set(ok_["track"])
        self.v_sound.set(max(1, self.S["sound"] or 2) if ok_["sound"] else 0)
        self.set_sound()
        if ok_["auto"] and winreg is not None:
            set_autostart(True)
            self.v_auto.set(autostart_enabled())
        self.save()
        got = sum(1 for v in ok_.values() if v)
        self.S["first_run"] = False
        self.onboarding = False
        self.save()
        if got:
            yield from self.react(f"مرسی {n}! بهم اعتماد کردی، ازت مراقبت می‌کنم!", "happy", "dance", 100)
        else:
            yield from self.react("باشه، مشکلی نیست! هر وقت خواستی از تنظیمات اجازه بده.", "happy", "idle", 100)
        self.queue.append(self.ev_challenge)

    def ev_autostart(self, n="رفیق"):
        self.S["first_run"] = False
        self.save()
        yield from self.intro_line(f"خوشبختم {n}! یه چیز دیگه...", 50)

        def build(f, sg):
            self.L(f, "می‌خوای هر بار ویندوز روشن شد من هم خودکار بیام و باهات بازی کنم؟", 12, wrap=270).pack(pady=8)
            row = tk.Frame(f, bg=CREAM)
            row.pack(pady=8)

            def yes():
                set_autostart(True)
                self.v_auto.set(autostart_enabled())
                self.close_sign(sg, "yes")

            self.B(row, "آره بیا!", yes).pack(side="left", padx=5)
            self.B(row, "نه، بعداً", lambda: self.close_sign(sg, "no"), bg="#64748b").pack(side="left", padx=5)

        def cb(res):
            if res == "yes":
                self.queue_react("هوراااا! هر بار ویندوز روشن شه من هم میام!", "happy", "dance", 90)
            else:
                self.queue_react("باشه... خودم یه جوری سر می‌زنم.", "sad", "idle", 70)
            self.queue.append(self.ev_challenge)

        sg = self.open_sign("اجرای خودکار", 330, 200, build, cb)
        yield from self.attend_sign(sg)

    def ev_greet(self):
        h = dt.datetime.now().hour
        g = ("صبح بخیر" if 5 <= h < 12 else "ظهر بخیر" if 12 <= h < 16 else "عصر بخیر" if 16 <= h < 20 else "شب بخیر")
        n = self.S["user_name"]
        yield from self.intro_line(f"{g}{(' ' + n) if n else ''}! دلم برات تنگ شده بود!", 100)
        self.say(f"امروز {persian_date()} است.", 4000)
        yield from self.wait(100, interruptible=False)
        if self.S["last_done"] != today_str():
            self.queue.append(self.ev_challenge)
        else:
            self.say("چالش امروزت رو که زدی! آفرین.", 3500)
            yield from self.wait(80, interruptible=False)

    def ev_challenge(self):
        text, key, op, thr = self.today_challenge()
        done = self.S["last_done"] == today_str()
        yield from self.intro_line("هی! چالش امروز آماده‌ست!", 50)

        def build(f, sg):
            self.L(f, persian_date(), 9, fg="#64748b").pack()
            self.L(f, text, 13, bold=True, wrap=310).pack(pady=12)
            self.L(f, "✓ انجام شده" if done else "هنوز انجام نشده", 11,
                   fg="#16a34a" if done else "#dc2626").pack()
            self.L(f, f"استریک {fa(self.current_streak())} روز  |  سطح {fa(self.level())}  |  امتیاز {fa(self.S['xp'])}",
                   9, fg="#475569").pack(pady=6)
            row = tk.Frame(f, bg=CREAM)
            row.pack(pady=6)
            if not done and key is None:
                self.B(row, "انجامش دادم ✓", lambda: (self.complete_challenge(), self.close_sign(sg, "ok")),
                       bg="#16a34a").pack(side="left", padx=4)
            elif not done:
                self.L(f, "وقتی انجامش بدی خودکار ثبت می‌شه.", 9, fg="#64748b").pack()
            self.B(row, "باشه", lambda: self.close_sign(sg, "ok"), bg="#64748b").pack(side="left", padx=4)

        sg = self.open_sign("چالش روزانه", 360, 330, build, None, hint="هنوز اینجام... چالش رو دیدی؟")
        yield from self.attend_sign(sg)

    def ev_draw(self):
        prompt = random.choice(DRAW_PROMPTS)
        yield from self.intro_line("یه ایده‌ی هنری دارم!", 45)

        def build(f, sg):
            cvs = tk.Canvas(f, width=300, height=190, bg="white", highlightthickness=2,
                            highlightbackground=WOOD, cursor="pencil")
            cvs.pack()
            strokes, st = [], {"col": "#1f2937", "w": 4, "cur": None}

            def down(e):
                st["cur"] = [(e.x, e.y)]
                strokes.append([st["col"], st["w"], st["cur"]])
                r = st["w"] / 2
                cvs.create_oval(e.x - r, e.y - r, e.x + r, e.y + r, fill=st["col"], outline=st["col"])

            def move(e):
                cur = st["cur"]
                if not cur:
                    return
                cvs.create_line(cur[-1][0], cur[-1][1], e.x, e.y, fill=st["col"], width=st["w"], capstyle="round")
                cur.append((e.x, e.y))

            cvs.bind("<ButtonPress-1>", down)
            cvs.bind("<B1-Motion>", move)
            pal = tk.Frame(f, bg=CREAM)
            pal.pack(pady=6)
            for col in ["#1f2937", "#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6", "#a855f7", "#92400e"]:
                lb = tk.Label(pal, bg=col, width=2, height=1, cursor="hand2", relief="raised", bd=2)
                lb.pack(side="left", padx=2)
                lb.bind("<Button-1>", lambda e, c=col: st.update(col=c, w=4))
            er = tk.Label(pal, text="پاک‌کن", bg="white", fg=INK, font=("Segoe UI", 8), cursor="hand2", relief="raised", bd=2)
            er.pack(side="left", padx=4)
            er.bind("<Button-1>", lambda e: st.update(col="white", w=16))
            row = tk.Frame(f, bg=CREAM)
            row.pack()

            def clear():
                cvs.delete("all")
                strokes.clear()

            self.B(row, "پاک کردن همه", clear, bg="#64748b").pack(side="left", padx=4)
            self.B(row, "تمام شد ✓", lambda: (self.finish_draw(prompt, strokes), self.close_sign(sg, "ok"))).pack(
                side="left", padx=4)

        sg = self.open_sign(prompt, 340, 340, build, None, hint="منتظر نقاشی‌ام... هر چی دوست داری بکش!", timeout=300)
        yield from self.attend_sign(sg)

    def finish_draw(self, prompt, strokes):
        strokes = [s for s in strokes if s[2]]
        if not strokes:
            self.queue_react("خالی؟! حداقل یه خط بکش!", "sad", "idle", 60)
            return
        items = []
        for col, w, pts in strokes:
            step = 2 if len(pts) > 80 else 1
            items.append([col, w, [[int(x), int(y)] for x, y in pts[::step]]])
        g = self.S["gallery"]
        g.append({"p": prompt, "d": today_str(), "s": items})
        del g[:-20]
        self.save()
        self.record("drawings", 1)
        self.add_xp(10)
        self.queue_react(random.choice(DRAW_PRAISE), "happy", "cheer", 110, prop="نقاشی تو")

    def show_gallery(self):
        w = self.win("گالری نقاشی‌ها", 520, 420)
        g = self.S["gallery"]
        if not g:
            self.L(w, "هنوز نقاشی نکشیدی! صبر کن تا ازت بخوام.", 12).pack(pady=40)
            return
        frame = tk.Frame(w, bg=CREAM)
        frame.pack(padx=8, pady=8)
        for i, item in enumerate(g[-6:][::-1]):
            cell = tk.Frame(frame, bg=CREAM)
            cell.grid(row=i // 2, column=i % 2, padx=6, pady=6)
            cvs = tk.Canvas(cell, width=240, height=140, bg="white", highlightthickness=2, highlightbackground=WOOD)
            cvs.pack()
            for col, wd, pts in item["s"]:
                sc = 0.8
                if len(pts) == 1:
                    x, y = pts[0]
                    cvs.create_oval(x * sc - 2, y * sc - 2, x * sc + 2, y * sc + 2, fill=col, outline=col)
                else:
                    cvs.create_line([c * sc for p in pts for c in p], fill=col, width=max(1, wd * sc),
                                    capstyle="round", joinstyle="round")
            self.L(cell, short(item["p"], 34), 8, wrap=240).pack()

    def ev_ask(self):
        keys = [k for k in ASKS if k not in self.S["facts"]]
        if not keys:
            return
        key = random.choice(keys)
        q, reply = ASKS[key]
        yield from self.intro_line("هی! یه سوال دارم ازت...", 50)

        def build(f, sg):
            e = tk.Entry(f, font=("Segoe UI", 13), justify="center", width=20)
            e.pack(pady=(10, 8))
            e.focus_set()

            def ok(_=None):
                v = bmp(e.get().strip())[:40]
                if not v:
                    return
                self.S["facts"][key] = v
                self.save()
                self.add_xp(5)
                self.queue_react(reply.format(v=v), "happy", "cheer", 110)
                if key in ("game", "app") and not any(it["kind"] == key and it["name"] == v for it in self.S["library"]):
                    self.queue.append(lambda k=key, n=v: self.ev_showme(k, n))
                self.close_sign(sg, "ok")

            e.bind("<Return>", ok)
            row = tk.Frame(f, bg=CREAM)
            row.pack(pady=6)
            self.B(row, "بگم!", ok).pack(side="left", padx=4)
            self.B(row, "نمی‌گم", lambda: self.close_sign(sg, "skip"), bg="#64748b").pack(side="left", padx=4)

        sg = self.open_sign(q, 340, 220, build, hint="منتظرم... جواب بده دیگه!")
        yield from self.attend_sign(sg)

    def ev_showme(self, kind=None, name=None):
        if kind is None:
            have = {it["kind"] for it in self.S["library"]}
            now = time.time()
            ks = [k for k in SHOW_KINDS if k not in have and now - self.S["no_kinds"].get(k, 0) > 7 * 86400]
            if not ks:
                return
            kind = random.choice(ks)
        info = SHOW_KINDS[kind]
        yield from self.intro_line("یه چیزی می‌خوام نشونم بدی...", 55)
        st = {"path": ""}

        def build(f, sg):
            ent = url = None
            if name:
                self.L(f, name, 14, bold=True).pack(pady=(0, 6))
            else:
                self.L(f, info["q"], 12, bold=True, wrap=310).pack(pady=(0, 6))
                ent = tk.Entry(f, font=("Segoe UI", 12), justify="center", width=22)
                ent.pack()
                ent.focus_set()
            lab = self.L(f, "", 9, fg="#475569", wrap=310)
            if info["file"]:
                self.L(f, info["pick"], 11, wrap=310).pack(pady=(10, 4))
                row = tk.Frame(f, bg=CREAM)
                row.pack()

                def pick_file():
                    p = filedialog.askopenfilename(parent=sg.win, title="فایل رو نشونم بده")
                    if p:
                        st["path"] = p
                        lab.config(text="✓ " + short(os.path.basename(p), 40), fg="#16a34a")

                self.B(row, "انتخاب فایل…", pick_file, bg="#7c3aed").pack(side="left", padx=3)
                if info.get("dir"):
                    def pick_dir():
                        p = filedialog.askdirectory(parent=sg.win, title="پوشه رو نشونم بده")
                        if p:
                            st["path"] = p
                            lab.config(text="✓ " + short(os.path.basename(p) or p, 40), fg="#16a34a")

                    self.B(row, "انتخاب پوشه…", pick_dir, bg="#7c3aed").pack(side="left", padx=3)
            else:
                self.L(f, "آدرس سایت (مثلاً youtube.com):", 11).pack(pady=(10, 4))
                url = tk.Entry(f, font=("Segoe UI", 12), justify="center", width=22)
                url.pack()
            lab.pack(pady=4)

            def save(_=None):
                nm = bmp(((ent.get() if ent else name) or "").strip())[:40]
                target = st["path"]
                if url is not None:
                    u = url.get().strip()
                    if u and not u.startswith(("http://", "https://")):
                        u = "https://" + u
                    target = u if "." in u else ""
                if target and not nm:
                    nm = bmp(os.path.splitext(os.path.basename(target.rstrip("/\\")))[0])[:40] or bmp(target)[:40]
                if not (nm and target):
                    lab.config(text="هم اسمش رو بنویس، هم نشونم بده!", fg="#dc2626")
                    return
                self.add_library(kind, nm, target)
                self.close_sign(sg, "ok")

            row2 = tk.Frame(f, bg=CREAM)
            row2.pack(pady=8)
            self.B(row2, "ثبتش کن ✓", save).pack(side="left", padx=4)
            self.B(row2, "ندارم / بعداً", lambda: self.close_sign(sg, "skip"), bg="#64748b").pack(side="left", padx=4)

        def cb(res):
            if res in ("skip", "timeout"):
                self.S["no_kinds"][kind] = time.time()
                self.save()

        sg = self.open_sign(info["title"], 360, 340 if info["file"] else 300, build, cb,
                            hint="منتظرم نشونم بدی!", timeout=240)
        yield from self.attend_sign(sg)

    def add_library(self, kind, name, target):
        self.S["library"].append({"kind": kind, "name": name, "target": target, "yes": 0, "nos": 0,
                                  "next": time.time() + random.uniform(1200, 2400)})
        del self.S["library"][:-30]
        if kind == "game" and "game" not in self.S["facts"]:
            self.S["facts"]["game"] = name
        self.save()
        self.add_xp(8)
        verb = {"game": "بازی کنیم", "app": "باز کنیم", "music": "گوش بدیم", "site": "بریم سراغش"}[kind]
        self.queue_react(f"«{name}» رو یادم موند! بعداً ازت می‌پرسم دوست داری {verb} یا نه.", "happy", "cheer", 130)

    def launch_item(self, it):
        t = it["target"]
        try:
            if t.startswith(("http://", "https://")):
                webbrowser.open(t)
            elif hasattr(os, "startfile"):
                os.startfile(t)
            else:
                subprocess.Popen(["xdg-open", t])
            return True
        except Exception:
            log_exc()
            return False

    def ev_invite(self, force=False):
        items = self.eligible_items(force)
        if not items:
            return
        it = random.choice(items)
        kind = it["kind"]
        if kind != "site" and not os.path.exists(it["target"]):
            it["next"] = time.time() + 86400
            self.save()
            return
        info = SHOW_KINDS[kind]
        yield from self.intro_line("هی... یه پیشنهاد دارم!", 45)

        def build(f, sg):
            self.L(f, info["ask"].format(n=it["name"]), 13, bold=True, wrap=300).pack(pady=(10, 16))
            row = tk.Frame(f, bg=CREAM)
            row.pack()
            self.B(row, "آره، بزن بریم!", lambda: self.close_sign(sg, "yes")).pack(side="left", padx=4)
            self.B(row, "نه، ممنون", lambda: self.close_sign(sg, "no"), bg="#64748b").pack(side="left", padx=4)

        def cb(res):
            now = time.time()
            if res == "yes":
                it["yes"] += 1
                it["nos"] = 0
                it["next"] = now + 4 * 3600
                ok = self.launch_item(it)
                self.S["mute_until"] = max(self.S["mute_until"], now + (1200 if kind == "game" else 300))
                if ok:
                    self.queue_react("بزن بریم! موفق باشی، من ساکت می‌شم.", "happy", "cheer", 90)
                else:
                    self.queue_react("نتونستم بازش کنم؛ شاید مسیرش عوض شده.", "sad", "idle", 90)
            elif res == "no":
                it["nos"] += 1
                it["next"] = now + min(5 * 86400, 12 * 3600 * 2 ** (it["nos"] - 1))
                self.say("باشه!", 1500)
            else:
                it["next"] = now + 3 * 3600
            self.save()

        sg = self.open_sign("پیشنهاد موجو", 340, 200, build, cb, hint="نظرت چیه؟", timeout=120)
        yield from self.attend_sign(sg)

    def ev_gift(self):
        facts, gifts, now = self.S["facts"], self.S["gifts"], time.time()
        keys = [k for k in GIFTS if facts.get(k) and now - gifts.get(k, 0) > 3 * 86400]
        if not keys:
            return
        k = random.choice(keys)
        v = facts[k]
        msg, tpl, qry = GIFTS[k]
        link = tpl.format(q=urllib.parse.quote(qry.format(v=v)))
        yield from self.intro_line("یه سورپرایز برات دارم!", 50)

        def build(f, sg):
            self.L(f, msg.format(v=v), 13, bold=True, wrap=300).pack(pady=(8, 14))
            row = tk.Frame(f, bg=CREAM)
            row.pack()
            self.B(row, "ببینم ✓", lambda: self.close_sign(sg, "yes")).pack(side="left", padx=4)
            self.B(row, "نه، ممنون", lambda: self.close_sign(sg, "no"), bg="#64748b").pack(side="left", padx=4)

        def cb(res):
            gifts[k] = time.time()
            if res == "yes":
                webbrowser.open(link)
                self.add_xp(3)
                self.queue_react("امیدوارم خوشت بیاد!", "happy", "cheer", 70)
            self.save()

        sg = self.open_sign("هدیه‌ی موجو", 340, 210, build, cb, hint="بازش کن، پشیمون نمی‌شی!")
        yield from self.attend_sign(sg)

    def ev_mood(self):
        yield from self.intro_line("چطوری امروز؟ جدی می‌پرسم!", 50)
        opts = [("عالی ☀", "happy", "وااای عالی! انرژیت منو هم شارژ کرد!"),
                ("خوبم ☺", "happy", "خوبه! منم همینطور."),
                ("معمولی ☁", "idle", "معمولی هم یه جور آرامشه."),
                ("بدم ☂", "sad", "بیا یه بغل مجازی... یه کم استراحت کن، من اینجام."),
                ("خسته‌ام ⚡", "sad", "خسته‌ای؟ یه نفس عمیق بکش و یه لیوان آب بخور. من هم پیشتم.")]

        def build(f, sg):
            self.L(f, "امروز حالت چطوره؟", 12).pack(pady=4)
            for i, (txt, ex, rep) in enumerate(opts):
                self.B(f, txt, lambda i=i, o=opts: (self.finish_mood(o[i]), self.close_sign(sg, "ok")),
                       width=16).pack(pady=3)

        sg = self.open_sign("چک حال و هوا", 300, 340, build, None, hint="یکی رو انتخاب کن!")
        yield from self.attend_sign(sg)

    def finish_mood(self, item):
        txt, ex, rep = item
        self.S["moods"].append([today_str(), 0])
        del self.S["moods"][:-60]
        self.save()
        self.add_xp(3)
        self.queue_react(rep, ex, "idle" if ex == "sad" else "cheer", 110)

    def ev_quiz(self):
        q, opts, right = random.choice(QUIZ)
        yield from self.intro_line("کوییز سرزده!", 40)

        def build(f, sg):
            self.L(f, q, 12, bold=True, wrap=300).pack(pady=(4, 10))
            for i, o in enumerate(opts):
                self.B(f, o, lambda i=i: (self.finish_quiz(i == right, opts[right]), self.close_sign(sg, "ok")),
                       width=22).pack(pady=3)

        sg = self.open_sign("کوییز!", 330, 360, build, None, hint="خجالت نکش، حدس بزن!")
        yield from self.attend_sign(sg)

    def finish_quiz(self, ok, answer):
        if ok:
            self.record("quiz_right", 1)
            self.add_xp(8)
            self.queue_react("آفرین! درست بود!", "happy", "dance", 90)
        else:
            self.queue_react(f"نه! جواب درست «{answer}» بود.", "sad", "idle", 90)

    def ev_play(self):
        yield from self.intro_line("حوصلم سر رفت... بازی کنیم؟", 60)
        games = [("حدس عدد", self.game_guess), ("سنگ کاغذ قیچی", self.game_rps), ("دوز", self.game_ttt),
                 ("ریاضی سریع", self.game_math), ("تست واکنش", self.game_reaction),
                 ("کیک‌پزی", self.game_cake)]

        def build(f, sg):
            self.L(f, "بازی مورد علاقه‌ت کدومه؟", 12).pack(pady=4)
            for name, fn in games:
                self.B(f, name, lambda fn=fn: (self.close_sign(sg, "ok"), self.root.after(150, fn)), width=18).pack(pady=3)
            self.B(f, "بعداً", lambda: self.close_sign(sg, "skip"), bg="#64748b", width=18).pack(pady=3)

        sg = self.open_sign("بازی کنیم؟", 300, 380, build, None, hint="بازی... بازی... بازی...")
        yield from self.attend_sign(sg)

    def ev_feed(self):
        yield from self.intro_line("شکمم قار و قور می‌کنه! یه چیزی بده بخورم.", 70)

        def build(f, sg):
            self.L(f, "چی بدم موجو بخوره؟", 12).pack(pady=4)
            grid = tk.Frame(f, bg=CREAM)
            grid.pack()
            for i, (name, kind, rep) in enumerate(FOODS):
                self.B(grid, name, lambda k=kind, r=rep, n=name: (self.close_sign(sg, "ok"), self.feed_react(k, r, n)),
                       width=10).grid(row=i // 2, column=i % 2, padx=4, pady=3)

        sg = self.open_sign("غذا بده!", 300, 330, build, None, hint="هنوز گرسنه‌ام...")
        yield from self.attend_sign(sg)

    def feed_react(self, kind, text, name=None):
        self.add_xp(2)
        self.queue.insert(0, lambda: self.eat(kind, text, name))

    FOOD_CRUMB = {"کیک": "#f6dfa4", "سیب": "#dc2626", "موز": "#facc15", "پیتزا": "#fbbf24", "شکلات": "#78350f", "بروکلی": "#16a34a",
                  "فلفل تند": "#dc2626", "برگر": "#d97706", "بستنی": "#fda4af", "هندوانه": "#dc2626"}

    def eat(self, kind, text, name=None, style=None):
        name = name or "سیب"
        fd = self.food = {"name": name, "k": 0.0, "bites": 0, "crumbs": [], "pos": (CXC, FOOT - 40), "vy": 0.0,
                          "style": style}
        try:
            self.expr, self.anim = "happy", "idle"
            self.snd.play("pop", force=True)
            self.pulse(0.15, -0.15)
            self.say(f"اوه {name}!", 1800)
            yield from self.wait(30, interruptible=False)
            for i in range(22):
                fd["k"] = i / 21.0
                yield
            nb = 3
            for bi in range(nb):
                for i in range(7):
                    fd["k"] = 1.0 - 0.28 * math.sin(math.pi * i / 6.0)
                    yield
                fd["bites"] += 1
                self.expr = "eat"
                self.pulse(0.12, -0.12)
                self.snd.play("pop", force=True)
                mxp, myp = fd["pos"]
                col = self.FOOD_CRUMB.get(name, "#fbbf24")
                for _ in range(5):
                    fd["crumbs"].append([mxp + random.uniform(-6, 6), myp - 6, random.uniform(-2.5, 2.5),
                                         random.uniform(-4, -1), random.randint(14, 24), col])
                for i in range(16):
                    yield
                if kind in ("hot", "yuck") and bi == 0:
                    break
            if kind == "yuck":
                self.expr = "sad"
                self.say(text)
                fd["drop"] = True
                fd["vx"] = -self.face * 2.0
                yield from self.wait(100, interruptible=False)
            elif kind == "hot":
                self.food = None
                self.set_color("#f87171")
                self.say(text)
                self.expr, self.anim = "surprised", "run"
                l, t, r, b = self.area()
                for _ in range(3):
                    yield from self.walk_to(random.choice([l + 60, r - 60]), speed=8.0, anim="run", interruptible=False)
                self.set_color(self.body_col())
            else:
                self.food = None
                self.expr, self.anim = "happy", "dance" if kind == "love" else "idle"
                self.say(text)
                yield from self.wait(90, interruptible=False)
        finally:
            self.food = None
        self.reset_look()

    def ev_health(self):
        k, text = random.choice(HEALTH)
        yield from self.intro_line("یه یادآوری کوچولو...", 40)

        def build(f, sg):
            self.L(f, text, 13, bold=True, wrap=290).pack(pady=14)
            row = tk.Frame(f, bg=CREAM)
            row.pack(pady=6)
            self.B(row, "انجام شد ✓", lambda: (self.add_xp(2), self.queue_react("آفرین به تو!", "happy", "cheer", 70),
                                                self.close_sign(sg, "ok")), bg="#16a34a").pack(side="left", padx=4)
            self.B(row, "بعداً", lambda: self.close_sign(sg, "skip"), bg="#64748b").pack(side="left", padx=4)

        sg = self.open_sign("وقت استراحت", 320, 230, build, None)
        yield from self.attend_sign(sg)

    def ev_chase(self):
        yield from self.get_down()
        need = 4
        self.catch = {"on": True, "n": 0, "need": need}
        self.say(f"منو بگیر! {fa(need)} بار روی من کلیک کن... اگه می‌تونی!", 4500)
        self.expr = "sneaky"
        vx = vy = 0.0
        end = self.t + 30 * 30
        while self.catch and self.catch["n"] < need and self.t < end:
            l, tp, r, b = self.area()
            px, py = self.root.winfo_pointerxy()
            cx, cy = self.fx(), self.fy() - 45
            dx, dy = cx - px, cy - py
            d = math.hypot(dx, dy) or 1.0
            if d < 300:
                k = (300 - d) / 300
                vx += dx / d * (1.2 + 2.2 * k)
            else:
                vx += random.uniform(-0.5, 0.5)
            vx = clamp(vx * 0.92, -12, 12)
            vy += 0.9
            nx, ny = self.fx() + vx, self.fy() + vy
            if nx < l + 40:
                nx, vx = l + 40, abs(vx) + 4
            if nx > r - 40:
                nx, vx = r - 40, -abs(vx) - 4
            g = self.ground()
            if ny >= g:
                ny = g
                vy = -random.uniform(5, 8) if (d < 220 or random.random() < 0.02) else 0.0
            self.put(nx, ny)
            self.face = 1 if vx > 0 else -1
            self.anim = "run" if ny >= g - 2 else "jump"
            yield
        c = self.catch or {"n": 0}
        n = c["n"]
        self.catch = None
        yield from self.fall()
        if n >= need:
            self.record("catches", n)
            self.add_xp(15)
            yield from self.react("آخ! گرفتیم! تو سریع‌ترینی!", "happy", "dance", 100)
        else:
            self.record("catches", n)
            yield from self.react("هههه! نتونستی بگیریم!", "sneaky", "dance", 90)

    def catch_hit(self):
        c = self.catch
        c["n"] += 1
        self.pulse(0.3, -0.3)
        self.snd.play("pop", force=True)
        left = c["need"] - c["n"]
        self.say("گرفتی!" if left <= 0 else f"آخ! {fa(left)} تای دیگه!", 1800)
        l, tp, r, b = self.area()
        far = random.choice([l + 80, r - 80])
        self.put(far if abs(far - self.fx()) > 250 else (l + r) / 2, self.ground())

    def ev_peek(self):
        yield from self.get_down()
        l, tp, r, b = self.area()
        side = random.choice([-1, 1])
        edge = l - 8 if side == -1 else r + 8
        self.expr = "sneaky"
        self.snd.play("whoosh")
        yield from self.walk_to(edge, speed=7.0, anim="run", free=True, interruptible=False)
        self.face = 1 if side == -1 else -1
        self.anim = "idle"
        yield from self.wait(30, interruptible=False)
        self.say(random.choice(PEEK_LINES), 3000)
        self.expr = "happy"
        yield from self.wait(100, interruptible=False)
        self.pulse(0.1, 0.2)
        yield from self.walk_to(random.uniform(l + 150, r - 150), speed=6.0, anim="run", interruptible=False)
        self.reset_look()

    def ev_parade(self):
        yield from self.get_down()
        l, tp, r, b = self.area()
        side = random.choice([-1, 1])
        start = l - 70 if side == -1 else r + 70
        end = r + 70 if side == -1 else l - 70
        near = self.fx() < (l + r) / 2
        yield from self.walk_to(l - 70 if near else r + 70, speed=8.0, anim="run", free=True, interruptible=False)
        start, end = (l - 70, r + 70) if near else (r + 70, l - 70)
        self.put(start, self.ground())
        self.prop = random.choice(PARADE_TEXTS)
        self.expr = "happy"
        yield from self.walk_to(end, speed=2.6, anim="walk", free=True, interruptible=False)
        self.prop = None
        yield from self.walk_to(l + 200 if end < 0 else r - 200, speed=5.0, anim="run", interruptible=False)
        self.reset_look()

    def ev_steal(self):
        yield from self.get_down()
        self.expr = "sneaky"
        self.say("psst... ماوست رو یه لحظه قرض می‌گیرم!", 2800)
        for _ in range(240):
            px, py = self.root.winfo_pointerxy()
            if abs(px - self.fx()) < 40:
                break
            d = 1 if px > self.fx() else -1
            self.face, self.anim = d, "run"
            self.x += d * 7
            yield
        self.say("گرفتمش! بیا بریم یه دور!", 2500)
        l, tp, r, b = self.area()
        tx = random.uniform(l + 150, r - 150)
        for _ in range(100):
            d = 1 if tx > self.fx() else -1
            if abs(tx - self.fx()) < 6:
                break
            self.face, self.anim = d, "walk"
            self.x += d * 5
            set_cursor(self.fx(), self.fy() - 55)
            yield
        self.expr = "happy"
        self.say("باشه باشه، بیا پسش بگیر!", 2500)
        self.anim = "wave"
        yield from self.wait(70, interruptible=False)
        self.reset_look()

    def ev_spy(self):
        yield from self.b_window(spy=True)

    def ev_glitch(self):
        yield from self.get_down()
        self.expr = "glitch"
        self.snd.play("glitch", force=True)
        ox, oy = self.x, self.y
        cols = ["#f472b6", "#fde047", "#60a5fa", "#a3e635", "#5eead4"]
        for i in range(55):
            self.x, self.y = ox + random.randint(-7, 7), oy + random.randint(-3, 3)
            if i % 4 == 0:
                self.set_color(random.choice(cols))
            yield
        self.x, self.y = ox, oy
        self.reset_look()
        self.expr = "surprised"
        self.say(random.choice(GLITCH_LINES), 5000)
        yield from self.wait(120, interruptible=False)
        self.reset_look()

    def ev_alarm(self, text):
        l, tp, r, b = self.area()
        yield from self.get_down()
        yield from self.walk_to((l + r) / 2, speed=8.0, anim="run", interruptible=False)
        w = tk.Toplevel(self.root)
        w.title("Mojo alarm")
        w.configure(bg="#c62828")
        w.attributes("-topmost", True)
        w.overrideredirect(True)
        sw = self.root.winfo_screenwidth()
        w.geometry(f"460x200+{(sw - 460) // 2}+60")
        tk.Label(w, text=bmp("⏰  " + text), bg="#c62828", fg="white", font=("Segoe UI", 18, "bold"),
                 wraplength=420).pack(pady=(28, 8))
        tk.Label(w, text="زود باش الان کارت دیر میشه", bg="#c62828", fg="#fee2e2", font=("Segoe UI", 14)).pack()
        tk.Button(w, text="باشه، رفتم!", command=w.destroy, font=F, bg="white", fg="#c62828", relief="flat",
                  padx=16, pady=4).pack(pady=16)
        w.after(60000, lambda: w.destroy() if alive(w) else None)
        self.beep()
        self.say(f"{text}! زود باش!", 6000)
        self.anim, self.expr = "cheer", "surprised"
        yield from self.wait(150, interruptible=False)
        self.reset_look()

    def beep(self):
        def run():
            for _ in range(4):
                try:
                    if winsound:
                        winsound.Beep(1100, 250)
                except Exception:
                    pass
                time.sleep(0.25)
        threading.Thread(target=run, daemon=True).start()

    def start_study(self):
        self.run_ev(self._study_dialog)

    def _study_dialog(self):
        def build(f, sg):
            self.L(f, "📚 چه مدت مطالعه کنیم؟", 13, bold=True, wrap=280).pack(pady=(8, 12))
            row = tk.Frame(f, bg=CREAM)
            row.pack()
            for mins in (5, 10, 20):
                self.B(row, f"{fa(mins)} دقیقه",
                       lambda m=mins: (self.begin_study(m), self.close_sign(sg, "ok")),
                       width=8).pack(side="left", padx=3)
            self.L(f, "یا خودت بنویس (دقیقه):", 10, fg="#64748b").pack(pady=(10, 4))
            custom = tk.Frame(f, bg=CREAM)
            custom.pack()
            ent = tk.Entry(custom, font=("Segoe UI", 12), justify="center", width=6)
            ent.pack(side="left", padx=4)

            def go_custom(_=None):
                try:
                    m = to_int(ent.get())
                except (ValueError, AttributeError):
                    return
                if 1 <= m <= 120:
                    self.begin_study(m)
                    self.close_sign(sg, "ok")

            ent.bind("<Return>", go_custom)
            self.B(custom, "شروع", go_custom).pack(side="left", padx=4)
            self.L(f, "من هم یه کتاب میارم و کنارت می‌خونم 🤫",
                   9, fg="#64748b", wrap=260).pack(pady=(12, 0))

        sg = self.open_sign("📖 مطالعه", 320, 260, build, None,
                            hint="کدوم مدت رو می‌خوای؟")
        yield from self.attend_sign(sg)

    def begin_study(self, minutes):
        total = int(minutes) * 60
        self.study = {"total": total, "until": None, "stage": "fetch", "minutes": int(minutes),
                      "started": False, "flip_t0": None, "next_flip": 0.0, "t0": 0, "t1": 0}
        self.next_event = time.time() + total + 90
        self.queue.clear()
        self.stop_gen()
        self.gen = None

    def do_study(self):
        st = self.study
        if not st:
            return
        l, tp, r, b = self.area()
        if not st["started"]:
            st["started"] = True
            yield from self.get_down()
            self.expr = "happy"
            self.say("باشه! یه لحظه صبر کن، برم کتابمو بیارم", 2800)
            yield from self.wait(28, interruptible=False)
            edge = l - 110 if self.fx() < (l + r) / 2 else r + 110
            yield from self.walk_to(edge, speed=7.0, anim="run", free=True, interruptible=False)
            st["stage"] = "carry"
            yield from self.wait(20, interruptible=False)
            spot = random.uniform(l + 230, max(l + 231, r - 300))
            self.face = 1 if spot > self.fx() else -1
            yield from self.walk_to(spot, speed=2.7, anim="walk", free=True, interruptible=False)
            self.anim = "idle"
            st["stage"], st["t0"] = "down", self.t
            self.say("اوف... چقدر سنگینه!", 2200)
            yield from self.wait(24, interruptible=False)
            self.snd.play("thud", force=True)
            self.pulse(0.25, -0.25)
            yield from self.wait(8, interruptible=False)
            st["stage"], st["t1"] = "open", self.t
            self.anim, self.expr = "read", "happy"
            self.snd.play("page", force=True)
            yield from self.wait(16, interruptible=False)
        else:
            yield from self.get_down()
        st["stage"] = "read"
        self.anim, self.expr = "read", "happy"
        if st["until"] is None:
            st["until"] = time.time() + st["total"]
            self.say(f"شروع کردیم! {fa(st['minutes'])} دقیقه مطالعه... هیس!", 3500)
        st["next_flip"] = time.time() + random.uniform(8, 14)
        while self.study is st and time.time() < st["until"]:
            if self.queue:
                spot = self.fx()
                fn = self.queue.pop(0)
                gen = fn()
                if gen is not None:
                    yield from gen
                if self.study is not st:
                    return
                yield from self.walk_to(spot, speed=6.0, anim="run", free=True, interruptible=False)
                self.anim, self.expr = "read", "happy"
            if time.time() >= st["next_flip"]:
                st["flip_t0"] = self.t
                self.snd.play("page")
                st["next_flip"] = time.time() + random.uniform(12, 24)
            yield
        if self.study is not st:
            return
        st["stage"] = "done"
        self.anim, self.expr = "cheer", "happy"
        self.snd.play("yay", force=True)
        self.say("زمان مطالعه تموم شد! آفرین به تو", 5500)
        self.add_xp(15 + st["minutes"] // 5)
        self.S["study_total"] = self.S.get("study_total", 0) + 1
        self.S["study_count"] = self.S.get("study_count", 0) + 1
        self.S["study_minutes"] = self.S.get("study_minutes", 0) + st["minutes"]
        self.save()
        yield from self.wait(150, interruptible=False)
        if self.study is st:
            self.study = None
        self.reset_look()

    def study_left_text(self):
        st = self.study
        if not st or st.get("until") is None:
            return None
        left = max(0, int(math.ceil(st["until"] - time.time())))
        m, s = divmod(left, 60)
        if m and s:
            return f"{fa(m)} دقیقه و {fa(s)} ثانیه"
        return f"{fa(m)} دقیقه" if m else f"{fa(s)} ثانیه"

    def study_whisper(self):
        txt = self.study_left_text()
        if txt is None:
            self.say("صبر کن... دارم کتابمو میارم!", 2500)
            return
        st = self.study
        left = st["until"] - time.time()
        if left <= 60:
            line = f"آخراشه! فقط {txt} مونده!"
        elif left > st["total"] * 0.75:
            line = random.choice([f"تازه شروع کردیم... {txt} مونده.", f"هیس... {txt} تا تموم شدن مونده."])
        else:
            line = random.choice([f"هیس... {txt} دیگه مونده!", f"{txt} تا تموم شدن مونده؛ ادامه بده!",
                                  f"فقط {txt} دیگه! داری عالی پیش می‌ری."])
        self.pulse(0.15, -0.15)
        self.say(line, 3500)

    def cancel_study(self):
        if not self.study:
            return
        self.study = None
        self.stop_gen()
        self.gen = None
        self.reset_look()
        self.say("باشه، مطالعه رو متوقف کردیم. هر وقت خواستی دوباره شروع می‌کنیم!", 4000)

    def on_press(self, e):
        if self.onboarding or self.throwing:
            return
        if self.study:
            self.study_whisper()
            return
        if self.catch and self.catch.get("on"):
            self.catch_hit()
            return
        self._drag = (e.x_root - self.x, e.y_root - self.y, e.x_root, e.y_root, False)

    def on_drag(self, e):
        if self.study or self.onboarding or self.throwing:
            return
        if not self._drag or (self.catch and self.catch.get("on")):
            return
        ox, oy, sx, sy, moved = self._drag
        if not moved and abs(e.x_root - sx) + abs(e.y_root - sy) > 5:
            moved = True
            self.stop_gen()
            self.dragging = True
            self.anim, self.expr = "held", "surprised"
            self.on_window = self.win_lim = self.floor = None
        if moved:
            self.x, self.y = e.x_root - ox, e.y_root - oy
        self._drag = (ox, oy, sx, sy, moved)

    def on_release(self, e):
        if self.study or self.onboarding or self.throwing:
            return
        d, self._drag = self._drag, None
        if not d:
            return
        if self.dragging:
            self.dragging = False
            self.gen = self.after_drop()
        elif not d[4]:
            self.stop_gen()
            self.gen = self.poke()

    # ───────────── پرتاب تخم‌مرغ / گوجه به صفحه ─────────────
    def clickthrough(self, win):
        if sys.platform != "win32":
            return
        try:
            import ctypes
            u = ctypes.windll.user32
            win.update_idletasks()
            h = u.GetParent(win.winfo_id()) or win.winfo_id()
            st = u.GetWindowLongW(h, -20)
            u.SetWindowLongW(h, -20, st | 0x80000 | 0x20 | 0x80)
        except Exception:
            pass

    def make_overlay(self, w, h, x, y):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-transparentcolor", TRANSP)
        except tk.TclError:
            pass
        win.configure(bg=TRANSP)
        win.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")
        cv = tk.Canvas(win, width=int(w), height=int(h), bg=TRANSP, highlightthickness=0, bd=0)
        cv.pack()
        self.clickthrough(win)
        return win, cv

    def draw_missile(self, c, kind, cx, cy, r, ang):
        if kind == "egg":
            pts = []
            for i in range(28):
                th = 2 * math.pi * i / 28
                u, v = math.sin(th) * (1 - 0.15 * math.cos(th)) * 0.78, -math.cos(th)
                x, y = u * r, v * r
                pts += [cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)]
            c.create_polygon(pts, fill="#fff3d6", outline="#c9a76a", width=2, smooth=True)
            c.create_oval(cx - r * 0.35, cy - r * 0.5, cx - r * 0.1, cy - r * 0.15, fill="white", outline="")
        else:
            c.create_oval(cx - r, cy - r * 0.9, cx + r, cy + r * 0.9, fill="#e11d2e", outline="#8f0f1a", width=2)
            c.create_oval(cx - r * 0.55, cy - r * 0.6, cx - r * 0.2, cy - r * 0.3, fill="#ff8a8a", outline="")
            for k in range(5):
                a = ang + k * 1.26
                c.create_polygon(cx + math.cos(a) * r * 0.1, cy - r * 0.85 + math.sin(a) * 4,
                                 cx + math.cos(a + 0.5) * r * 0.55, cy - r * 0.8 + math.sin(a + 0.5) * 6,
                                 cx + math.cos(a + 1.0) * r * 0.15, cy - r * 0.95,
                                 fill="#2f9e44", outline="#1b6b2c")

    def throw_at_screen(self):
        self.throwing = True
        try:
            yield from self.throw_body()
        finally:
            self.throwing = False

    def throw_body(self):
        kind = random.choice(("egg", "tomato"))
        name = "تخم‌مرغ" if kind == "egg" else "گوجه"
        self.expr, self.anim = "sneaky", "idle"
        self.say(f"بسه دیگه!! بیا {name} بخور!", 2600)
        self.snd.play("glitch", force=True)
        yield from self.wait(40, interruptible=False)
        l, t, r, b = self.area()
        tx = random.uniform(l + 200, r - 200)
        ty = random.uniform(t + 150, b - 280)
        sx0, sy0 = self.fx(), self.fy() - 60
        self.anim = "cheer"
        self.snd.play("whoosh", force=True)
        n = 15
        win = cv = None
        win, cv = self.make_overlay(self.root.winfo_screenwidth(), self.root.winfo_screenheight(), 0, 0)
        for i in range(1, n + 1):
            s = i / n
            x = sx0 + (tx - sx0) * s
            y = sy0 + (ty - sy0) * s - 90 * 4 * s * (1 - s) * 0.5
            rr = 10 + 70 * s * s
            cv.delete("all")
            self.draw_missile(cv, kind, x, y, rr, s * 9)
            yield
        try:
            win.destroy()
        except tk.TclError:
            pass
        self.snd.play("thud", force=True)
        self.snd.play("squeak", force=True)
        self.add_splat(kind, tx, ty)
        self.expr, self.anim = "happy", "dance"
        self.say(random.choice(["هههه! نشونه‌ی دقیق!", "خودت خواستی!", "بوم! تو دردسر افتادی!"]), 3500)
        self.snd.play("giggle", force=True)
        yield from self.wait(90, interruptible=False)
        self.reset_look()

    def add_splat(self, kind, cx, cy):
        W, H = 300, 520
        x0, y0 = cx - W / 2, max(0, cy - 150)
        win, cv = self.make_overlay(W, H, x0, y0)
        rnd = random.Random()
        blob = []
        for i in range(22):
            th = 2 * math.pi * i / 22
            rr = (92 if i % 2 else 62) * rnd.uniform(0.8, 1.15)
            blob += [W / 2 + math.cos(th) * rr, 150 + math.sin(th) * rr * 0.85]
        drips = [(W / 2 + rnd.uniform(-60, 60), rnd.uniform(28, 55), rnd.uniform(0.7, 1.4)) for _ in range(6)]
        dots = [(W / 2 + rnd.uniform(-125, 125), 150 + rnd.uniform(-115, 115), rnd.uniform(3, 9)) for _ in range(14)]
        self.splats.append({"win": win, "cv": cv, "kind": kind, "t": 0, "x": x0, "y": y0, "blob": blob,
                            "drips": drips, "dots": dots, "W": W, "H": H, "vy": 0.0,
                            "hold": random.randint(110, 170), "fade": 210})

    def splat_tick(self):
        for sp in list(self.splats):
            try:
                if not alive(sp["win"]) or not self.splat_draw(sp):
                    raise tk.TclError("done")
            except Exception as ex:
                if not isinstance(ex, tk.TclError):
                    log_exc()
                try:
                    sp["win"].destroy()
                except tk.TclError:
                    pass
                self.splats.remove(sp)

    def splat_draw(self, sp):
        sp["t"] += 1
        t, hold, fade = sp["t"], sp["hold"], sp["fade"]
        k = clamp((t - hold) / fade, 0.0, 1.0)
        if k >= 1.0:
            return False
        if t > hold:
            sp["vy"] += 0.007
            sp["y"] += 0.25 + sp["vy"] * (1 + k)
        try:
            sp["win"].attributes("-alpha", clamp(1.0 - k * 0.97, 0.03, 1.0))
        except tk.TclError:
            pass
        sp["win"].geometry(f"+{int(sp['x'])}+{int(sp['y'])}")
        c, W = sp["cv"], sp["W"]
        c.delete("all")
        egg = sp["kind"] == "egg"
        main, rim = ("#fff6e0", "#d8bf86") if egg else ("#d7192b", "#8f0f1a")
        grow = clamp(t / 6.0, 0.3, 1.0)
        ext = 1.0 + 3.2 * k
        for (dx, ln, wd) in sp["drips"]:
            L_ = ln * ext * 1.7 * grow
            w_ = 7 * wd
            c.create_line(dx, 150, dx, 150 + 60 + L_, width=w_, fill=main, capstyle="round")
            c.create_oval(dx - w_ * 0.8, 150 + 60 + L_ - w_ * 0.8, dx + w_ * 0.8, 150 + 60 + L_ + w_ * 0.8,
                          fill=main, outline="")
        pts = [W / 2 + (v - W / 2) * grow if i % 2 == 0 else 150 + (v - 150) * grow for i, v in enumerate(sp["blob"])]
        c.create_polygon(pts, fill=main, outline=rim, width=3, smooth=True)
        for x, y, r in sp["dots"]:
            c.create_oval(x - r, y - r, x + r, y + r, fill=main, outline="")
        if egg:
            c.create_oval(W / 2 - 34, 150 - 30, W / 2 + 34, 150 + 30, fill="#ffb703", outline="#e08a00", width=2)
            c.create_oval(W / 2 - 18, 150 - 20, W / 2 - 4, 150 - 8, fill="#ffe08a", outline="")
            for (x, y) in ((W / 2 - 80, 205), (W / 2 + 70, 95)):
                c.create_polygon(x, y, x + 16, y + 6, x + 6, y + 18, fill="#fff9ee", outline="#d8bf86")
        else:
            for (x, y) in ((W / 2 - 30, 130), (W / 2 + 26, 168), (W / 2 - 8, 190), (W / 2 + 40, 120), (W / 2 - 55, 172)):
                c.create_oval(x - 4, y - 3, x + 4, y + 3, fill="#ffd166", outline="")
            c.create_oval(W / 2 - 52, 100, W / 2 - 22, 118, fill="#ff7b84", outline="")
        return True

    def after_drop(self):
        g = self.ground()
        dist = g - self.fy()
        own = self.S.get("owned", {})
        self.throwing = True          # در این مدت هیچ‌چیز کار نمی‌کنه (کلیک، منو، رویداد)
        try:
            if dist > 130 and own.get("parachute"):
                yield from self.chute_fall(g)
                yield from self.react(random.choice(["چتر نجات نجاتم داد!", "فرود نرم! چه حالی داد!", "ممنون از چتر!"]),
                                      "happy", "cheer", 70)
            else:
                yield from self.fall()
                if dist > DIZZY_DIST:
                    yield from self.dizzy()
                else:
                    yield from self.react(random.choice(DROP_LINES), "surprised", "idle", 60)
        finally:
            self.throwing = False
            self.chute = None

    def chute_fall(self, floor):
        ch = self.chute = {"t": 0, "fold": 0, "sway": 0.0,
                           "color": random.choice(["#ef4444", "#3b82f6", "#f59e0b", "#a855f7", "#10b981"])}
        self.anim, self.expr = "chute", "surprised"
        self.snd.play("whoosh", force=True)
        vy = 10.0
        x0 = self.x
        l, tp, r, b = self.area()
        while self.fy() < floor:
            ch["t"] += 1
            vy = max(2.2, vy - 0.6)
            self.y += vy
            ch["sway"] = math.sin(ch["t"] / 9.0) * 12
            self.x = clamp(self.x + math.sin(ch["t"] / 11.0) * 1.4, l - 60, r - CW + 60)
            if ch["t"] == 12:
                self.expr = "happy"
            if self.fy() > floor:
                self.y = floor - FOOT
            yield
        self.anim, self.expr = "idle", "happy"
        self.pulse(0.18, -0.18)
        self.snd.play("land", force=True)
        for _ in range(20):
            ch["fold"] += 1
            yield
        self.chute = None
        self.floor = self.on_window = self.win_lim = None

    def dizzy(self):
        self.expr, self.anim = "dizzy", "idle"
        self.snd.play("glitch", force=True)
        self.say("ووووی... دنیا داره می‌چرخه...", 3400)
        x0 = self.x
        l, tp, r, b = self.area()
        for i in range(DIZZY_FRAMES):
            amp = 12 * (1 - i / float(DIZZY_FRAMES)) + 2
            self.x = clamp(x0 + math.sin(i / 5.0) * amp, l - 40, r - CW + 40)
            self.sx = 1 + math.sin(i / 7.0) * 0.06
            if i == DIZZY_FRAMES // 2:
                self.say("همه‌چی دوتا دوتا شده...", 2600)
            yield
        self.x = clamp(x0, l - 40, r - CW + 40)
        self.reset_look()
        yield from self.react("اوف... حالم بهتر شد! دیگه همه‌چی کار می‌کنه.", "happy", "cheer", 70)

    def ev_fly(self):
        if not self.S.get("owned", {}).get("jetpack"):
            return
        self.throwing = True
        try:
            yield from self.get_down()
            l, t, r, b = self.area()
            self.expr, self.anim = "happy", "idle"
            self.say(random.choice(["وقت پروازه! جت‌پکم کو؟", "یه چرخ تو آسمون بزنم؟", "جت‌پک آماده‌ست!"]), 2800)
            jt = self.jet = {"on": False, "wear": 0}
            for i in range(14):
                jt["wear"] = i + 1
                yield
            yield from self.wait(18, interruptible=False)
            jt["on"] = True
            self.snd.play("whoosh", force=True)
            self.expr = "surprised"
            yield from self.wait(14, interruptible=False)
            self.anim, self.expr = "fly", "happy"
            fmin = t + 135
            x0, y0 = self.fx(), self.fy()
            ty = random.uniform(fmin, fmin + 70)
            for i in range(1, 56):
                k = ease_out(i / 55.0)
                self.put(x0 + math.sin(i / 6.0) * 6, lerp(y0, ty, k))
                if i % 22 == 0:
                    self.snd.play("whoosh", force=True)
                yield
            lines = ["ویییی! من پرنده‌ام!", "بالاتر از ابرا!", "فضا اینجاست؟", "هورااا!", "نگاه کن چه بلندم!"]
            for wp in range(random.randint(3, 5)):
                tx = random.uniform(l + 90, r - 90)
                ty2 = random.uniform(fmin, max(fmin + 40, b - 280))
                sx_, sy_ = self.fx(), self.fy()
                self.face = 1 if tx > sx_ else -1
                n = int(clamp(math.hypot(tx - sx_, ty2 - sy_) / 7.0, 40, 130))
                if wp == 0 or random.random() < 0.6:
                    self.say(random.choice(lines), 2200)
                for i in range(1, n + 1):
                    k = i / float(n)
                    e = k * k * (3 - 2 * k)
                    self.put(lerp(sx_, tx, e), lerp(sy_, ty2, e) + math.sin(i / 5.0) * 5)
                    if i % 24 == 0:
                        self.snd.play("whoosh", force=True)
                    yield
                yield from self.wait(random.randint(6, 24), interruptible=False)
            g = self.ground()
            sx_, sy_ = self.fx(), self.fy()
            tx = clamp(sx_, l + 80, r - 80)
            n = 80
            self.say("فرود می‌کنم... آروم آروم...", 2400)
            for i in range(1, n + 1):
                k = ease_out(i / float(n))
                self.put(lerp(sx_, tx, k), lerp(sy_, g, k))
                yield
            self.anim = "idle"
            jt["on"] = False
            self.pulse(0.3, -0.3)
            self.snd.play("land", force=True)
            self.floor = self.on_window = self.win_lim = None
            for i in range(14):
                jt["wear"] = 14 - i
                yield
            self.jet = None
            yield from self.react(random.choice(["پرواز عالی بود!", "دلم می‌خواد دوباره پرواز کنم!", "آسمون دسکتاپ قشنگه!"]),
                                  "happy", "dance", 70)
        finally:
            self.jet = None
            self.throwing = False
            if self.anim == "fly":
                self.anim = "idle"

    def poke(self):
        now = time.time()
        self.pokes = [p for p in self.pokes if now - p < 8] + [now]
        self.pulse(0.3, -0.3)
        self.snd.play("squeak", force=True)
        if len(self.pokes) >= 5 and random.random() < 0.6:
            self.pokes = []
            yield from self.throw_at_screen()
            return
        if len(self.pokes) >= 5:
            self.pokes = []
            self.say("بسه دیگه!! فرار می‌کنم!", 2500)
            self.expr = "surprised"
            l, tp, r, b = self.area()
            yield from self.walk_to(random.choice([l + 100, r - 100]), speed=9.0, anim="run", interruptible=False)
            self.reset_look()
            return
        self.expr, self.anim = "happy", "cheer"
        self.say(random.choice(POKES), 2500)
        yield from self.wait(45, interruptible=False)
        self.reset_look()

    def run_ev(self, fn):
        if self.onboarding or self.throwing:
            return
        if self.study and fn != self._study_dialog:
            self.study_whisper()
            return
        self.queue.append(fn)
        self.stop_gen()

    def popup(self, e):
        if self.onboarding or self.throwing:
            return
        m = tk.Menu(self.root, tearoff=0, font=F)
        if self.study:
            m.add_command(label="⏱ چقدر مونده؟", command=self.study_whisper)
            m.add_command(label="⏹ توقف مطالعه", command=self.cancel_study)
            m.add_separator()
        fun = tk.Menu(m, tearoff=0, font=F)
        for name, fn in [("🎲 حدس عدد", self.game_guess),
                         ("✊ سنگ کاغذ قیچی", self.game_rps),
                         ("⭕ دوز", self.game_ttt),
                         ("➗ ریاضی سریع", self.game_math),
                         ("⚡ تست واکنش", self.game_reaction),
                         ("🎂 کیک‌پزی", self.game_cake)] + (
                [("🚀 پرواز با جت‌پک", self.ev_fly)] if self.S.get("owned", {}).get("jetpack") else []):
            fun.add_command(label=name, command=lambda fn=fn: self.run_ev(fn))
        m.add_cascade(label="🎮 سرگرمی", menu=fun)
        tools = tk.Menu(m, tearoff=0, font=F)
        tools.add_command(label="📖 مطالعه", command=self.start_study)
        tools.add_command(label="⏰ یادآور", command=self.add_reminder)
        tools.add_command(label="🖼️ گالری نقاشی‌ها", command=self.show_gallery)
        tools.add_command(label="💻 وضعیت سیستم", command=self.sys_info)
        tools.add_command(label="📊 زمان استفاده از برنامه‌ها", command=self.show_usage)
        tools.add_command(label="📅 تاریخ امروز", command=lambda: self.say(persian_date()))
        m.add_cascade(label="🛠️ ابزارها", menu=tools)
        st = tk.Menu(m, tearoff=0, font=F)
        chaos = tk.Menu(st, tearoff=0, font=F)
        for v, name in [(1, "آروم"), (2, "متوسط"), (3, "شیطون!")]:
            chaos.add_radiobutton(label=name, value=v, variable=self.v_chaos, command=self.set_chaos)
        st.add_cascade(label="میزان شیطونی", menu=chaos)
        snd = tk.Menu(st, tearoff=0, font=F)
        for v, name in [(0, "خاموش"), (1, "کم"), (2, "متوسط"), (3, "بلند")]:
            snd.add_radiobutton(label=name, value=v, variable=self.v_sound, command=self.set_sound)
        st.add_cascade(label="صدا", menu=snd)
        st.add_command(label="🎨 رنگ‌ها و فروشگاه...", command=self.show_colors)
        st.add_checkbutton(label="اجرا با روشن شدن ویندوز", variable=self.v_auto, command=self.toggle_auto)
        st.add_checkbutton(label="اجازه‌ی بردن ماوس", variable=self.v_mouse, command=self.toggle_mouse)
        st.add_checkbutton(label="نشستن روی پنجره‌ها", variable=self.v_window, command=self.toggle_window)
        st.add_checkbutton(label="ثبت زمان استفاده از برنامه‌ها", variable=self.v_track, command=self.toggle_track)
        st.add_command(label="ساکت باش (۳۰ دقیقه)", command=self.mute)
        st.add_command(label="کلید API هوش مصنوعی (اختیاری)", command=self.set_api_key)
        m.add_cascade(label="⚙️ تنظیمات", menu=st)
        m.add_separator()
        m.add_command(label="👋 خداحافظ موجو", command=self.quit)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def quit(self):
        self.say("فعلاً! زود برمی‌گردم...", 1200)
        self.root.after(1300, self.root.destroy)

    def set_chaos(self):
        self.S["chaos"] = self.v_chaos.get()
        self.next_event = time.time() + 10
        self.save()

    def set_sound(self):
        self.S["sound"] = self.v_sound.get()
        self.snd.set_level(self.S["sound"])
        self.snd.play("ding", force=True)
        self.save()

    def show_likes(self):
        w = self.win("علاقه‌های من", 460, 500)
        S = self.S
        lb = tk.Listbox(w, font=F, height=14, activestyle="none", selectbackground="#99f6e4")
        lb.pack(fill="both", expand=True, padx=12, pady=(12, 6))
        rows = []
        kinds = {"game": "بازی", "app": "برنامه", "music": "موسیقی", "site": "سایت"}

        def refresh():
            lb.delete(0, "end")
            rows.clear()
            for k, v in S["facts"].items():
                rows.append(("f", k))
                lb.insert("end", f"{FACT_LABELS.get(k, k)}: {v}")
            for i, it in enumerate(S["library"]):
                rows.append(("l", i))
                lb.insert("end", f"[{kinds.get(it['kind'], '')}] {it['name']}")

        def delete():
            for idx in reversed(list(lb.curselection())):
                t, k = rows[idx]
                if t == "f":
                    S["facts"].pop(k, None)
                else:
                    S["library"].pop(k)
            self.save()
            refresh()

        self.B(w, "حذف مورد انتخابی", delete, bg="#dc2626").pack(pady=4)
        row = tk.Frame(w, bg=CREAM)
        row.pack(pady=6)
        for kind, name in [("game", "+ بازی"), ("app", "+ برنامه"), ("music", "+ موسیقی"), ("site", "+ سایت")]:
            self.B(row, name, lambda k=kind: (w.destroy(), self.run_ev(lambda: self.ev_showme(k)))).pack(side="left", padx=3)
        refresh()

    def toggle_auto(self):
        if self.v_auto.get() and winreg is None:
            self.v_auto.set(False)
            self.say("اجرای خودکار فقط توی ویندوز کار می‌کنه.")
            return
        set_autostart(self.v_auto.get())
        self.v_auto.set(autostart_enabled())
        self.say("از این به بعد با ویندوز میام!" if self.v_auto.get() else "باشه، دیگه خودکار نمیام.")

    def toggle_mouse(self):
        self.S["mouse_ok"] = self.v_mouse.get()
        self.save()

    def toggle_window(self):
        self.S["window_ok"] = self.v_window.get()
        self.save()

    def mute(self):
        self.S["mute_until"] = time.time() + 1800
        self.save()
        self.say("باشه، ۳۰ دقیقه ساکت می‌شم... قول!", 3000)

    def set_api_key(self):
        k = simpledialog.askstring("کلید API", "کلید Anthropic API (برای چت هوشمند):", show="*", parent=self.root)
        if k is not None:
            self.S["api_key"] = k.strip()
            self.save()
            self.say("ذخیره شد! حالا توی چت باهوش‌تر جواب می‌دم.")

    def add_reminder(self):
        s = simpledialog.askstring("یادآور", "چی رو یادآوری کنم؟", parent=self.root)
        if not s or not s.strip():
            return
        t = simpledialog.askstring("زمان", "چند دقیقه دیگه؟ (مثلاً 15)\nیا ساعت دقیق (مثلاً 14:30):", parent=self.root)
        if not t:
            return
        t = t.strip().translate(P2E)
        now = dt.datetime.now()
        at = None
        mt = re.match(r"^(\d{1,2})[:.](\d{2})$", t)
        if mt and int(mt.group(1)) < 24 and int(mt.group(2)) < 60:
            tgt = now.replace(hour=int(mt.group(1)), minute=int(mt.group(2)), second=0, microsecond=0)
            if tgt <= now:
                tgt += dt.timedelta(days=1)
            at = tgt.timestamp()
        else:
            try:
                at = time.time() + float(t) * 60
            except ValueError:
                pass
        if at is None:
            self.say("زمان رو نفهمیدم!")
            return
        self.S["reminders"].append({"at": at, "text": bmp(s.strip())[:60]})
        self.save()
        self.say("باشه، یادم می‌مونه!")

    def google(self):
        q = simpledialog.askstring("جستجو", "چی رو بگردم؟", parent=self.root)
        if q:
            webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(q))
            self.say("بفرما، توی مرورگر باز کردم.")

    def sys_info(self):
        parts = []
        if psutil:
            parts.append(f"پردازنده {fa(round(psutil.cpu_percent(interval=0.3)))}٪")
            parts.append(f"رم {fa(round(psutil.virtual_memory().percent))}٪")
            try:
                bt = psutil.sensors_battery()
                if bt:
                    parts.append(f"باتری {fa(round(bt.percent))}٪")
            except Exception:
                pass
        try:
            parts.append(f"فضای خالی {fa(round(shutil.disk_usage(os.path.abspath(os.sep)).free / 1024 ** 3))} گیگ")
        except Exception:
            pass
        if not psutil:
            parts.append("(برای CPU و RAM: pip install psutil)")
        self.say(" | ".join(parts), 8000)

    def win(self, title, w, h, game=False):
        win = tk.Toplevel(self.root)
        win.title("Mojo " + title)
        win.configure(bg=CREAM)
        win.attributes("-topmost", True)
        l, tp, r, b = self.area()
        x = self.x - w - 10
        if x < l + 10:
            x = min(r - w - 10, self.x + CW + 10)
        y = clamp(self.y, tp + 10, b - h - 40)
        win.geometry(f"{w}x{h}+{int(x)}+{int(y)}")
        win.resizable(False, False)
        if game:
            self.games.append(win)
        return win

    def open_chat(self):
        if self.chat_win and alive(self.chat_win):
            self.chat_win.lift()
            return
        w = self.chat_win = self.win("گپ", 400, 460)
        txt = tk.Text(w, font=F, wrap="word", state="disabled", bg="white", relief="flat", height=18)
        txt.tag_configure("me", justify="right", foreground="#1d4ed8", rmargin=8, spacing3=6)
        txt.tag_configure("bot", justify="right", foreground="#111827", rmargin=8, spacing3=6)
        txt.pack(fill="both", expand=True, padx=10, pady=(10, 6))
        ent = tk.Entry(w, font=F, justify="right")
        ent.pack(fill="x", padx=10, pady=4)
        ent.focus_set()

        def add(who, s):
            txt.config(state="normal")
            txt.insert("end", ("تو: " if who == "me" else "موجو: ") + bmp(s) + "\n", who)
            txt.config(state="disabled")
            txt.see("end")

        def send(_=None):
            s = ent.get().strip()
            if not s:
                return
            ent.delete(0, "end")
            add("me", s)

            def got(r):
                if alive(w):
                    add("bot", r)
                self.say(r, 7000)

            self.reply(s, got)

        ent.bind("<Return>", send)
        self.B(w, "ارسال", send).pack(pady=(2, 10))
        add("bot", "سلام! بپرس، جوک بخوای، چالش، یا بگو «بازی».")

    def reply(self, text, cb):
        r = self.local_reply(text)
        if r is not None:
            cb(r)
            return
        key = self.S.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
        if key:
            self.ask_claude(text, key, cb)
        else:
            cb(random.choice(["جالبه! بیشتر بگو.", "هوم... من فقط یه ژله‌ام، ولی گوش می‌دم.",
                              "نفهمیدم، ولی یه جوک بگم؟ " + random.choice(JOKES)]))

    def ask_claude(self, text, key, cb):
        self.chat_hist.append({"role": "user", "content": text})
        self.chat_hist = self.chat_hist[-8:]
        hist = list(self.chat_hist)
        system = ("تو «موجو» هستی؛ یه موجود ژله‌ای شیطون و بامزه که روی دسکتاپ ویندوز زندگی می‌کنه. "
                  "همیشه به فارسی، خیلی کوتاه (حداکثر دو جمله) و صمیمی جواب بده.")

        def work():
            try:
                body = json.dumps({"model": "claude-sonnet-5-5", "max_tokens": 300, "system": system,
                                   "messages": hist}).encode()
                req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                                             headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                                      "content-type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.load(r)
                out = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip() or "هوم؟"
                self.chat_hist.append({"role": "assistant", "content": out})
            except Exception as ex:
                out = f"اتصال به هوش مصنوعی نشد ({type(ex).__name__})."
                self.chat_hist.pop()
            self.q.put(lambda: cb(out))

        threading.Thread(target=work, daemon=True).start()

    def local_reply(self, text):
        s = text.strip().lower().translate(P2E)
        has = lambda *ks: any(k in s for k in ks)
        now = dt.datetime.now()
        n = self.S["user_name"]
        if has("سلام", "درود", "hello") or s in ("hi", "hey"):
            return f"سلام {n}!" if n else "سلام رفیق!"
        if has("خوبی", "چطوری", "حالت"):
            return "عالیم! ژله‌ام سفت و سرحاله. تو چطوری؟"
        if has("اسمت", "کی هستی", "تو کی"):
            return "من موجوام؛ یه موجود ژله‌ای که روی دسکتاپت زندگی می‌کنه!"
        if has("جوک"):
            return random.choice(JOKES)
        if has("نکته", "جالب"):
            return random.choice(FACTS)
        if has("چالش"):
            return "چالش امروز: " + self.today_challenge()[0]
        if has("بازی"):
            self.root.after(300, lambda: self.run_ev(self.ev_play))
            return "بزن بریم!"
        if has("نقاشی"):
            self.root.after(300, lambda: self.run_ev(self.ev_draw))
            return "یه تابلو میارم!"
        if has("مطالعه", "درس"):
            self.root.after(300, self.start_study)
            return "بریم مطالعه!"
        if has("ساعت"):
            return f"ساعت {fa(now.strftime('%H:%M'))} است."
        if has("تاریخ", "امروز"):
            return persian_date()
        if has("ممنون", "مرسی", "تشکر"):
            return "قابلی نداشت!"
        if has("خداحافظ", "بای"):
            return "بدرود! من همین دور و برم."
        return None

    def finish_game(self, won, xp, text):
        self.S["stats"]["games"] += 1
        if won:
            self.S["stats"]["wins"] += 1
        self.add_xp(xp)
        self.queue_react(text, "happy" if won else "sad", "cheer" if won else "idle", 80)

    def game_guess(self):
        win = self.win("حدس عدد", 340, 240, game=True)
        secret, tries = random.randint(1, 100), [0]
        self.L(win, "یه عدد بین ۱ تا ۱۰۰ حدس بزن!", 12).pack(pady=(18, 8))
        ent = tk.Entry(win, font=("Segoe UI", 14), justify="center", width=10)
        ent.pack()
        ent.focus_set()
        msg = self.L(win, "", 12)
        msg.pack(pady=10)

        def go(_=None):
            try:
                n = to_int(ent.get())
            except ValueError:
                return
            ent.delete(0, "end")
            tries[0] += 1
            if n < secret:
                msg.config(text=f"بزرگ‌تر ↑   (حدس {fa(tries[0])})")
            elif n > secret:
                msg.config(text=f"کوچیک‌تر ↓   (حدس {fa(tries[0])})")
            else:
                msg.config(text=f"آفرین! با {fa(tries[0])} حدس پیدا کردی ✓", fg="#16a34a")
                ent.config(state="disabled")
                btn.config(state="disabled")
                self.finish_game(True, max(5, 30 - tries[0] * 3), "عددو پیدا کردی! خوب بود.")
                self.record("guess_best", tries[0])

        btn = self.B(win, "حدس بزن", go)
        btn.pack(pady=4)
        ent.bind("<Return>", go)

    def game_rps(self):
        win = self.win("سنگ کاغذ قیچی", 380, 270, game=True)
        names = ["سنگ", "کاغذ", "قیچی"]
        sc = {"me": 0, "bot": 0}
        res = self.L(win, "انتخاب کن!", 14)
        res.pack(pady=(18, 6))
        board = self.L(win, "تو ۰ - ۰ من", 11, fg="#475569")
        board.pack()

        def play(i):
            b = random.randrange(3)
            if i == b:
                out = "مساوی شدیم!"
            elif (i - b) % 3 == 1:
                sc["me"] += 1
                out = "تو بردی!"
                self.record("rps_wins", 1)
                self.finish_game(True, 3, "اوه، این دور رو باختم!")
            else:
                sc["bot"] += 1
                out = "من بردم!"
                self.finish_game(False, 1, "یه دور دیگه؟ من تازه گرم شدم!")
            if alive(win):
                res.config(text=f"تو: {names[i]}   |   من: {names[b]}\n{out}")
                board.config(text=f"تو {fa(sc['me'])} - {fa(sc['bot'])} من")

        row = tk.Frame(win, bg=CREAM)
        row.pack(pady=18)
        for i, nm in enumerate(names):
            self.B(row, nm, lambda i=i: play(i)).pack(side="left", padx=6)

    def game_cake(self):
        g = getattr(self, "cake_game", None)
        if g and alive(g.win):
            g.win.lift()
            return
        self.cake_game = CakeGame(self)

    def game_math(self):
        win = self.win("ریاضی سریع", 340, 300, game=True)
        st = {"score": 0, "left": 30, "ans": 0, "on": True}
        head = self.L(win, "", 11, fg="#475569")
        head.pack(pady=(14, 4))
        q = self.L(win, "", 22)
        q.pack(pady=10)
        ent = tk.Entry(win, font=("Segoe UI", 16), justify="center", width=8)
        ent.pack()
        ent.focus_set()
        info = self.L(win, "", 11)
        info.pack(pady=8)

        def newq():
            op = random.choice("+-×")
            if op == "×":
                a, b = random.randint(2, 12), random.randint(2, 12)
                st["ans"] = a * b
            elif op == "+":
                a, b = random.randint(10, 99), random.randint(10, 99)
                st["ans"] = a + b
            else:
                a = random.randint(20, 99)
                b = random.randint(1, a)
                st["ans"] = a - b
            q.config(text=f"{a} {op} {b} = ?")

        def refresh():
            head.config(text=f"زمان: {fa(st['left'])} ثانیه   |   امتیاز: {fa(st['score'])}")

        def submit(_=None):
            if not st["on"]:
                return
            try:
                v = to_int(ent.get())
            except ValueError:
                return
            ent.delete(0, "end")
            if v == st["ans"]:
                st["score"] += 1
                info.config(text="درسته ✓", fg="#16a34a")
            else:
                info.config(text=f"غلط ✗ (جواب: {st['ans']})", fg="#dc2626")
            refresh()
            newq()

        def clock():
            if not alive(win) or not st["on"]:
                return
            st["left"] -= 1
            refresh()
            if st["left"] <= 0:
                st["on"] = False
                ent.config(state="disabled")
                sc = st["score"]
                q.config(text=f"نتیجه: {fa(sc)}")
                self.record("math_best", sc)
                self.finish_game(sc >= 8, sc * 2, f"ریاضی سریع تموم شد: {fa(sc)} تا درست!")
                return
            win.after(1000, clock)

        ent.bind("<Return>", submit)
        newq()
        refresh()
        win.after(1000, clock)

    def game_reaction(self):
        win = self.win("تست واکنش", 360, 280, game=True)
        box = tk.Label(win, text="آماده‌ای؟ کلیک کن تا شروع شه", bg=TEAL, fg="white", font=("Segoe UI", 14, "bold"),
                       width=24, height=8, cursor="hand2", wraplength=280)
        box.pack(padx=14, pady=14, fill="both", expand=True)
        st = {"phase": "idle", "t0": 0.0, "job": None}

        def go():
            if alive(win):
                box.config(text="الان کلیک کن!", bg="#16a34a")
                st["t0"] = time.time()
                st["phase"] = "go"

        def click(_=None):
            if st["phase"] == "idle":
                box.config(text="صبر کن تا سبز شه...", bg="#dc2626")
                st["phase"] = "wait"
                st["job"] = win.after(random.randint(1500, 4000), go)
            elif st["phase"] == "wait":
                win.after_cancel(st["job"])
                box.config(text="زود زدی! دوباره کلیک کن", bg=TEAL)
                st["phase"] = "idle"
            elif st["phase"] == "go":
                ms = int((time.time() - st["t0"]) * 1000)
                box.config(text=f"{fa(ms)} میلی‌ثانیه\nکلیک کن برای دور بعد", bg=TEAL)
                st["phase"] = "idle"
                self.record("reaction_best", ms)
                self.finish_game(ms < 400, 10 if ms < 250 else 5 if ms < 400 else 2, f"واکنشت {fa(ms)} میلی‌ثانیه بود!")

        box.bind("<Button-1>", click)

    def game_ttt(self):
        win = self.win("دوز", 300, 360, game=True)
        bd, btns, over = [""] * 9, [], [False]
        status = self.L(win, "تو X هستی. نوبت توئه!", 12)
        status.pack(pady=10)
        grid = tk.Frame(win, bg=CREAM)
        grid.pack()

        def end(r):
            over[0] = True
            if r == "X":
                status.config(text="بردی! آفرین ✓", fg="#16a34a")
                self.record("ttt_wins", 1)
                self.finish_game(True, 15, "دوز رو بردی! باهوشی.")
            elif r == "O":
                status.config(text="این دور رو من بردم!", fg="#dc2626")
                self.finish_game(False, 2, "من بردم! دور بعد رو ببر.")
            else:
                status.config(text="مساوی شد.")
                self.finish_game(False, 4, "مساوی شدیم؛ خوب بازی کردی.")

        def click(i):
            if over[0] or bd[i]:
                return
            bd[i] = "X"
            btns[i].config(text="X", fg="#2563eb")
            r = ttt_winner(bd)
            if r:
                return end(r)
            j = ttt_bot(bd)
            bd[j] = "O"
            btns[j].config(text="O", fg="#dc2626")
            r = ttt_winner(bd)
            if r:
                end(r)

        for i in range(9):
            b = tk.Button(grid, text="", font=("Segoe UI", 24, "bold"), width=3, height=1, bg="white", relief="flat",
                          command=lambda i=i: click(i))
            b.grid(row=i // 3, column=i % 3, padx=3, pady=3)
            btns.append(b)

        def again():
            win.destroy()
            self.game_ttt()

        self.B(win, "دوباره", again).pack(pady=12)


_lock = None


def single_instance():
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 47654))
    except OSError:
        return None
    s.listen(1)
    return s


if __name__ == "__main__":
    _lock = single_instance()
    if _lock is None:
        sys.exit(0)
    Mojo().root.mainloop()