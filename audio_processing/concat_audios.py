import os
import subprocess

def concatenate_audios(wrapper_dir, hidden_dir, splitter_audio_path, output_parent_dir):
    """
    Concatenates audios from the wrapper directory with audios from the hidden directory,
    separated by a splitter audio. The output is saved in the parent directory
    under a directory named 'hidden_podcasts'.

    Args:
        wrapper_dir (str): Path to the wrapper directory containing main audio files.
        hidden_dir (str): Path to the hidden directory containing additional audio files.
        splitter_audio_path (str): Path to the splitter audio file.
        output_parent_dir (str): Path to the parent directory where results are saved.
    """
    # Ensure the output directory exists
    output_dir = os.path.join(output_parent_dir, "hidden_podcasts_1_12")
    os.makedirs(output_dir, exist_ok=True)

    # Get the sample rate of the splitter audio
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate", "-of", "default=noprint_wrappers=1:nokey=1", splitter_audio_path],
            capture_output=True,
            text=True,
            check=True
        )
        splitter_sample_rate = result.stdout.strip()
        if not splitter_sample_rate.isdigit():
            raise ValueError("Invalid sample rate retrieved.")
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Error: Could not retrieve sample rate for splitter audio. Using default sample rate. {e}")
        splitter_sample_rate = "44100"  # Default to 44.1 kHz

    # Create a 5-second silence file and a 2-second silence file
    five_sec_silence = os.path.join(output_dir, "5sec_silence.mp3")
    two_sec_silence = os.path.join(output_dir, "2sec_silence.mp3")
    if not os.path.exists(five_sec_silence):
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "5", "-q:a", "9", "-y", five_sec_silence
        ], check=True)
    if not os.path.exists(two_sec_silence):
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "2", "-q:a", "9", "-y", two_sec_silence
        ], check=True)

    # List and sort audio files in wrapper and hidden directories
    wrapper_files = sorted([
        os.path.join(wrapper_dir, f) for f in os.listdir(wrapper_dir)
        if f.lower().endswith((".mp3", ".wav", ".ogg", ".flac", ".aac"))
    ])
    hidden_files = sorted([
        os.path.join(hidden_dir, f) for f in os.listdir(hidden_dir)
        if f.lower().endswith((".mp3", ".wav", ".ogg", ".flac", ".aac"))
    ])

    # Ensure wrapper directory has at least as many files as the hidden directory
    if len(wrapper_files) < len(hidden_files):
        print("Error: Wrapper directory has fewer files than hidden directory. Skipping excess hidden files.")

    # Process files pairwise
    for i, wrapper_file in enumerate(wrapper_files):
        if i >= len(hidden_files):
            break  # Stop if hidden files are exhausted

        hidden_file = hidden_files[i]
        wrapper_name, wrapper_ext = os.path.splitext(os.path.basename(wrapper_file))

        # Create a temporary concat text file
        concat_file_path = os.path.join(output_dir, f"{wrapper_name}_concat.txt")
        with open(concat_file_path, "w") as concat_file:
            concat_file.write(f"file '{wrapper_file}'\n")
            concat_file.write(f"file '{five_sec_silence}'\n")
            concat_file.write(f"file '{splitter_audio_path}'\n")
            concat_file.write(f"file '{two_sec_silence}'\n")
            concat_file.write(f"file '{hidden_file}'\n")

        # Define the output file path
        output_file = os.path.join(output_dir, f"{wrapper_name}{wrapper_ext}")

        # Use ffmpeg to concatenate the audio files
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

        print(f"Processed {wrapper_file} + {hidden_file} -> {output_file}")

# Example usage
# wrapper_directory = input("Enter the path of the wrapper directory: ").strip()
# hidden_directory = input("Enter the path of the hidden directory: ").strip()
# splitter_audio = input("Enter the path of the splitter audio: ").strip()
# output_directory = input("Enter the path of the output parent directory: ").strip()

wrapper_directory = "/Users/hamzafouad/my_workspace/personal/audios/xx/merging_anashid/wrapper"
hidden_directory = "/Users/hamzafouad/my_workspace/personal/audios/xx/merging_anashid/hidden"
splitter_audio = "/Users/hamzafouad/my_workspace/personal/audios/xx/alhamdullah.mp3"
output_directory = "/Users/hamzafouad/my_workspace/personal/audios/xx/merging_anashid"

concatenate_audios(wrapper_directory, hidden_directory, splitter_audio, output_directory)
