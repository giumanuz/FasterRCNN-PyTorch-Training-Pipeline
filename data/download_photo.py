import firebase_admin
from firebase_admin import credentials, storage, firestore
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from PIL import Image
from tqdm import tqdm

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

blobs = bucket.list_blobs(prefix="photos/")

db = firestore.client()

photos_ref = db.collection("photos")
pins_ref = db.collection("pins")

yes_count = 0
no_count = 0
photo_count = 0


def process_blob(blob):
    global yes_count, no_count, photo_count
    file_name = os.path.basename(blob.name)
    if not file_name:
        return

    # Determine the folder based on the 80/20 ratio
    if photo_count % 5 == 0:
        target_folder = val_folder
    else:
        target_folder = train_folder

    photo_id, _ = os.path.splitext(file_name)
    photo_doc = photos_ref.document(photo_id).get()
    if not photo_doc.exists:
        return

    photo_data = photo_doc.to_dict()
    if not photo_data.get("processed", False):
        return

    timestamp_str = photo_data.get("date")
    timestamp = datetime.fromisoformat(timestamp_str.isoformat())
    exclude_start = datetime.fromisoformat("2025-02-19T14:30:00+01:00")
    exclude_end = datetime.fromisoformat("2025-02-19T16:15:00+01:00")

    if exclude_start <= timestamp <= exclude_end:
        return

    pins_docs = pins_ref.where("photo_id", "==", photo_id).get()
    if len(pins_docs) < 2:
        return

    # Count the objects without saving the files
    for pin_doc in pins_docs:
        pin_data = pin_doc.to_dict()
        label = pin_data.get("label")
        if label == "SI":
            yes_count += 1
        elif label == "NO":
            no_count += 1

    photo_count += 1


for blob in tqdm(blobs, desc="Processing blobs"):
    process_blob(blob)

print("Conteggio delle foto e dei file XML completato! 🎉")
print(f"Yes count: {yes_count}")
print(f"No count: {no_count}")
print(f"Photos counted: {photo_count}")
