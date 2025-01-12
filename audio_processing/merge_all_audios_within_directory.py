import os
import subprocess

def generate_silence_audio(output_path, duration=3, sample_rate=44100):
    """
    Generates a silent audio file.

    Args:
        output_path (str): Path to save the silent audio file.
        duration (int): Duration of the silence in seconds.
        sample_rate (int): Sample rate for the silent audio.
    """
    subprocess.run([
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"anullsrc=r={sample_rate}:cl=stereo",
        "-t", str(duration),
        "-q:a", "9",
        "-y", output_path
    ], check=True)

def merge_audios_with_silence(parent_directory, splitter_audio_path=None):
    """
    Merges all audio files within each subdirectory of a parent directory,
    separated by a custom audio splitter or silence if no splitter is provided.

    Args:
        parent_directory (str): Path to the parent directory containing subdirectories of audio files.
        splitter_audio_path (str, optional): Path to the splitter audio file. Defaults to 3 seconds of silence.
    """
    # Check if splitter audio path is provided
    if splitter_audio_path is None:
        splitter_audio_path = os.path.join(parent_directory, "silent_splitter.mp3")
        generate_silence_audio(splitter_audio_path)

    # Get the sample rate of the splitter audio
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate", "-of", "default=noprint_wrappers=1:nokey=1", splitter_audio_path],
        capture_output=True,
        text=True,
        check=True
    )
    splitter_sample_rate = result.stdout.strip()
    print(f"Parent directory: {parent_directory}")
    print(f"Splitter audio sample rate: {splitter_sample_rate}")

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
# parent_directory = input("Enter the directory path: ")
# splitter_audio_path = input("Enter the path of the audio file to split (or leave blank for silence): ")
parent_directory = "/Users/hamzafouad/my_workspace/personal/audios/original/dangerous/wrapper"
splitter_audio_path = None  # Pass a valid path or None for silence
merge_audios_with_silence(parent_directory, splitter_audio_path)
