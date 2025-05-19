import os
import re

def rename_files(directory, new_prefix):
    new_prefix = str(new_prefix)
    # if len(new_prefix) != 5:
    #     print("Error: new_prefix must be exactly 5 characters (e.g., '04_04').")
    #     return

    for filename in os.listdir(directory):
        match = re.match(r'^\d{2}_', filename)
        if match:
            parts = filename.split('_', 1)
            if len(parts) == 2:
                new_filename = f"{new_prefix}_{parts[1]}"
                old_filepath = os.path.join(directory, filename)
                new_filepath = os.path.join(directory, new_filename)
                try:
                    os.rename(old_filepath, new_filepath)
                    print(f"Renamed: {filename} -> {new_filename}")
                except PermissionError as e:
                    print(f"PermissionError: {e}. File: {old_filepath}, Target: {new_filepath}")
                    print(f"Testing permissions for file {old_filepath}:")
                    print(f"Readable: {os.access(old_filepath, os.R_OK)}")
                    print(f"Writable: {os.access(old_filepath, os.W_OK)}")
                except Exception as e:
                    print(f"Error: {e}. File: {old_filepath}, Target: {new_filepath}")

# Example usage
directory_path = input("Enter the directory path: ")
new_prefix = input("Enter the new digit prefix: ")

rename_files(directory_path, new_prefix)
