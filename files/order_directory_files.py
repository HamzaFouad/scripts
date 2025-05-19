import os

def rename_files_with_new_order(directory):

    # Get list of files in the directory and sort them to ensure order
    files = sorted(os.listdir(directory))

    # Initialize a counter for file numbering
    counter = 1111

    # Loop through each file
    for filename in files:
        # Check if it's a file (and not a directory)
        if os.path.isfile(os.path.join(directory, filename)):
            # Create the new filename with the padded counter
            new_filename = f"{counter:04d}_{filename}"

            # Get full file paths
            old_filepath = os.path.join(directory, filename)
            new_filepath = os.path.join(directory, new_filename)

            # Rename the file
            os.rename(old_filepath, new_filepath)
            print(f"Renamed: {filename} -> {new_filename}")

            # Increment the counter
            counter += 1

# Example usage:
directory_path = input("Enter the directory path: ")

rename_files_with_new_order(directory_path)
