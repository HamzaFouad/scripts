import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
import re


def translate_filename(full_filename):
    system_prompt = (
        "You are TranslateAI. Your task is to translate Arabic filenames to arabic Franco with english letters. also, use numbers like 3 for ع and 2 for ء and 7 for ح and 8 for غ and 5 for خ"
        "You MUST keep any numeric parts that indicate the file order or structure UNCHANGED. For example, if the "
        "filename is '01_02_الملف.mp3', the '01_02' part should stay exactly the same, and only the Arabic part ('الملف') should be translated."
        "return the filename directly without additional introduction or explanation. so i use this filename to rename my file right away and make it automated"
    )

    user_prompt = f"Here is the filename: {full_filename}"

    try:
        response = client.chat.completions.create(model="gpt-4",  # Correct model name, should be "gpt-4" or "gpt-3.5-turbo"
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
        max_tokens=100,
        temperature=0.7)
        # Extract the translation from the assistant's response
        translation = response.choices[0].message.content.strip()
        return translation

    except Exception as e:
        print(f"Error with OpenAI API: {e}")
        return None


def rename_files_in_directory(directory):
    for filename in os.listdir(directory):
        full_path = os.path.join(directory, filename)

        # Only process files (skip directories)
        if os.path.isfile(full_path):
            print(f"Processing filename: {filename}")

            # Send the full filename to OpenAI to handle the translation
            translated_filename = translate_filename(filename)

            if translated_filename:
                new_full_path = os.path.join(directory, translated_filename)

                # Rename the file
                os.rename(full_path, new_full_path)
                print(f"Renamed '{filename}' to '{translated_filename}'")
            else:
                print(f"Failed to translate the filename: {filename}")


# Main execution
if __name__ == "__main__":
    # Define the directory to scan
    directory_to_scan = './00_ebthal'  # Replace with the path of your directory

    # Call the rename function
    rename_files_in_directory(directory_to_scan)
