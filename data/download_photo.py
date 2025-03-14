import firebase_admin
from firebase_admin import credentials, storage, firestore
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from PIL import Image
import random

cred = credentials.Certificate("secret.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'weldlabeling.firebasestorage.app'
})

bucket = storage.bucket()

download_folder = "downloaded_photos"
train_folder = os.path.join(download_folder, "train")
val_folder = os.path.join(download_folder, "val")
os.makedirs(train_folder, exist_ok=True)
os.makedirs(val_folder, exist_ok=True)

blobs = list(bucket.list_blobs(prefix="photos/"))
random.shuffle(blobs)

db = firestore.client()

photos_ref = db.collection("photos")
pins_ref = db.collection("pins")

yes_count = 0
no_count = 0
photo_count = 0
val_split = int(0.2 * len(blobs))

for i, blob in enumerate(blobs):
    file_name = os.path.basename(blob.name)
    if not file_name:
        continue
    
    folder = val_folder if i < val_split else train_folder
    file_path = os.path.join(folder, file_name)
    
    photo_id, _ = os.path.splitext(file_name)
    photo_doc = photos_ref.document(photo_id).get()
    if not photo_doc.exists:
        continue

    photo_data = photo_doc.to_dict()
    if not photo_data.get("processed", False):
        continue

    timestamp_str = photo_data.get("date")
    timestamp = datetime.fromisoformat(timestamp_str.isoformat())
    exclude_start = datetime.fromisoformat("2025-02-19T14:30:00+01:00")
    exclude_end = datetime.fromisoformat("2025-02-19T16:15:00+01:00")

    if exclude_start <= timestamp <= exclude_end:
        continue

    pins_docs = pins_ref.where("photo_id", "==", photo_id).get()
    if len(pins_docs) < 2:
        continue

    annotation = ET.Element("annotation")
    ET.SubElement(annotation, "folder").text = folder
    ET.SubElement(annotation, "filename").text = file_name
    ET.SubElement(annotation, "path").text = file_path
    source = ET.SubElement(annotation, "source")
    ET.SubElement(source, "database").text = "weldLabel"
    size = ET.SubElement(annotation, "size")
    blob.download_to_filename(file_path)
    with Image.open(file_path) as img:
        width, height = img.size
        depth = len(img.getbands())
    ET.SubElement(size, "width").text = str(width)
    ET.SubElement(size, "height").text = str(height)
    ET.SubElement(size, "depth").text = str(depth)

    for pin_doc in pins_docs:
        pin_data = pin_doc.to_dict()
        obj = ET.SubElement(annotation, "object")
        label = pin_data.get("label")
        if label == "SI":
            label = "good_weld"
            yes_count += 1
        elif label == "NO":
            label = "bad_weld"
            no_count += 1
        if label not in ["good_weld", "bad_weld"]:
            print(f"Label {label} non riconosciuto")
        ET.SubElement(obj, "name").text = label
        bndbox = ET.SubElement(obj, "bndbox")
        ET.SubElement(bndbox, "xmin").text = str(pin_data.get("x_left"))
        ET.SubElement(bndbox, "xmax").text = str(pin_data.get("x_right"))
        ET.SubElement(bndbox, "ymin").text = str(pin_data.get("y_top"))
        ET.SubElement(bndbox, "ymax").text = str(pin_data.get("y_bottom"))

    tree = ET.ElementTree(annotation)
    xml_file = os.path.join(folder, f"{photo_id}.xml")
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)
    photo_count += 1

print("Download delle foto e creazione dei file XML completati! 🎉")
print(f"Yes count: {yes_count}")
print(f"No count: {no_count}")
print(f"Photos saved: {photo_count}")