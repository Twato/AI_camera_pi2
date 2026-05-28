# -*- coding: utf-8 -*-

import cv2
import easyocr
import os
import numpy as np

image_path = "/home/toto/rpicam_apps_1.9.0-2_arm64/usb_captures/usb_20260522_141847.jpg"

# OCR_MODE = "number"
# OCR_MODE = "text"
# OCR_MODE = "text_no_rotate"
OCR_MODE = "text_sharp"

if not os.path.exists(image_path):
    print("Image not found")
    exit()

image = cv2.imread(image_path)

if image is None:
    print("Cannot load image")
    exit()
 
clone = image.copy()

# =====================
# RESIZE PREVIEW FOR ROI
# =====================
max_width = 1200

img_h, img_w = image.shape[:2]
scale = 2.0

if img_w > max_width:
    scale = max_width / img_w

preview = cv2.resize(
    image,
    None,
    fx=scale,
    fy=scale,
    interpolation=cv2.INTER_AREA
)

print("Select ROI then press ENTER")
print("Press C to cancel")

roi = cv2.selectROI(
    "Select OCR Area",
    preview,
    showCrosshair=True,
    fromCenter=False
)

cv2.destroyAllWindows()

x, y, w, h = roi

if w == 0 or h == 0:
    print("No ROI selected")
    exit()

# �ŧ���˹� ROI ��Ѻ��ѧ�ٻ��ԧ
x = int(x / scale)
y = int(y / scale)
w = int(w / scale)
h = int(h / scale)

crop = clone[y:y+h, x:x+w]

def preprocess_number(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    gray = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))

    gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    gray = cv2.dilate(gray, kernel, iterations=1)

    gray = cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE)

    return gray


def preprocess_text(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(
        gray,
        None,
        fx=4,
        fy=4,
        interpolation=cv2.INTER_CUBIC
    )

    gray = cv2.rotate(
        gray,
        cv2.ROTATE_90_COUNTERCLOCKWISE
    )

    return gray

def preprocess_text_no_rotate(crop):

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(
        gray,
        None,
        fx=4,
        fy=4,
        interpolation=cv2.INTER_CUBIC
    )

    return gray

def preprocess_text_sharp(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    # ���¡�͹ ������� OCR ��繵���˭���
    gray = cv2.resize(
        gray,
        None,
        fx=5,
        fy=5,
        interpolation=cv2.INTER_CUBIC
    )

    # ���� contrast Ẻ�� �
    gray = cv2.convertScaleAbs(
        gray,
        alpha=1.25,
        beta=5
    )

    # sharpen �ҡ������
    sharpen_kernel = np.array([
        [0, -0.5, 0],
        [-0.5, 3, -0.5],
        [0, -0.5, 0]
    ], dtype=np.float32)

    gray = cv2.filter2D(
        gray,
        -1,
        sharpen_kernel
    )

    gray = cv2.rotate(
        gray,
        cv2.ROTATE_90_COUNTERCLOCKWISE
    )

    return gray

if OCR_MODE == "number":

    print("OCR MODE : NUMBER")

    gray = preprocess_number(crop)

    allowlist = "0123456789"

elif OCR_MODE == "text":

    print("OCR MODE : TEXT")

    gray = preprocess_text(crop)

    allowlist = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_."

elif OCR_MODE == "text_no_rotate":

    print("OCR MODE : TEXT NO ROTATE")

    gray = preprocess_text_no_rotate(crop)

    allowlist = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_."

elif OCR_MODE == "text_sharp":

    print("OCR MODE : TEXT SHARP")

    gray = preprocess_text_sharp(crop)

    allowlist = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-_."

else:

    print("Invalid OCR_MODE")
    exit()

cv2.imwrite("ocr_roi.jpg", gray)

print("Loading OCR model...")

reader = easyocr.Reader(["en"], gpu=False)

print("Reading OCR...")


results = reader.readtext(
    gray,
    allowlist=allowlist,
    detail=1,
    paragraph=False,
    decoder='beamsearch'
)

print("\n===== OCR RESULT =====")

if not results:
    print("No text detected")
else:
    final_text = ""

    for bbox, text, conf in results:
        print(f"TEXT: {text}")
        print(f"CONF: {conf:.2f}")
        print("-------------------")
        final_text += text

    print("\nFINAL :", final_text)

print("======================")

cv2.imshow("OCR ROI", gray)

print("Press ESC or close window to exit")

while True:
    if cv2.getWindowProperty("OCR ROI", cv2.WND_PROP_VISIBLE) < 1:
        break

    key = cv2.waitKey(1) & 0xFF

    if key == 27:
        break

cv2.destroyAllWindows()