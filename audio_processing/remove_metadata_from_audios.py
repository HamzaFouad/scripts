#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio Metadata Removal Script

Purpose:
    Completely strips all metadata, embedded images, and tracing data from audio files
    while preserving the original audio quality. Processes directories recursively.

What gets removed:
    - Embedded images (album artwork, cover art, pictures)
    - Metadata tags (artist, album, title, year, genre, etc.)
    - Origin information (download source, URLs, file origin)
    - ID3 tags (both ID3v1 and ID3v2 completely stripped)
    - Comments and descriptions
    - Attachments and non-audio streams
    - Tracing data (encoder info, creation software, etc.)

What remains:
    - Pure audio data only (no re-encoding, preserves quality)

Supported formats:
    .mp3, .wav, .ogg, .flac, .aac, .m4a, .wma

Features:
    - Recursive directory processing
    - Skips hidden files and non-audio directories
    - Safe processing using temporary files
    - Comprehensive error handling
    - Progress tracking and reporting

Requirements:
    - ffmpeg must be installed and available in PATH

Usage:
    python remove_metadata_from_audios.py
    
    The script will prompt for a directory path and process all audio files found.

Technical details:
    Uses ffmpeg with the following flags:
    - `-map 0:a` : Selects only audio streams (skips embedded images)
    - `-map_metadata -1` : Removes all metadata
    - `-id3v2_version 0` : Strips ID3v2 tags
    - `-write_id3v1 0` : Strips ID3v1 tags
    - `-codec:a copy` : Copies audio without re-encoding (preserves quality)
"""

import os
import subprocess
import tempfile
from pathlib import Path

def remove_metadata_from_audio(input_file_path):
    """
    Removes all metadata from an audio file using ffmpeg and replaces the original file.
    
    Args:
        input_file_path (str): Path to the audio file to process.
    """
    try:
        # Create a temporary file for the processed audio
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(input_file_path)[1], delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Use ffmpeg to remove ALL metadata, embedded images, and tracing data
        # -map_metadata -1 removes all metadata tags
        # -map 0:a selects only audio streams (no pictures/video streams)
        # -codec:a copy copies audio without re-encoding
        # -id3v2_version 0 strips ID3 tags completely
        # This removes: album art, origin info, tags, comments, artwork, etc.
        subprocess.run([
            'ffmpeg',
            '-i', input_file_path,
            '-map', '0:a',           # Map only audio streams (skip images/attachments)
            '-map_metadata', '-1',   # Remove all metadata
            '-codec:a', 'copy',      # Copy audio stream without re-encoding
            '-id3v2_version', '0',   # Strip ID3v2 tags
            '-write_id3v1', '0',     # Strip ID3v1 tags
            '-y',                    # Overwrite output file
            temp_path
        ], check=True, capture_output=True)
        
        # Replace the original file with the processed one
        os.replace(temp_path, input_file_path)
        print(f"Successfully removed metadata from: {input_file_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error processing {input_file_path}: {e}")
        # Clean up temporary file if it exists
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        print(f"Unexpected error processing {input_file_path}: {e}")
        # Clean up temporary file if it exists
        if os.path.exists(temp_path):
            os.remove(temp_path)

def process_directory(directory_path):
    """
    Recursively processes all audio files in a directory and removes metadata.
    
    Args:
        directory_path (str): Path to the directory containing audio files.
    """
    directory = Path(directory_path)
    
    if not directory.exists() or not directory.is_dir():
        print(f"Error: Directory '{directory_path}' does not exist or is not a directory.")
        return
    
    # Supported audio file extensions
    audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma'}
    
    # Count files to process
    audio_files = []
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and common non-audio directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ['__pycache__', 'node_modules', 'venv', 'env']]
        
        for file in files:
            # Skip hidden files and files without extensions
            if file.startswith('.') or '.' not in file:
                continue
                
            file_path = os.path.join(root, file)
            if Path(file).suffix.lower() in audio_extensions:
                audio_files.append(file_path)
    
    if not audio_files:
        print(f"No audio files found in directory: {directory_path}")
        return
    
    print(f"Found {len(audio_files)} audio files to process...")
    
    # Process each audio file
    processed_count = 0
    for audio_file in audio_files:
        try:
            remove_metadata_from_audio(audio_file)
            processed_count += 1
        except Exception as e:
            print(f"Failed to process {audio_file}: {e}")
    
    print(f"\nProcessing complete! Successfully processed {processed_count} out of {len(audio_files)} files.")

def main():
    """Main function to get directory input and process files."""
    directory_path = input("Enter the path of the directory containing audio files: ").strip()
    
    if not directory_path:
        print("Error: No directory path provided.")
        return
    
    # Expand user path if it contains ~
    directory_path = os.path.expanduser(directory_path)
    
    process_directory(directory_path)

if __name__ == "__main__":
    main()
