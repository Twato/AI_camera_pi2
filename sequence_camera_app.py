from picamera2 import Picamera2, Preview
from time import sleep, time
from datetime import datetime
from PIL import Image, ImageTk
import os
import threading
import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox



SAVE_DIR = "captures"
os.makedirs(SAVE_DIR, exist_ok=True)

PREVIEW_SIZE = (320, 240)
CAPTURE_SIZE = (1280, 720)
PREVIEW_INTERVAL = 0.5  # 0.2 = ����ҳ 5 FPS
MOTION_THRESHOLD = 50000
STABLE_THRESHOLD = 70000

FOCUS_DELAY = 7
REMOVE_DELAY = 5
STABLE_TIME = 2
last_preview_time = 0
running = False
current_camera = None

target_count = 0
current_count = 0
SHOW_PREVIEW = True

running = False
current_camera = None


def set_status(text):
    status_label.config(text=text)
    root.update_idletasks()
    print(text)


def make_folder(name):
    folder = os.path.join(SAVE_DIR, name)
    os.makedirs(folder, exist_ok=True)
    return folder


def filename(camera_name):
    folder = make_folder(camera_name)
    name = datetime.now().strftime(f"{camera_name}_%Y%m%d_%H%M%S.jpg")
    return os.path.join(folder, name)


def gray_from_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    return gray


def motion_score(bg, current):
    diff = cv2.absdiff(bg, current)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    return np.sum(thresh)

def update_preview(frame, is_bgr=False):
    global last_preview_time

    now = time()
    if now - last_preview_time < PREVIEW_INTERVAL:
        return

    last_preview_time = now

    try:
        frame = cv2.resize(frame, (480, 270))

        if is_bgr:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)

        preview_label.imgtk = imgtk
        preview_label.config(image=imgtk)

    except Exception as e:
        print("Preview Error:", e)


def wait_stable_picam(cam):
    stable_start = None
    prev = None

    while running:
        frame = cam.capture_array()

        # ?? ���� preview �͹��Ŵ background
        update_preview(frame, is_bgr=False)

        gray = gray_from_frame(frame)

        if prev is None:
            prev = gray
            sleep(0.2)
            continue

        score = motion_score(prev, gray)

        # DEBUG �٤�� motion
        print("STABLE SCORE:", score)

        if score < STABLE_THRESHOLD:
            if stable_start is None:
                stable_start = time()

            if time() - stable_start >= STABLE_TIME:
                return gray

        else:
            stable_start = None

        prev = gray
        sleep(0.2)

    return None


def run_picamera(camera_index, camera_name):
    global current_camera

    cam = None

    try:
        set_status(f"{camera_name}: Opening Camera")

        cam = Picamera2(camera_index)
        current_camera = cam

        config = cam.create_preview_configuration(
            main={"size": PREVIEW_SIZE}
        )
        cam.configure(config)

        # ����� Preview.QT ���� ������Ҩ��ʴ�� UI �ͧ
        cam.start()
        sleep(1)

        cam.set_controls({
            "AfMode": 2,
            "AfTrigger": 0
        })

        set_status(f"{camera_name}: Loading Background")

        bg = wait_stable_picam(cam)

        if bg is None:
            return

        set_status(f"{camera_name}: Ready / Waiting Object")

        while running:
            frame = cam.capture_array()

            update_preview(frame, is_bgr=False)

            gray = gray_from_frame(frame)
            score = motion_score(bg, gray)

            if score > MOTION_THRESHOLD:
                set_status(f"{camera_name}: Object Detected")
                sleep(0.8)

                set_status(f"{camera_name}: Auto Focus {FOCUS_DELAY} sec")
                focus_with_preview_picam(cam)

                sleep(FOCUS_DELAY)

                filepath = filename(camera_name)

                set_status(f"{camera_name}: Capturing")

                cam.switch_mode_and_capture_file(
                    cam.create_still_configuration(
                        main={"size": CAPTURE_SIZE}
                    ),
                    filepath
                )

                print("Saved:", filepath)
                set_status(f"{camera_name}: Saved Image")

                set_status(f"{camera_name}: Remove Object {REMOVE_DELAY} sec")
                sleep(REMOVE_DELAY)

                break

            sleep(0.5)

    except Exception as e:
        print(f"{camera_name} Error:", e)
        set_status(f"{camera_name}: Error")

    finally:
        try:
            if cam is not None:
                cam.stop()
                cam.close()
        except Exception as e:
            print("Close camera error:", e)

        current_camera = None
        set_status(f"{camera_name}: Closed")
        sleep(2)


def wait_stable_usb(cap):
    stable_start = None
    prev = None

    while running:
        ret, frame = cap.read()

        if not ret:
            sleep(0.2)
            continue

        update_preview(frame, is_bgr=True)

        gray = gray_from_frame(frame)

        if prev is None:
            prev = gray
            sleep(0.2)
            continue

        score = motion_score(prev, gray)
        print("USB STABLE SCORE:", score)

        if score < STABLE_THRESHOLD:
            if stable_start is None:
                stable_start = time()

            if time() - stable_start >= STABLE_TIME:
                set_status("USB Background Ready")
                return gray
        else:
            stable_start = None

        prev = gray
        sleep(0.2)

    return None

def run_usb_camera(device_index, camera_name):
    cap = None

    try:
        set_status(f"{camera_name}: Opening USB Camera")

        cap = cv2.VideoCapture(
            f"/dev/video{device_index}",
            cv2.CAP_V4L2
        )

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        if not cap.isOpened():
            set_status(f"{camera_name}: Cannot Open USB Camera")
            return

        sleep(1)

        # =====================
        # USB WARM UP
        # =====================
        set_status(f"{camera_name}: USB Warm Up...")

        for _ in range(30):
            ret, frame = cap.read()

            if ret:
                update_preview(frame, is_bgr=True)

            sleep(0.1)

        # =====================
        # LOAD BACKGROUND
        # =====================
        set_status(f"{camera_name}: Loading Background")

        bg = wait_stable_usb(cap)

        if bg is None:
            set_status(f"{camera_name}: Cannot Load Background")
            return

        set_status(f"{camera_name}: Ready / Waiting Object")

        # =====================
        # DETECT LOOP
        # =====================
        while running:
            ret, frame = cap.read()

            if not ret:
                set_status(f"{camera_name}: Cannot Read Frame")
                sleep(0.5)
                continue

            update_preview(frame, is_bgr=True)

            gray = gray_from_frame(frame)
            score = motion_score(bg, gray)

            print(f"{camera_name} MOTION SCORE:", score)

            if score > MOTION_THRESHOLD:
                set_status(f"{camera_name}: Object Detected")
                sleep(0.8)

                set_status(f"{camera_name}: Hold {FOCUS_DELAY} sec")
                hold_with_preview_usb(cap)

                ret, frame = cap.read()

                if ret:
                    update_preview(frame, is_bgr=True)

                    filepath = filename(camera_name)

                    cv2.imwrite(filepath, frame)

                    print("Saved:", filepath)
                    set_status(f"{camera_name}: Saved Image")

                set_status(
                    f"{camera_name}: Remove Object {REMOVE_DELAY} sec"
                )

                sleep(REMOVE_DELAY)

                break

            sleep(0.3)

    except Exception as e:
        print(f"{camera_name} Error:", e)
        set_status(f"{camera_name}: Error")

    finally:
        if cap is not None:
            cap.release()

        set_status(f"{camera_name}: Closed")
        sleep(2)


def sequence_loop():
    global running, current_count

    while running and current_count < target_count:
        run_picamera(0, "cam0_bag")

        if not running:
            break

        run_picamera(1, "cam1_box")

        if not running:
            break

        run_usb_camera(16, "usb_carton")

        if not running:
            break

        current_count += 1

        progress_label.config(
            text=f"Progress: {current_count} / {target_count}"
        )

        if current_count >= target_count:
            running = False
            set_status("Status: Finish Job")
            root.after(1500, show_page1)
            break

    set_status("Status: Sequence Stopped")

def start_sequence():
    global running

    if running:
        return

    running = True
    set_status("Status: Sequence Started")

    thread = threading.Thread(target=sequence_loop, daemon=True)
    thread.start()

def stop_sequence():
    global running, current_camera

    running = False

    try:
        if current_camera is not None:
            if SHOW_PREVIEW:
                current_camera.stop_preview()
            current_camera.stop()
            current_camera.close()
    except:
        pass

    set_status("Status: Stop Requested")

def focus_with_preview_picam(cam):
    set_status(f"Auto Focus {FOCUS_DELAY} sec")

    cam.set_controls({
        "AfMode": 1,
        "AfTrigger": 0
    })

    start_time = time()

    while running and time() - start_time < FOCUS_DELAY:
        frame = cam.capture_array()
        update_preview(frame, is_bgr=False)
        sleep(0.1)

    cam.set_controls({
        "AfMode": 2,
        "AfTrigger": 0
    })
def hold_with_preview_usb(cap):
    set_status(f"USB Hold {FOCUS_DELAY} sec")

    start_time = time()

    while running and time() - start_time < FOCUS_DELAY:
        ret, frame = cap.read()
        if ret:
            update_preview(frame, is_bgr=True)
        sleep(0.1)


def on_close():
    stop_sequence()
    root.destroy()




# =====================
# PAGE CONTROL
# =====================
def show_page1():
    global running

    running = False

    page2.pack_forget()
    page1.pack(fill="both", expand=True)

    count_entry.delete(0, tk.END)
    count_entry.focus()

    set_page1_status("Please input quantity 1 - 100")


def show_page2():
    page1.pack_forget()
    page2.pack(fill="both", expand=True)


def set_page1_status(text):
    page1_status.config(text=text)


def start_from_input(event=None):
    global target_count, current_count, running

    value = count_entry.get().strip()

    if not value.isdigit():
        messagebox.showwarning("Warning", "Please input number only")
        return

    count = int(value)

    if count < 1 or count > 100:
        messagebox.showwarning("Warning", "Please input number 1 - 100")
        return

    target_count = count
    current_count = 0
    running = True

    show_page2()

    progress_label.config(text=f"Progress: 0 / {target_count}")
    set_status("Status: Sequence Started")

    thread = threading.Thread(target=sequence_loop, daemon=True)
    thread.start()


def stop_sequence():
    global running, current_camera

    running = False

    try:
        if current_camera is not None:
            current_camera.stop()
            current_camera.close()
    except:
        pass

    set_status("Status: Stop Requested")
    root.after(1000, show_page1)


def on_close():
    stop_sequence()
    root.destroy()


# =====================
# GUI
# =====================
root = tk.Tk()
root.title("Sequential Camera Data Collection")
root.geometry("760x520")
root.resizable(False, False)

# =====================
# PAGE 1: INPUT COUNT
# =====================
page1 = tk.Frame(root)

title1 = tk.Label(
    page1,
    text="AI Camera Data Collection",
    font=("Arial", 20, "bold")
)
title1.pack(pady=40)

sub1 = tk.Label(
    page1,
    text="Input Quantity",
    font=("Arial", 16)
)
sub1.pack(pady=10)

count_entry = tk.Entry(
    page1,
    font=("Arial", 28),
    justify="center",
    width=8
)
count_entry.pack(pady=10)

hint1 = tk.Label(
    page1,
    text="Input number 1 - 100 and press Enter",
    font=("Arial", 12),
    fg="gray"
)
hint1.pack(pady=10)

page1_status = tk.Label(
    page1,
    text="Please input quantity 1 - 100",
    font=("Arial", 12)
)
page1_status.pack(pady=10)

count_entry.bind("<Return>", start_from_input)

# =====================
# PAGE 2: CAMERA PREVIEW
# =====================
page2 = tk.Frame(root)

title2 = tk.Label(
    page2,
    text="Sequential Camera Data Collection",
    font=("Arial", 16, "bold")
)
title2.pack(pady=5)

preview_frame = tk.Frame(
    page2,
    bg="black",
    width=640,
    height=300
)
preview_frame.pack(pady=5)
preview_frame.pack_propagate(False)

preview_label = tk.Label(preview_frame, bg="black")
preview_label.pack(fill="both", expand=True)

status_label = tk.Label(
    page2,
    text="Status: Idle",
    font=("Arial", 12)
)
status_label.pack(pady=5)

progress_label = tk.Label(
    page2,
    text="Progress: 0 / 0",
    font=("Arial", 12, "bold")
)
progress_label.pack(pady=5)

button_frame = tk.Frame(page2)
button_frame.pack(pady=5)

btn_stop = tk.Button(
    button_frame,
    text="Stop",
    font=("Arial", 14),
    width=18,
    command=stop_sequence
)
btn_stop.pack(side="left", padx=10)

root.protocol("WM_DELETE_WINDOW", on_close)

page1.pack(fill="both", expand=True)
count_entry.focus()

root.mainloop()