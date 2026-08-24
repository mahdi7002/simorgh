import os, subprocess, sys, time
sys.path.insert(0, os.path.expanduser("~/simorgh"))
from core.engine.stt import transcribe_wav

WATCH_DIR = os.path.expanduser("~/simorgh/audio_in")

def convert_to_wav(input_path):
    output_path = input_path + "_converted.wav"
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16",
        output_path
    ], check=True, capture_output=True)
    return output_path

def process_file(filepath):
    if not os.path.isfile(filepath):
        return
    if filepath.endswith(".txt") or "converted" in filepath:
        return
    try:
        wav_path = convert_to_wav(filepath)
        text = transcribe_wav(wav_path)
        out_path = filepath + ".txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✔ {os.path.basename(filepath)} → {os.path.basename(out_path)}: {text[:80]}")
        if os.path.exists(wav_path):
            os.unlink(wav_path)
    except Exception as e:
        print(f"✗ {os.path.basename(filepath)}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for p in sys.argv[1:]:
            process_file(os.path.abspath(p))
    else:
        print(f"👀 پایش پوشه: {WATCH_DIR}")
        before = set(os.listdir(WATCH_DIR))
        while True:
            time.sleep(2)
            after = set(os.listdir(WATCH_DIR))
            new_files = after - before
            for f in new_files:
                process_file(os.path.join(WATCH_DIR, f))
            before = after
