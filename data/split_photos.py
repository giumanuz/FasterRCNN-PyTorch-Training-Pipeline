import os
import shutil
import random

# Define paths
downloaded_photos_path = 'downloaded_photos'
output_path = 'split_photos'
os.makedirs(output_path, exist_ok=True)
train_path = os.path.join(output_path, 'train')
val_path = os.path.join(output_path, 'val')

# Create output directories
os.makedirs(train_path, exist_ok=True)
os.makedirs(val_path, exist_ok=True)

# Get list of files
files = [f for f in os.listdir(downloaded_photos_path) if f.endswith('.JPG')]
random.shuffle(files)

# Split files into train and val
split_index = int(len(files) * 0.8)
train_files = files[:split_index]
val_files = files[split_index:]

# Function to copy files
def copy_files(file_list, destination):
    for file in file_list:
        base_name = os.path.splitext(file)[0]
        jpg_file = f"{base_name}.JPG"
        xml_file = f"{base_name}.xml"
        shutil.copy(os.path.join(downloaded_photos_path, jpg_file), os.path.join(destination, jpg_file))
        shutil.copy(os.path.join(downloaded_photos_path, xml_file), os.path.join(destination, xml_file))

# Copy files to train and val directories
copy_files(train_files, train_path)
copy_files(val_files, val_path)

print("Files have been split and copied successfully.")