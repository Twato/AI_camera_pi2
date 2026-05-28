from datetime import datetime
import os
import cv2
import tkinter as tk
from PIL import Image, ImageTk

# =====================
# CONFIG
# =====================
SAVE_DIR = "usb_captures"
os.makedirs(SAVE_DIR, exist_ok=True)

USB_DEVICE = 0

CAM_WIDTH = 1280
CAM_HEIGHT = 720
CAM_FPS = 30

running = True
cap = None
latest_frame = None


# =====================
# STATUS
# =====================
def set_status(text):
    status_label.config(text=text)
    root.update_idletasks()
    print(text)


# =====================
# OPEN CAMERA
# =====================
def open_camera():
    global cap

    cap = cv2.VideoCapture(
        f"/dev/video{USB_DEVICE}",
        cv2.CAP_V4L2
    )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAM_FPS)

    if not cap.isOpened():
        set_status("Cannot open USB camera")
        return False

    set_status("Camera Ready")
    return True

# =====================
# RESIZE IMAGE TO FIT UI
# =====================
def resize_to_fit(frame, max_width, max_height):
    h, w = frame.shape[:2]

    scale = min(max_width / w, max_height / h)

    new_w = int(w * scale)
    new_h = int(h * scale)

    return cv2.resize(frame, (new_w, new_h))


# =====================
# UPDATE PREVIEW
# =====================
def update_camera():
    global latest_frame

    if not running or cap is None:
        return

    ret, frame = cap.read()

    if ret:
        latest_frame = frame.copy()

        preview_w = int(root.winfo_width() * 0.9)
        preview_h = int(root.winfo_height() * 0.55)

        if preview_w > 10 and preview_h > 10:
            display = resize_to_fit(
                frame,
                preview_w,
                preview_h
            )

            display = cv2.cvtColor(
                display,
                cv2.COLOR_BGR2RGB
            )

            img = Image.fromarray(display)
            imgtk = ImageTk.PhotoImage(image=img)

            preview_label.imgtk = imgtk
            preview_label.config(image=imgtk)

    root.after(30, update_camera)

# =====================
# POPUP
# =====================
def show_popup(text, bg="#1f8f3a"):

    popup_label.config(
        text=f"[ OK ] {text}",
        bg=bg
    )

    popup_label.place(
        relx=0.5,
        rely=0.78,
        anchor="center"
    )

    root.after(
        3000,
        lambda: popup_label.place_forget()
    )

# =====================
# CAPTURE IMAGE
# =====================
def capture_image():
    global latest_frame

    if latest_frame is None:
        set_status("No frame to capture")
        return

    filename = datetime.now().strftime(
        "usb_%Y%m%d_%H%M%S.jpg"
    )

    filepath = os.path.join(
        SAVE_DIR,
        filename
    )

    cv2.imwrite(
        filepath,
        latest_frame,
        [cv2.IMWRITE_JPEG_QUALITY, 100]
    )

    set_status("Upload Completed")

    show_popup("UPLOAD COMPLETED")

    root.after(
        3000,
        lambda: set_status("Camera Ready")
    )
    # =====================
# CLOSE APP
# =====================
def on_close():
    global running, cap

    running = False

    if cap is not None:
        cap.release()
        cap = None

    root.destroy()


# =====================
# GUI
# =====================
root = tk.Tk()
root.title("USB Camera Manual Capture")

# fullscreen ����СѺ HMI
# ��������ҡ fullscreen ��� comment ��÷Ѵ���
root.attributes("-fullscreen", True)

root.configure(bg="#e6e6e6")

# ESC �͡�ҡ fullscreen
root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))

# layout responsive
root.grid_rowconfigure(0, weight=0)
root.grid_rowconfigure(1, weight=1)
root.grid_rowconfigure(2, weight=0)
root.grid_rowconfigure(3, weight=0)
root.grid_columnconfigure(0, weight=1)

title_label = tk.Label(
    root,
    text="USB Camera Manual Capture",
    font=("Arial", 20, "bold"),
    bg="#e6e6e6"
)
title_label.grid(
    row=0,
    column=0,
    pady=15,
    sticky="n"
)

preview_frame = tk.Frame(
    root,
    bg="black"
)
preview_frame.grid(
    row=1,
    column=0,
    padx=10,
    pady=5,
    sticky="nsew"
)

preview_label = tk.Label(
    preview_frame,
    bg="black"
)
preview_label.place(
    relx=0.5,
    rely=0.5,
    anchor="center"
)

status_label = tk.Label(
    root,
    text="Opening Camera...",
    font=("Arial", 18),
    bg="#e6e6e6"
)
status_label.grid(
    row=2,
    column=0,
    pady=10
)
popup_label = tk.Label(
    root,
    text="",
    font=("Arial", 24, "bold"),
    bg="#1f8f3a",
    fg="white",
    padx=28,
    pady=12,
    relief="flat"
)

popup_label.place_forget()

btn_capture = tk.Button(
    root,
    text="CAPTURE",
    font=("Arial", 22, "bold"),
    bg="#00aa00",
    fg="white",
    activebackground="#008800",
    activeforeground="white",
    height=2,
    command=capture_image
)
btn_capture.grid(
    row=3,
    column=0,
    padx=40,
    pady=25,
    sticky="ew"
)

root.protocol("WM_DELETE_WINDOW", on_close)

# =====================
# START AUTO
# =====================
if open_camera():
    update_camera()

root.mainloop()