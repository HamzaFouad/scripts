import os
import subprocess

def convert_to_mp3(file_path):
    """
    Converts the given file to mp3 format using ffmpeg and, if successful,
    replaces the original file with the mp3 version.
    """
    # Generate the new file path by replacing the original extension with .mp3
    mp3_path = os.path.splitext(file_path)[0] + ".mp3"
    
    # Convert the file to mp3 using ffmpeg
    try:
        # Run the ffmpeg conversion command
        subprocess.run(['ffmpeg', '-i', file_path, '-q:a', '2', mp3_path], check=True)
        
        # If conversion is successful, remove the original file and replace with mp3
        os.remove(file_path)
        print(f"Successfully converted and replaced: {file_path} with {mp3_path}")
    except subprocess.CalledProcessError as e:
        # Log an error message if conversion fails
        print(f"Error converting {file_path}: {e}")
        # Remove the partially converted file if it exists
        if os.path.exists(mp3_path):
            os.remove(mp3_path)

def process_directory(directory):
    """
    Loops through all files in a directory and converts any non-mp3 files to mp3.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Check if the file is not already an mp3
            if not file.lower().endswith('.mp3'):
                convert_to_mp3(file_path)

# Set the directory you want to process
directory_to_process = "10_quran_shk_mustafa"
process_directory(directory_to_process)
