# Scripts Repository

A collection of utility scripts for audio processing and file management tasks.

## 📁 Project Structure

```
.
├── audio_processing/          # Audio manipulation scripts
│   ├── concat_audios.py
│   ├── convert_to_mp3.py
│   ├── merge_all_audios_within_directory.py
│   ├── remove_metadata_from_audios.py
│   ├── speed_audio_script.py
│   └── split_long_audios_to_smaller_ones.py
├── files/                     # File management scripts
│   ├── add_file_prefix_script.py
│   ├── add_file_prefix_with_order.py
│   ├── change_file_prefix_script.py
│   ├── filename_translation_script.py
│   ├── order_directory_files.py
│   └── rename_files.py
├── finalize.py               # Finalization script
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
└── README.md               # This file
```

## 🚀 Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- ffmpeg (for audio processing scripts)

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd scripts
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install ffmpeg (if not already installed):**
   
   **macOS:**
   ```bash
   brew install ffmpeg
   ```
   
   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get update
   sudo apt-get install ffmpeg
   ```
   
   **Windows:**
   Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

5. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```env
   OPENAI_API_KEY=your-openai-api-key-here
   ```

## 📝 Scripts Overview

### Audio Processing Scripts

#### `speed_audio_script.py`
Speed up audio files in subdirectories. Automatically extracts speed factors from directory names.
```bash
python audio_processing/speed_audio_script.py
```

#### `convert_to_mp3.py`
Convert audio files to MP3 format.
```bash
python audio_processing/convert_to_mp3.py
```

#### `concat_audios.py`
Concatenate multiple audio files into one.
```bash
python audio_processing/concat_audios.py
```

#### `merge_all_audios_within_directory.py`
Merge all audio files within a directory.
```bash
python audio_processing/merge_all_audios_within_directory.py
```

#### `split_long_audios_to_smaller_ones.py`
Split long audio files into smaller chunks (e.g., 30-minute segments).
```bash
python audio_processing/split_long_audios_to_smaller_ones.py
```

#### `remove_metadata_from_audios.py`
Remove metadata from audio files.
```bash
python audio_processing/remove_metadata_from_audios.py
```

### File Management Scripts

#### `filename_translation_script.py`
Translate Arabic filenames to Franco-Arabic (Arabic written with English letters).
- **Requires:** OpenAI API key in `.env` file
- **Usage:** Update the `directory_to_scan` variable in the script, then run:
  ```bash
  python files/filename_translation_script.py
  ```

#### `add_file_prefix_script.py`
Add a prefix to all files in a directory.
```bash
python files/add_file_prefix_script.py
```

#### `add_file_prefix_with_order.py`
Add a prefix with ordering to files in a directory.
```bash
python files/add_file_prefix_with_order.py
```

#### `change_file_prefix_script.py`
Change the prefix of files (e.g., change "01_" to "04_04_").
```bash
python files/change_file_prefix_script.py
```

#### `order_directory_files.py`
Order files in a directory.
```bash
python files/order_directory_files.py
```

#### `rename_files.py`
Rename files in a directory.
```bash
python files/rename_files.py
```

### Utility Scripts

#### `finalize.py`
Finalization script for organizing and processing files.
```bash
python finalize.py
```

## 🔐 Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# OpenAI API Configuration (required for filename_translation_script.py)
OPENAI_API_KEY=your-openai-api-key-here
```

**Note:** Never commit your `.env` file to version control. The `.env.example` file serves as a template.

## 📦 Dependencies

All required Python packages are listed in `requirements.txt`:

- `openai` - OpenAI API client (for filename translation)
- `python-dotenv` - Load environment variables from `.env` file

## 🔧 Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Make sure you've installed all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **ffmpeg not found**: Ensure ffmpeg is installed and available in your PATH. Test with:
   ```bash
   ffmpeg -version
   ```

3. **OpenAI API errors**: 
   - Verify your API key is correctly set in `.env`
   - Ensure you have sufficient API credits
   - Check your internet connection

4. **Permission errors**: Some scripts may require write permissions. Run with appropriate permissions if needed.