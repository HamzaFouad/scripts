import os
import subprocess
import sys

def split_audio(input_path, start_time, output_path=None, end_time=None):
    """
    Splits audio from a specific moment (start time) to the end or to a specified end time.

    Args:
        input_path (str): Path to the input audio file.
        start_time (str): Start time in format HH:MM:SS or MM:SS (e.g., "01:09:30" or "69:30").
        output_path (str, optional): Path to save the output audio file. 
                                     If not provided, will be generated from input filename.
        end_time (str, optional): End time in format HH:MM:SS or MM:SS. 
                                  If not provided, extracts from start_time to the end of the audio.
    """
    # Validate input file exists and is a file (not a directory)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not os.path.isfile(input_path):
        raise ValueError(f"Input path is a directory, not a file: {input_path}")

    # Generate output path if not provided
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        ext = os.path.splitext(input_path)[1]
        # Sanitize start_time for filename (replace colons with underscores)
        safe_start_time = start_time.replace(":", "_")
        output_path = os.path.join(
            os.path.dirname(input_path),
            f"{base_name}_from_{safe_start_time}{ext}"
        )

    # Build ffmpeg command
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", input_path,
        "-ss", start_time,  # Start time
        "-y",  # Overwrite output file if it exists
    ]

    # Add end time if provided
    if end_time:
        ffmpeg_cmd.extend(["-to", end_time])

    # Add output path
    ffmpeg_cmd.append(output_path)

    # Execute ffmpeg command
    try:
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        print(f"Audio split successfully!")
        print(f"Input: {input_path}")
        print(f"Start time: {start_time}")
        if end_time:
            print(f"End time: {end_time}")
        print(f"Output: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error splitting audio: {e}")
        if e.stderr:
            print(f"FFmpeg error: {e.stderr}")
        raise

def parse_time_input(time_str):
    """
    Validates and normalizes time input format.
    
    Args:
        time_str (str): Time string in format HH:MM:SS, MM:SS, or SS
        
    Returns:
        str: Normalized time string in HH:MM:SS format
    """
    parts = time_str.split(":")
    if len(parts) == 1:
        # Just seconds
        return f"00:00:{parts[0].zfill(2)}"
    elif len(parts) == 2:
        # MM:SS
        return f"00:{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    elif len(parts) == 3:
        # HH:MM:SS
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
    else:
        raise ValueError(f"Invalid time format: {time_str}. Use HH:MM:SS, MM:SS, or SS")

# Example usage
if __name__ == "__main__":
    # You can modify these values or use command line arguments
    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        start = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else None
        end = sys.argv[4] if len(sys.argv) > 4 else None
    else:
        # Default example
        input_file = input("Enter the path to the input audio file: ").strip()
        start = input("Enter the start time (HH:MM:SS or MM:SS): ").strip()
        output_file = input("Enter the output path (or press Enter for auto-generated): ").strip() or None
        end = input("Enter the end time (HH:MM:SS or MM:SS, or press Enter for end of file): ").strip() or None

    # Normalize time format
    start = parse_time_input(start)
    if end:
        end = parse_time_input(end)

    split_audio(input_file, start, output_file, end)
