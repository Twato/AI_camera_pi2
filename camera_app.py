from picamera2 import Picamera2, Preview
from time import sleep, time
from datetime import datetime
import os
import tkinter as tk
from tkinter import messagebox
import threading
import cv2
import numpy as np

# =====================
# CONFIG
# =====================
SAVE_DIR = "captures"
os.makedirs(SAVE_DIR, exist_ok=True)

PREVIEW_SIZE = (1280, 720)
CAPTURE_SIZE = (1920, 1080)

MOTION_THRESHOLD = 120000
STABLE_THRESHOLD = 70000

FOCUS_DELAY = 5
POST_CAPTURE_DELAY = 5
STABLE_TIME = 2

picam2 = None
camera_running = False
auto_running = False
last_capture_time = 0


def set_status(text):
    status_label.config(text=text)
    root.update_idletasks()


def get_gray_frame():
    frame = picam2.capture_array()
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    return gray


def start_camera():
    global picam2, camera_running

    if camera_running:
        return

    try:
        picam2 = Picamera2()

        config = picam2.create_preview_configuration(
            main={"size": PREVIEW_SIZE}
        )
        picam2.configure(config)

        picam2.start_preview(Preview.QT)
        picam2.start()

        sleep(1)

        picam2.set_controls({
            "AfMode": 2,
            "AfTrigger": 0
        })

        camera_running = True
        set_status("Status: Camera Ready")

    except Exception as e:
        messagebox.showerror("Camera Error", str(e))


def autofocus_once():
    try:
        picam2.set_controls({
            "AfMode": 1,
            "AfTrigger": 0
        })

        sleep(FOCUS_DELAY)

        picam2.set_controls({
            "AfMode": 2,
            "AfTrigger": 0
        })

    except Exception as e:
        print("Autofocus Error:", e)


def capture_image(auto=False):
    global last_capture_time

    if not camera_running or picam2 is None:
        messagebox.showwarning("Warning", "Please start camera first")
        return None

    try:
        filename = datetime.now().strftime("capture_%Y%m%d_%H%M%S.jpg")
        filepath = os.path.join(SAVE_DIR, filename)

        set_status("Status: Auto Focusing...")
        autofocus_once()

        set_status("Status: Capturing...")

        picam2.switch_mode_and_capture_file(
            picam2.create_still_configuration(
                main={"size": CAPTURE_SIZE}
            ),
            filepath
        )

        last_capture_time = time()
        set_status(f"Captured: {filename}")

        if not auto:
            messagebox.showinfo("Success", f"Saved image:\n{filepath}")

        print("Saved:", filepath)
        return filepath

    except Exception as e:
        if not auto:
            messagebox.showerror("Capture Error", str(e))
        print("Capture Error:", e)
        return None


def wait_until_stable():
    stable_start = None
    prev_gray = None

    while auto_running and camera_running:
        try:
            gray = get_gray_frame()

            if prev_gray is None:
                prev_gray = gray
                sleep(0.2)
                continue

            diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            score = np.sum(thresh)

            if score < STABLE_THRESHOLD:
                if stable_start is None:
                    stable_start = time()

                if time() - stable_start >= STABLE_TIME:
                    return gray
            else:
                stable_start = None

            prev_gray = gray
            sleep(0.2)

        except Exception as e:
            print("Wait Stable Error:", e)
            sleep(0.5)

    return None


def start_auto_capture():
    global auto_running

    if not camera_running:
        messagebox.showwarning("Warning", "Please start camera first")
        return

    if auto_running:
        return

    auto_running = True
    set_status("Status: Auto Capture Running")

    thread = threading.Thread(target=auto_capture_loop, daemon=True)
    thread.start()


def stop_auto_capture():
    global auto_running
    auto_running = False
    set_status("Status: Auto Capture Stopped")


def auto_capture_loop():
    global auto_running

    set_status("Status: Reset Background...")
    prev_gray = wait_until_stable()

    if prev_gray is None:
        prev_gray = get_gray_frame()

    set_status("Status: Ready")

    while auto_running and camera_running:
        try:
            gray = get_gray_frame()

            diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            motion_score = np.sum(thresh)

            if motion_score > MOTION_THRESHOLD:
                set_status("Status: Object Detected / Hold")
                sleep(0.8)

                capture_image(auto=True)

                set_status("Status: Remove Object...")
                sleep(POST_CAPTURE_DELAY)

                set_status("Status: Waiting Stable...")
                new_background = wait_until_stable()

                if new_background is not None:
                    prev_gray = new_background
                else:
                    prev_gray = get_gray_frame()

                set_status("Status: Ready")
                sleep(0.5)

            else:
                prev_gray = gray

            sleep(0.1)

        except Exception as e:
            print("Auto Capture Error:", e)
            sleep(0.5)


def stop_camera():
    global picam2, camera_running, auto_running

    auto_running = False

    if camera_running and picam2 is not None:
        try:
            picam2.stop_preview()
            picam2.stop()
            picam2.close()
        except Exception as e:
            messagebox.showerror("Stop Error", str(e))
        finally:
            picam2 = None
            camera_running = False
            set_status("Status: Camera Stopped")


def on_close():
    stop_camera()
    root.destroy()


# =====================
# GUI
# =====================
root = tk.Tk()
root.title("AI Camera Test App")
root.geometry("430x360")

title = tk.Label(root, text="AI Camera Test App", font=("Arial", 18, "bold"))
title.pack(pady=15)

status_label = tk.Label(root, text="Status: Idle", font=("Arial", 12))
status_label.pack(pady=10)

btn_start = tk.Button(root, text="Start Camera", font=("Arial", 14), width=22, command=start_camera)
btn_start.pack(pady=5)

btn_capture = tk.Button(root, text="Capture", font=("Arial", 14), width=22, command=capture_image)
btn_capture.pack(pady=5)

btn_auto_start = tk.Button(root, text="Start Auto Capture", font=("Arial", 14), width=22, command=start_auto_capture)
btn_auto_start.pack(pady=5)

btn_auto_stop = tk.Button(root, text="Stop Auto Capture", font=("Arial", 14), width=22, command=stop_auto_capture)
btn_auto_stop.pack(pady=5)

btn_stop = tk.Button(root, text="Stop Camera", font=("Arial", 14), width=22, command=stop_camera)
btn_stop.pack(pady=5)

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()