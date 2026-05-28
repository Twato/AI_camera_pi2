import cv2
import easyocr
import os
import numpy as np
import re

image_path = "/home/toto/rpicam_apps_1.9.0-2_arm64/usb_captures/usb_20260525_133755.jpg"

# OCR_MODE = "number"
# OCR_MODE = "text"
# OCR_MODE = "text_no_rotate"
# OCR_MODE = "text_sharp"
OCR_MODE = "text_sharp_no_rotate"
# OCR_MODE = "number_no_rotate"

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

def preprocess_number_no_rotate(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(
        gray,
        None,
        fx=5,
        fy=5,
        interpolation=cv2.INTER_CUBIC
    )

    gray = cv2.convertScaleAbs(
        gray,
        alpha=1.25,
        beta=5
    )

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

    gray = cv2.resize(
        gray,
        None,
        fx=5,
        fy=5,
        interpolation=cv2.INTER_CUBIC
    )

    gray = cv2.convertScaleAbs(
        gray,
        alpha=1.25,
        beta=5
    )

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

def preprocess_text_sharp_no_rotate(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(
        gray,
        None,
        fx=5,
        fy=5,
        interpolation=cv2.INTER_CUBIC
    )

    gray = cv2.convertScaleAbs(
        gray,
        alpha=1.25,
        beta=5
    )

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

    return gray

# =====================
# OCR CLEAN / FIX / VALIDATE
# Pattern:
# 1-3   = number
# 4     = letter
# 5     = number
# 6     = letter
# 7-10  = HEX
# Example: 621U3K000A
# =====================
def clean_ocr_text(text):
    text = text.upper()
    text = text.replace(" ", "")
    text = text.replace("-", "")
    text = text.replace("_", "")
    text = text.replace(".", "")

    return re.sub(r"[^A-Z0-9]", "", text)


def fix_to_digit(ch):
    if ch in ["O", "Q", "D"]:
        return "0"
    if ch in ["I", "L"]:
        return "1"
    if ch == "S":
        return "5"
    if ch == "B":
        return "8"
    return ch


def fix_to_letter(ch):
    if ch == "0":
        return "O"
    if ch == "1":
        return "I"
    if ch == "5":
        return "S"
    if ch == "8":
        return "B"
    return ch


def fix_by_pattern(text):
    text = clean_ocr_text(text)

    if len(text) > 10:
        text = text[:10]

    if len(text) < 10:
        return text, False

    chars = list(text)

    # ��Ƿ�� 1-3 = ����Ţ
    for i in [0, 1, 2]:
        chars[i] = fix_to_digit(chars[i])

    # ��Ƿ�� 4 = ����ѡ��
    chars[3] = fix_to_letter(chars[3])

    # ��Ƿ�� 5 = ����Ţ
    chars[4] = fix_to_digit(chars[4])

    # ��Ƿ�� 6 = ����ѡ��
    chars[5] = fix_to_letter(chars[5])

    # ��Ƿ�� 7-10 = HEX
    # HEX ���� 0-9, A-F
    for i in [6, 7, 8, 9]:
        chars[i] = fix_to_digit(chars[i])

    fixed = "".join(chars)

    pattern = r"^[0-9]{3}[A-Z][0-9][A-Z][0-9A-F]{4}$"
    is_valid = re.match(pattern, fixed) is not None

    return fixed, is_valid


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

elif OCR_MODE == "text_sharp_no_rotate":

    print("OCR MODE : TEXT SHARP NO ROTATE")

    gray = preprocess_text_sharp_no_rotate(crop)

    allowlist = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-_."

elif OCR_MODE == "number_no_rotate":

    print("OCR MODE : NUMBER NO ROTATE")

    gray = preprocess_number_no_rotate(crop)

    allowlist = "0123456789"

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
    decoder="beamsearch"
)

print("\n===== OCR RESULT =====")

if not results:
    print("No text detected")

else:
    raw_final = ""

    for bbox, text, conf in results:
        print(f"TEXT: {text}")
        print(f"CONF: {conf:.2f}")
        print("-------------------")

        raw_final += text

    print("\nRAW FINAL :", raw_final)

    # �� pattern ੾������ code
    if OCR_MODE in ["text_sharp", "text_sharp_no_rotate"]:

        fixed_text, is_valid = fix_by_pattern(raw_final)

        print("FIX FINAL :", fixed_text)
        print("VALID     :", is_valid)

    else:

        print("FINAL     :", raw_final)

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