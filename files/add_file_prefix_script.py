import os

def add_prefix_to_files(directory, prefix):
    # Ensure prefix is treated as a string
    prefix = str(prefix)

    # Get list of files in the directory
    files = os.listdir(directory)

    # Loop through each file
    for filename in files:
        # Check if it's a file (and not a directory)
        if os.path.isfile(os.path.join(directory, filename)):
            # Create the new filename with the prefix
            new_filename = f"{prefix}_{filename}"

            # Get full file paths
            old_filepath = os.path.join(directory, filename)
            new_filepath = os.path.join(directory, new_filename)

            # Rename the file
            os.rename(old_filepath, new_filepath)
            print(f"Renamed: {filename} -> {new_filename}")

# Example usage:
directory_path = input("Enter the directory path: ")
prefix = input("Enter the prefix to add: ")

add_prefix_to_files(directory_path, prefix)
