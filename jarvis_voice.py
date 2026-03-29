import sounddevice as sd
import queue
import json
import vosk
import requests
import pyttsx3

# -----------------------------
# SETTINGS
# -----------------------------
MODEL_PATH = "/Users/akhileshwaddankeri/ai-bot/vosk-model"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"

DEVICE_ID = 2   # 🔥 TRY 2 (Mac mic) OR 0

# -----------------------------
# INIT
# -----------------------------
q = queue.Queue()
model = vosk.Model(MODEL_PATH)
samplerate = 16000

engine = pyttsx3.init()
engine.setProperty('rate', 180)

is_listening = False
memory = []
MAX_MEMORY = 5

# -----------------------------
# FUNCTIONS
# -----------------------------
def speak(text):
    print("\n🔊 Jarvis:", text)
    engine.say(text)
    engine.runAndWait()

def stop_voice():
    engine.stop()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

# -----------------------------
# STREAMING AI
# -----------------------------
def ask_ai_stream(prompt):
    global memory

    memory.append(f"User: {prompt}")
    memory = memory[-MAX_MEMORY:]

    full_prompt = "\n".join(memory) + "\nAI:"

    full_answer = ""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": full_prompt,
                "stream": True
            },
            stream=True,
            timeout=60
        )

        print("\n🤖 Jarvis:", end=" ", flush=True)

        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("response", "")

                print(token, end="", flush=True)
                full_answer += token

        print()

    except Exception as e:
        full_answer = "Error connecting to AI"
        print("\n❌", e)

    memory.append(f"AI: {full_answer}")
    memory = memory[-MAX_MEMORY:]

    return full_answer

# -----------------------------
# AUDIO FIX (MAC STABLE)
# -----------------------------
sd.default.device = DEVICE_ID

stream = sd.RawInputStream(
    samplerate=16000,
    blocksize=8000,
    dtype='int16',
    channels=1,
    device=(DEVICE_ID, None),   # 🔥 FIX
    callback=callback
)

# -----------------------------
# START
# -----------------------------
print("🎤 Jarvis PRO MAX... Say 'hey jarvis'")

try:
    stream.start()
except Exception as e:
    print("❌ Mic error:", e)
    print("👉 Try changing DEVICE_ID (0 or 2)")
    exit()

rec = vosk.KaldiRecognizer(model, samplerate)

# -----------------------------
# MAIN LOOP
# -----------------------------
while True:
    try:
        data = q.get()

        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").lower()

            if text.strip() == "":
                continue

            print("\n👂 Heard:", text)

            # 🛑 STOP (interrupt speech)
            if any(word in text for word in ["stop", "top", "shop"]):
                stop_voice()
                print("🛑 Stopped")
                continue

            # 🎯 WAKE WORD (robust)
            if "jar" in text:
                is_listening = True
                speak("Yes, I'm listening")
                continue

            # 🤖 RESPONSE
            if is_listening:
                print("🧑 You:", text)

                answer = ask_ai_stream(text)
                speak(answer)

                is_listening = False

    except KeyboardInterrupt:
        print("\n👋 Exiting Jarvis...")
        break

    except Exception as e:
        print("⚠️ Error:", e)
        continue
