import firebase_admin
from firebase_admin import credentials, storage, firestore
import os
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from PIL import Image

cred = credentials.Certificate("secret.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'weldlabeling.firebasestorage.app'
})

bucket = storage.bucket()

download_folder = "downloaded_photos"
os.makedirs(download_folder, exist_ok=True)

blobs = bucket.list_blobs(prefix="photos/")

db = firestore.client()

photos_ref = db.collection("photos")
pins_ref = db.collection("pins")

def process_blob(blob):
    file_name = os.path.basename(blob.name)
    if not file_name:
        return
    file_path = os.path.join(download_folder, file_name)
    print(f"Scaricando {file_name}...")
    

    photo_id, _ = os.path.splitext(file_name)
    photo_doc = photos_ref.document(photo_id).get()
    if not photo_doc.exists:
        return

    photo_data = photo_doc.to_dict()
    if not photo_data.get("processed", False):
        return

    timestamp_str = photo_data.get("date")
    print(timestamp_str, type(timestamp_str))
    timestamp = datetime.fromisoformat(timestamp_str.isoformat())
    exclude_start = datetime.fromisoformat("2025-02-19T14:30:00+01:00")
    exclude_end = datetime.fromisoformat("2025-02-19T16:15:00+01:00")

    if exclude_start <= timestamp <= exclude_end:
        return

    pins_docs = pins_ref.where("photo_id", "==", photo_id).get()
    if len(pins_docs) < 2:
        return

    annotation = ET.Element("annotation")
    ET.SubElement(annotation, "folder").text = download_folder
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
        elif label == "NO":
            label = "bad_weld"
        ET.SubElement(obj, "name").text = label
        bndbox = ET.SubElement(obj, "bndbox")
        ET.SubElement(bndbox, "xmin").text = str(pin_data.get("x_left"))
        ET.SubElement(bndbox, "xmax").text = str(pin_data.get("x_right"))
        ET.SubElement(bndbox, "ymin").text = str(pin_data.get("y_top"))
        ET.SubElement(bndbox, "ymax").text = str(pin_data.get("y_bottom"))

    tree = ET.ElementTree(annotation)
    xml_file = os.path.join(download_folder, f"{photo_id}.xml")
    tree.write(xml_file, encoding="utf-8", xml_declaration=True)
    blob.download_to_filename(file_path)

# with ThreadPoolExecutor() as executor:
#     executor.map(process_blob, blobs)
first_blob = next(blobs, None)
if first_blob:
    process_blob(first_blob)

print("Download delle foto e creazione dei file XML completati! 🎉")
