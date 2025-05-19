import os
import shutil
import re
import csv

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
    if '__' in directory_name:
        return directory_name.split('__')[0]
    return "unknown"

def clean_filename(filename):
    """
    Cleans a filename by removing characters that are not English letters, numbers, or special characters.

    Args:
        filename (str): The original filename without extension.

    Returns:
        str: The cleaned filename.
    """
    return re.sub(r"[^a-zA-Z0-9._-]", "", filename)

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

def copy_audio_file(source_path, destination_dir, prefix, counter):
    """
    Copies an audio file to the destination directory with a modified name.

    Args:
        source_path (str): Path to the source file.
        destination_dir (str): Path to the destination directory.
        prefix (str): Prefix to add to the filename.
    """
    file_name = os.path.basename(source_path)
    file_name_without_ext, ext = os.path.splitext(file_name)
    # clean_name = clean_filename(file_name_without_ext)
    # new_name = f"{counter}_{prefix}_{clean_name}{ext}"
    new_name = f"{counter}{ext}"
    destination_path = os.path.join(destination_dir, new_name)
    destination_path = handle_file_name_conflict(destination_path)
    shutil.copy2(source_path, destination_path)
    print(f"Copied {source_path} to {destination_path}")

def add_splitter_audio(destination_dir, splitter_audio_path, counter):
    splitter_file_name = os.path.basename(splitter_audio_path)
    new_name = f"{counter}_splitter_{splitter_file_name}"
    destination_path = os.path.join(destination_dir, new_name)
    shutil.copy2(splitter_audio_path, destination_path)
    print(f"Added splitter audio: {splitter_audio_path} as {destination_path}")
    return counter + 1

def collect_audios(source_parent_dir, destination_dir, splitter_audio_path, start_counter=1111):
    """
    Collects all .mp3 files from all subdirectories of a given parent directory,
    modifies filenames to include a prefix based on the directory name, and copies 
    them into a single destination directory. Additionally, writes a CSV file
    with the starting and ending numbers for each directory.

    Args:
        source_parent_dir (str): Path to the parent directory containing subdirectories with audio files.
        destination_dir (str): Path to the directory where all audio files will be copied.
    """
    ensure_directory_exists(destination_dir)
    csv_data = []
    counter = start_counter
    
    # Sort directories before processing
    subdirs = sorted([os.path.join(source_parent_dir, d) for d in os.listdir(source_parent_dir) if os.path.isdir(os.path.join(source_parent_dir, d))])

    for root in subdirs:
        dir_name = os.path.basename(root)
        prefix = get_directory_prefix(dir_name)

        start_laptop_order = None
        end_laptop_order = None
        jac_ordering_counter = 1

        files = sorted([f for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))])

        for file in sorted(files):
            if file.lower().endswith(".mp3"):
                source_path = os.path.join(root, file)
                if start_laptop_order is None:
                    start_laptop_order = counter
                end_laptop_order = counter

                copy_audio_file(source_path, destination_dir, prefix, counter)
                counter += 1
                jac_ordering_counter += 1

        if start_laptop_order is not None:
            jac_ordering_start = 1
            jac_ordering_end = jac_ordering_counter
            csv_data.append([
                dir_name,
                start_laptop_order,
                end_laptop_order,
                jac_ordering_start,
                jac_ordering_end,
            ])

            # Add splitter audio after processing the current playlist
            counter = add_splitter_audio(destination_dir, splitter_audio_path, counter)

    # Write CSV data
    csv_file_path = os.path.join(destination_dir, "directory_summary.csv")
    with open(csv_file_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["directoryname", "start_laptop_order", "end_laptop_order", "start_jac_order", "end_jac_order"])
        writer.writerows(csv_data)
    print(f"CSV summary written to {csv_file_path}")

# Example usage
# source_directory = input("Enter the path of the source parent directory: ").strip()
# destination_directory = input("Enter the path of the destination directory: ").strip()
# splitter_audio_path = input("Enter the path of the splitter audio file: ").strip()

source_directory = "/Users/hamzafouad/my_workspace/personal/audios/card_01_03_2025"
destination_directory = "/Users/hamzafouad/my_workspace/personal/audios/memory_card_01_03_2025"
splitter_audio_path = "/Users/hamzafouad/my_workspace/personal/audios/original/seek_afterlife.mp3"

collect_audios(source_directory, destination_directory, splitter_audio_path, start_counter=1111)
