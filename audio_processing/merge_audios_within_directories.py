import os
import subprocess

def merge_audios_with_silence(parent_directory, splitter_audio_path):
    """
    Merges all audio files within each subdirectory of a parent directory,
    separated by a custom audio splitter. The merged audio is named after
    the subdirectory and saved beside it as an MP3 file.

    Args:
        parent_directory (str): Path to the parent directory containing subdirectories of audio files.
        splitter_audio_path (str): Path to the splitter audio file.
    """
    # Get the sample rate of the splitter audio
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate", "-of", "default=noprint_wrappers=1:nokey=1", splitter_audio_path],
        capture_output=True,
        text=True,
        check=True
    )
    splitter_sample_rate = result.stdout.strip()

    # Iterate over all child directories in the parent directory
    for child_dir in os.listdir(parent_directory):
        child_path = os.path.join(parent_directory, child_dir)

        # Check if the path is a directory
        if os.path.isdir(child_path):
            print(f"Processing directory: {child_dir}")

            # List and sort all audio files in the child directory
            audio_files = [
                os.path.join(child_path, f) for f in os.listdir(child_path)
                if f.lower().endswith((".mp3", ".wav", ".ogg", ".flac", ".aac"))
            ]
            audio_files.sort()  # Optional: sort files alphabetically

            # Create a temporary concat text file
            concat_file_path = os.path.join(parent_directory, f"{child_dir}_concat.txt")
            with open(concat_file_path, "w") as concat_file:
                for audio_file in audio_files:
                    concat_file.write(f"file '{audio_file}'\n")
                    concat_file.write(f"file '{splitter_audio_path}'\n")

            # Remove the last splitter entry for correctness
            with open(concat_file_path, "r") as concat_file:
                lines = concat_file.readlines()
            with open(concat_file_path, "w") as concat_file:
                concat_file.writelines(lines[:-1])

            # Define the output file path
            output_file = os.path.join(parent_directory, f"{child_dir}.mp3")

            # Use ffmpeg to concatenate all audio files
            subprocess.run([
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file_path,
                "-ar", splitter_sample_rate,
                "-ac", "2",  # Stereo audio for better quality
                "-b:a", "192k",  # Adjust bit rate for better quality
                "-y", output_file
            ], check=True)

            # Remove the temporary concat file
            os.remove(concat_file_path)

            print(f"Merged audio saved to {output_file}")

# Example usage
parent_directory = input("Enter the directory path: ")
splitter_audio_path = input("Enter the path of the audio file to split: ")
merge_audios_with_silence(parent_directory, splitter_audio_path)
