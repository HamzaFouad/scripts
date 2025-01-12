import os
import shutil
import re

def ensure_directory_exists(directory):
    """
    Ensures the given directory exists, creating it if necessary.

    Args:
        directory (str): Path to the directory.
    """
    os.makedirs(directory, exist_ok=True)

def get_directory_prefix(directory_name):
    """
    Extracts the first two digits from the directory name and adds an underscore.
    If no digits are found, returns "999_".

    Args:
        directory_name (str): Name of the directory.

    Returns:
        str: The prefix (e.g., "12_") or "999_" if no digits are found.
    """
    match = re.match(r"(\d{2})", directory_name)
    return f"{match.group(1)}_" if match else "999_"

def clean_filename(filename):
    """
    Cleans a filename by removing non-numeric characters, except underscores.

    Args:
        filename (str): The original filename without extension.

    Returns:
        str: The cleaned filename.
    """
    return re.sub(r"[^\d_]", "", filename)

def handle_file_name_conflict(destination_path):
    """
    Resolves filename conflicts by appending a counter to the filename.

    Args:
        destination_path (str): The intended path for the file.

    Returns:
        str: A unique file path.
    """
    base, ext = os.path.splitext(destination_path)
    counter = 1
    while os.path.exists(destination_path):
        destination_path = f"{base}_{counter}{ext}"
        counter += 1
    return destination_path

def copy_audio_file(source_path, destination_dir, prefix):
    """
    Copies an audio file to the destination directory with a modified name.

    Args:
        source_path (str): Path to the source file.
        destination_dir (str): Path to the destination directory.
        prefix (str): Prefix to add to the filename.
    """
    file_name = os.path.basename(source_path)
    file_name_without_ext, ext = os.path.splitext(file_name)
    clean_name = clean_filename(file_name_without_ext)
    new_name = f"{prefix}{clean_name}{ext}"
    destination_path = os.path.join(destination_dir, new_name)
    destination_path = handle_file_name_conflict(destination_path)
    shutil.copy2(source_path, destination_path)
    print(f"Copied {source_path} to {destination_path}")

def collect_audios(source_parent_dir, destination_dir):
    """
    Collects all .mp3 files from all subdirectories of a given parent directory,
    modifies filenames to include a prefix based on the directory name, and copies 
    them into a single destination directory.

    Args:
        source_parent_dir (str): Path to the parent directory containing subdirectories with audio files.
        destination_dir (str): Path to the directory where all audio files will be copied.
    """
    ensure_directory_exists(destination_dir)
    for root, _, files in os.walk(source_parent_dir):
        dir_name = os.path.basename(root)
        prefix = get_directory_prefix(dir_name)
        for file in files:
            if file.lower().endswith(".mp3"):  # Check only .mp3 files (case insensitive)
                source_path = os.path.join(root, file)
                copy_audio_file(source_path, destination_dir, prefix)

# Example usage
source_directory = input("Enter the path of the source parent directory: ").strip()
destination_directory = input("Enter the path of the destination directory: ").strip()

collect_audios(source_directory, destination_directory)
