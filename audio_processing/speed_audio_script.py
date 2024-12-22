import os
import concurrent.futures
import subprocess
from pathlib import Path

def speed_up_audio(input_file, output_file, speed=1.3):
    """Uses ffmpeg to speed up an audio file by a given factor."""
    try:
        subprocess.run(
            ['ffmpeg', '-i', input_file, '-filter:a', f'atempo={speed}', '-y', output_file],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError as e:
        print(f"Error processing {input_file}: {e}")

def process_audio_file(file_path, output_dir, speed):
    """Speeds up the audio file and saves it to the output directory."""
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    output_file = os.path.join(output_dir, f"{name}_speedup{ext}")
    speed_up_audio(file_path, output_file, speed)
    print(f"Processed {file_path} -> {output_file}")

def extract_speed_from_parent(parent_dir_name, default_speed=1.3):
    """Extracts the speed factor from the parent directory name or returns the default."""
    try:
        return float(parent_dir_name)
    except ValueError:
        return default_speed

def process_directory_recursive(input_dir, speed=1.3, base_output_dir=None):
    """Recursively processes all audio files in a directory and its subdirectories."""
    input_dir = Path(input_dir).resolve()
    
    # Create base output directory if not provided
    if base_output_dir is None:
        base_output_dir = input_dir.parent / "speedup"
    base_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Adjust output directory path
    relative_path = input_dir.relative_to(input_dir.parent)
    output_dir = base_output_dir / relative_path
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_files = list(input_dir.glob("*.mp3")) + list(input_dir.glob("*.wav"))
    if audio_files:
        print(f"Found {len(audio_files)} audio files in {input_dir}. Processing...")
        # Process files concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(process_audio_file, str(file.resolve()), str(output_dir.resolve()), speed)
                for file in audio_files
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error in thread: {e}")

    # Process nested directories
    for sub_dir in input_dir.iterdir():
        if sub_dir.is_dir():
            process_directory_recursive(sub_dir, speed, base_output_dir)

def main():
    """Main function to process all subdirectories."""
    input_directory = input("Enter the path of the main directory containing subdirectories: ").strip()
    if not input_directory:
        print("Error: No directory entered.")
        return

    input_path = Path(input_directory).resolve()
    if not input_path.exists() or not input_path.is_dir():
        print(f"Error: Directory '{input_path}' does not exist or is not a directory.")
        return

    # Process all top-level subdirectories
    for sub_dir in input_path.iterdir():
        if sub_dir.is_dir():
            speed = extract_speed_from_parent(sub_dir.name)
            print(f"Processing directory '{sub_dir}' with speed factor: {speed}")
            process_directory_recursive(sub_dir, speed)

if __name__ == "__main__":
    main()
