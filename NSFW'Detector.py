from transformers import pipeline
from PIL import Image, ImageFilter, ImageFile

import ctypes
import os
import cv2
import csv
import hashlib

ImageFile.LOAD_TRUNCATED_IMAGES = True

ctypes.windll.kernel32.SetConsoleTitleW("NSFW'Detector :")

image_formats = (".png", ".jpg", ".jpeg")
video_formats = (".mp4", ".mov", ".avi", ".mkv")

model_nsfw = pipeline("image-classification", model="AdamCodd/vit-base-nsfw-detector", use_fast=True)

desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
quarantine_path = os.path.join(desktop_path, "quarantaine")

os.makedirs(quarantine_path, exist_ok=True)

report_path = os.path.join(desktop_path, "rapport.csv")
hash_path = os.path.join(desktop_path, "nsfw_hash.txt")

try:

    with open(report_path, mode="w", newline="", encoding="utf-8") as csv_file:

        writer = csv.writer(csv_file)
        writer.writerow(["Nom :", "Chemin :", "Catégorie :", "Confiance :"])

        for folder, subfolders, files in os.walk(desktop_path):

            for file in files:

                file_path = os.path.join(folder, file)

                if file.lower().endswith(image_formats):

                    image = Image.open(file_path).convert("RGB")
                    prediction = model_nsfw(image)

                elif file.lower().endswith(video_formats):

                    capture = cv2.VideoCapture(file_path)
                    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
                    step = max(1, total // 5)
                    nsfw_detected = False
                    frames_to_check = []

                    for count in range(0, total, step):
                        capture.set(cv2.CAP_PROP_POS_FRAMES, count)
                        ret, frame = capture.read()
                        if not ret:

                            continue

                        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        pred = model_nsfw(img)
                        frames_to_check.append(count)

                        for category in pred:

                            if "NSFW" in category.get("label","").upper() and category.get("score",0) > 0.5:
                                nsfw_detected = True
                                break

                        if nsfw_detected:

                            break

                    capture.release()

                    if not nsfw_detected:

                        continue

                    prediction = [{"label":"NSFW","score":1.0}]

                    nsfw = True

                else:

                    continue

                nsfw_flag = False
                score = 0.0

                for category in prediction:

                    label = category.get("label", "Unknown")
                    value = category.get("score", 0.0)

                    if "NSFW" in label.upper():

                        score = max(score, value)

                        if value > 0.5: 

                            nsfw_flag = True

                label = "NSFW" if nsfw_flag else "NORMAL"
                percentage = f"{score*100:.2f} %"

                writer.writerow([file, file_path, label, percentage])

                if nsfw_flag:
                    
                    print(f"Un fichier NSFW vient d'être trouvé : {file}, celui-ci est désormais en quarantaine !")
                    
                    with open(file_path, "rb") as f:

                        file_hash = hashlib.sha256(f.read()).hexdigest()

                    with open(hash_path, "a", encoding="utf-8") as hash:

                        hash.write(file_hash + "\n")

                    if file.lower().endswith(image_formats):

                        image = image.filter(ImageFilter.GaussianBlur(10))
                        image.save(os.path.join(quarantine_path, file))

                        os.remove(file_path)
                    
                    else:

                        capture = cv2.VideoCapture(file_path)
                        four_cc = cv2.VideoWriter_fourcc(*"mp4v")
                        output_path = os.path.join(quarantine_path, file)

                        fps = capture.get(cv2.CAP_PROP_FPS)
                        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        
                        out = cv2.VideoWriter(output_path, four_cc, fps, (width, height))

                        while True:

                            ret, frame = capture.read()

                            if not ret:

                                break

                            frame = cv2.GaussianBlur(frame, (51, 51), 0)
                            out.write(frame)

                        capture.release()
                        out.release()

                        os.remove(file_path)

except KeyboardInterrupt:
    
    pass