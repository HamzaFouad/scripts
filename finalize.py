import os
import shutil
import re
import csv
import logging
from notifications import send_telegram_notification

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
    _, ext = os.path.splitext(splitter_audio_path)
    new_name = f"{counter}{ext}"
    destination_path = os.path.join(destination_dir, new_name)
    destination_path = handle_file_name_conflict(destination_path)
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
    current_jac_order_val = 1
    splitter_numbers = []

    
    # Sort directories before processing
    subdirs = sorted([os.path.join(source_parent_dir, d) for d in os.listdir(source_parent_dir) if os.path.isdir(os.path.join(source_parent_dir, d))])

    for root in subdirs:
        dir_name = os.path.basename(root)
        prefix = get_directory_prefix(dir_name)

        start_laptop_order = None
        end_laptop_order = None
        dir_specific_start_jac_order = None # To store the JAC start for this directory's files

        files = sorted([f for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))])

        for file in sorted(files):
            if file.lower().endswith(".mp3"):
                source_path = os.path.join(root, file)
                if start_laptop_order is None:
                    start_laptop_order = counter
                    dir_specific_start_jac_order = current_jac_order_val

                end_laptop_order = counter

                copy_audio_file(source_path, destination_dir, prefix, counter)
                counter += 1
                current_jac_order_val += 1

        if start_laptop_order is not None:
            dir_specific_end_jac_order = current_jac_order_val - 1
            csv_data.append([
                dir_name,
                start_laptop_order,
                end_laptop_order,
                dir_specific_start_jac_order,
                dir_specific_end_jac_order,
            ])

            # Add splitter audio after processing the current playlist
            splitter_numbers.append(counter)
            counter = add_splitter_audio(destination_dir, splitter_audio_path, counter)

    # Write CSV data
    destination_dir_name = os.path.basename(destination_dir)
    csv_filename = f"{destination_dir_name}_summary.csv"
    csv_file_path = os.path.join(source_parent_dir, csv_filename)
    with open(csv_file_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["directoryname", "start_laptop_order", "end_laptop_order", "start_jac_order", "end_jac_order"])
        writer.writerows(csv_data)
        # Add splitter numbers at the end
        writer.writerow([])  # Empty row for spacing
        writer.writerow(["Splitter Numbers"] + splitter_numbers)
    print(f"CSV summary written to {csv_file_path}")
    return csv_file_path

# Example usage
# source_directory = input("Enter the path of the source parent directory: ").strip()
# destination_directory = input("Enter the path of the destination directory: ").strip()
# splitter_audio_path = input("Enter the path of the splitter audio file: ").strip()

source_directory = "/Users/hamzafouad/my_workspace/personal/audios/medo_memory_01_01_2026"
destination_directory = "/Users/hamzafouad/my_workspace/personal/audios/medo_memory_01_01_2026_finalized"
splitter_audio_path = "/Users/hamzafouad/my_workspace/personal/patience_reward_ayah.mp3"

if __name__ == "__main__":
    try:
        print("Starting audio collection process...")
        csv_file_path = collect_audios(source_directory, destination_directory, splitter_audio_path, start_counter=1111)
        print("Audio collection completed successfully!")
        
        # Send Telegram notification
        message = (
            f"✅ Finalization Complete!\n\n"
            f"📁 Source: {os.path.basename(source_directory)}\n"
            f"📂 Destination: {os.path.basename(destination_directory)}\n"
            f"📊 CSV file generated successfully.\n"
            f"📎 See attached CSV for details."
        )
        
        success = send_telegram_notification(message, csv_file_path)
        if success:
            print("Telegram notification sent successfully!")
        else:
            print("Warning: Failed to send Telegram notification. Check your bot token and chat ID.")
            
    except Exception as e:
        error_message = f"❌ Error during finalization: {str(e)}"
        print(error_message)
        
        # Try to send error notification
        try:
            send_telegram_notification(error_message)
        except Exception as notification_error:
            logger.error(f"Failed to send error notification to Telegram: {notification_error}")
        
        raise
