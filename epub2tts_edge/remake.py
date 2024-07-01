import os
import edge_tts
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydub import AudioSegment
from alive_progress import alive_bar
import time
import re
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Define paths
file_path = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/file.txt"
output_dir = "/Users/jacks/Documents/Git/epub2tts-edge/epub2tts_edge/output/"

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Read text file content
with open(file_path, "r") as file_txt:
    file_content = file_txt.read()

def remove_special_characters(input_string):
    return re.sub("[◇]+", "", input_string)

def append_silence(tempfile, duration=1200):
    if not os.path.exists(tempfile) or os.path.getsize(tempfile) == 0:
        if os.path.exists(tempfile):
            os.remove(tempfile)
        return False
    audio = AudioSegment.from_file(tempfile)
    combined = audio + AudioSegment.silent(duration)
    combined.export(tempfile, format="flac")
    return True

async def run_tts(sentence, filename):
    communicate = edge_tts.Communicate(sentence, "en-US-BrianNeural")
    await communicate.save(filename)
    return append_silence(filename)

def read_sentence(sentence, tcount, retries=3):
    filename = os.path.join(output_dir, f"pg{tcount}.flac")
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        return filename
    attempt = 0
    while attempt < retries:
        try:
            asyncio.run(run_tts(sentence, filename))
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return filename
            else:
                print(Fore.YELLOW + "Audio file is empty, retrying...")
        except Exception as e:
            print(Fore.YELLOW + f"Retrying sentence {sentence} / {tcount + 1} due to error: {e}")
        attempt += 1
        time.sleep(1**attempt)
    print(Fore.RED + f"Failed to process sentence {tcount + 1} after {retries} attempts")
    return None

def process_chapter(chapter, chapter_number, total_chapters):
    sentences = [sentence for sentence in chapter.split("\n") if sentence.strip()]
    tcount = sum(len([s for s in total_chapters[i].split("\n") if s.strip()]) for i in range(chapter_number))

    print(Fore.GREEN + f"Starting Chapter {chapter_number + 1}: {sentences[0][:50]}..." if sentences else f"Starting Chapter {chapter_number + 1}: Empty Chapter")

    audio_files = []
    with ThreadPoolExecutor() as executor, alive_bar(len(sentences), title=f"Processing Chapter {chapter_number + 1}") as bar:
        futures = {executor.submit(read_sentence, sentence, tcount + i): i for i, sentence in enumerate(sentences)}
        for future in as_completed(futures):
            try:
                audio_file = future.result()
                if audio_file and os.path.exists(audio_file):
                    audio_files.append(audio_file)
            except Exception as e:
                print(Fore.RED + f"Generated an exception: {e}")
            bar()

    combined_audio = AudioSegment.empty()
    with alive_bar(len(audio_files), title=f"Combining Chapter {chapter_number + 1}") as bar:
        for audio_file in audio_files:
            try:
                combined_audio += AudioSegment.from_file(audio_file)
            except Exception as e:
                print(Fore.RED + f"Error processing file {audio_file}: {e}")
            bar()

    combined_filename = os.path.join(output_dir, f"chapter_{chapter_number + 1}.wav")
    combined_audio.export(combined_filename, format="wav")
    print(Fore.CYAN + f"Combined audio for Chapter {chapter_number + 1} saved as {combined_filename}")

    for audio_file in audio_files:
        os.remove(audio_file)

def read_book(content):
    print(Fore.BLUE + "Content before splitting into chapters:\n", content[:500], "...")
    chapters = content.split("# ")
    print(Fore.BLUE + f"Number of chapters found: {len(chapters)}")
    for chapter_number, chapter in enumerate(chapters):
        print(Fore.BLUE + f"Chapter {chapter_number + 1} content preview:\n", chapter[:200], "...")
        process_chapter(chapter, chapter_number, chapters)

if __name__ == "__main__":
    read_book(file_content)
