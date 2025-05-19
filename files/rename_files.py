import os
import re

def sanitize_filename(filename):
    ''' 
    Replace spaces and special characters with underscores.
    Collapse consecutive underscores into a single underscore.
    '''
    # Replace any character that is not alphanumeric with an underscore
    sanitized = re.sub(r'[^a-zA-Z0-9]+', '_', filename)
    # Ensure no leading or trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized

def rename_files_in_directory(directory):
    for root, _, files in os.walk(directory):
        for filename in files:
            sanitized_name = sanitize_filename(filename)

            old_path = os.path.join(root, filename)
            new_path = os.path.join(root, f"{filename}.mp3")
            
            if old_path != new_path:  # Avoid renaming if names are the same
                os.rename(old_path, new_path)
                print(f"Renamed '{old_path}' to '{new_path}'")

if __name__ == "__main__":
    directory = "card"
    rename_files_in_directory(directory)
