from picamera2 import Picamera2, Preview
from datetime import datetime
import os
import cv2
import tkinter as tk
from tkinter import messagebox
from time import sleep

SAVE_DIR = "captures"
os.makedirs(SAVE_DIR, exist_ok=True)

cam0 = None
cam1 = None
usb_cam = None

cam0_running = False
cam1_running = False
usb_running = False


def save_path(camera_name):
    folder = os.path.join(SAVE_DIR, camera_name)
    os.makedirs(folder, exist_ok=True)

    filename = datetime.now().strftime(f"{camera_name}_%Y%m%d_%H%M%S.jpg")
    return os.path.join(folder, filename)


def set_status(text):
    status_label.config(text=text)
    root.update_idletasks()


# =====================
# CAM0 - IMX519
# =====================
def start_cam0():
    global cam0, cam0_running

    if cam0_running:
        return

    try:
        cam0 = Picamera2(0)
        config = cam0.create_preview_configuration(
            main={"size": (1280, 720)}
        )
        cam0.configure(config)
        cam0.start_preview(Preview.QT)
        cam0.start()
        sleep(1)

        cam0.set_controls({
            "AfMode": 2,
            "AfTrigger": 0
        })

        cam0_running = True
        set_status("CAM0 Ready")

    except Exception as e:
        messagebox.showerror("CAM0 Error", str(e))

def capture_cam0():
    if not cam0_running:
        messagebox.showwarning("Warning", "Start CAM0 first")
        return

    try:
        filepath = save_path("cam0_bag")

        cam0.set_controls({
            "AfMode": 1,
            "AfTrigger": 0
        })
        sleep(3)

        cam0.switch_mode_and_capture_file(
            cam0.create_still_configuration(
                main={"size": (1920, 1080)}
            ),
            filepath
        )

        set_status(f"Saved CAM0: {filepath}")
        print("Saved:", filepath)

    except Exception as e:
        messagebox.showerror("CAM0 Capture Error", str(e))


def stop_cam0():
    global cam0, cam0_running

    if cam0_running and cam0 is not None:
        cam0.stop_preview()
        cam0.stop()
        cam0.close()

    cam0 = None
    cam0_running = False
    set_status("CAM0 Stopped")


# =====================
# CAM1 - IMX519
# =====================
def start_cam1():
    global cam1, cam1_running

    if cam1_running:
        return

    try:
        cam1 = Picamera2(1)
        config = cam1.create_preview_configuration(
            main={"size": (1280, 720)}
        )
        cam1.configure(config)
        cam1.start_preview(Preview.QT)
        cam1.start()
        sleep(1)

        cam1.set_controls({
            "AfMode": 2,
            "AfTrigger": 0
        })

        cam1_running = True
        set_status("CAM1 Ready")

    except Exception as e:
        messagebox.showerror("CAM1 Error", str(e))


def capture_cam1():
    if not cam1_running:
        messagebox.showwarning("Warning", "Start CAM1 first")
        return

    try:
        filepath = save_path("cam1_box")

        cam1.set_controls({
            "AfMode": 1,
            "AfTrigger": 0
        })
        sleep(3)

        cam1.switch_mode_and_capture_file(
            cam1.create_still_configuration(
                main={"size": (1920, 1080)}
            ),
            filepath
        )

        set_status(f"Saved CAM1: {filepath}")
        print("Saved:", filepath)

    except Exception as e:
        messagebox.showerror("CAM1 Capture Error", str(e))

def stop_cam1():
    global cam1, cam1_running

    if cam1_running and cam1 is not None:
        cam1.stop_preview()
        cam1.stop()
        cam1.close()

    cam1 = None
    cam1_running = False
    set_status("CAM1 Stopped")


# =====================
# USB CAMERA
# =====================
def start_usb():
    global usb_cam, usb_running

    if usb_running:
        return

    try:
        usb_cam = cv2.VideoCapture(16)

        if not usb_cam.isOpened():
            raise Exception("Cannot open USB camera /dev/video0")

        usb_running = True
        set_status("USB Camera Ready")

    except Exception as e:
        messagebox.showerror("USB Camera Error", str(e))


def capture_usb():
    if not usb_running or usb_cam is None:
        messagebox.showwarning("Warning", "Start USB camera first")
        return

    try:
        ret, frame = usb_cam.read()

        if not ret:
            raise Exception("Cannot read frame from USB camera")

        filepath = save_path("usb_carton")
        cv2.imwrite(filepath, frame)

        set_status(f"Saved USB: {filepath}")
        print("Saved:", filepath)

    except Exception as e:
        messagebox.showerror("USB Capture Error", str(e))


def stop_usb():
    global usb_cam, usb_running

    if usb_cam is not None:
        usb_cam.release()

    usb_cam = None
    usb_running = False
    set_status("USB Camera Stopped")


def stop_all():
    try:
        stop_cam0()
    except:
        pass

    try:
        stop_cam1()
    except:
        pass

    try:
        stop_usb()
    except:
        pass


def on_close():
    stop_all()
    root.destroy()

# =====================
# GUI
# =====================
root = tk.Tk()
root.title("Multi Camera Data Collection")
root.geometry("500x520")

title = tk.Label(root, text="Multi Camera Data Collection", font=("Arial", 18, "bold"))
title.pack(pady=15)

status_label = tk.Label(root, text="Status: Idle", font=("Arial", 12))
status_label.pack(pady=10)

tk.Label(root, text="CAM0 - Bag", font=("Arial", 14, "bold")).pack(pady=5)
tk.Button(root, text="Start CAM0", width=25, command=start_cam0).pack(pady=3)
tk.Button(root, text="Capture CAM0", width=25, command=capture_cam0).pack(pady=3)
tk.Button(root, text="Stop CAM0", width=25, command=stop_cam0).pack(pady=3)

tk.Label(root, text="CAM1 - Box", font=("Arial", 14, "bold")).pack(pady=5)
tk.Button(root, text="Start CAM1", width=25, command=start_cam1).pack(pady=3)
tk.Button(root, text="Capture CAM1", width=25, command=capture_cam1).pack(pady=3)
tk.Button(root, text="Stop CAM1", width=25, command=stop_cam1).pack(pady=3)

tk.Label(root, text="USB - Carton", font=("Arial", 14, "bold")).pack(pady=5)
tk.Button(root, text="Start USB", width=25, command=start_usb).pack(pady=3)
tk.Button(root, text="Capture USB", width=25, command=capture_usb).pack(pady=3)
tk.Button(root, text="Stop USB", width=25, command=stop_usb).pack(pady=3)

tk.Button(root, text="Stop All", width=25, bg="red", fg="white", command=stop_all).pack(pady=15)

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()