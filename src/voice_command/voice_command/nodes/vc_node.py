#!/usr/bin/env python3
"""
ROS2 Voice Command Node
-----------------------
Hold SPACEBAR to record → Whisper STT → GPT JSON → std_msgs/String topic

Dependencies:
    pip install openai sounddevice numpy scipy pynput faster-whisper
    sudo apt install libportaudio2 portaudio19-dev
    (faster-whisper only needed if USE_LOCAL_WHISPER = True)
    use before running:
    export PYTHONPATH=/home/david-ross/gitRepos/EECE5552_Course_Project/.venv/lib/python3.12/site-packages:$PYTHONPATH
"""

import json
import queue
import threading
import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import sounddevice as sd
from pynput import keyboard
from openai import OpenAI

# ─────────────────────────────────────────────
# CONFIG — edit these
# ─────────────────────────────────────────────
from voice_command.config.ros2_presets import STD_CFG as ros_settings

OPENAI_API_KEY      = "sk-..."          # Your OpenAI key
USE_LOCAL_WHISPER   = True             # True = faster-whisper (offline), False = OpenAI API
LOCAL_WHISPER_MODEL = "base.en"         # tiny.en | base.en | small.en | medium.en
SAMPLE_RATE         = 16_000            # Hz — Whisper expects 16k
CHANNELS            = 1
ROS_TOPIC           = ros_settings.topic_text_commands
MAX_MESSAGES        = ros_settings.max_messages
TRIGGER_KEY         = keyboard.Key.space

# GPT prompt — customize the JSON schema your robot expects
SYSTEM_PROMPT = """
You are a robot command parser. Convert the user's voice command into a
compact JSON object. Use this schema:
{
  "action":  "<move|rotate|stop|pick|place|say|unknown>",
  "target":  "<object or direction, null if N/A>",
  "value":   "<numeric value or null>",
  "unit":    "<meters|degrees|null>",
  "raw":     "<original transcribed text>"
}
Respond with ONLY the JSON object — no markdown, no explanation.
""".strip()
# ─────────────────────────────────────────────


class WhisperBackend:
    """Swap between OpenAI API Whisper and local faster-whisper."""

    def __init__(self, use_local: bool, api_key: str, local_model: str):
        self.use_local = use_local
        if use_local:
            from faster_whisper import WhisperModel
            print(f"[STT] Loading local faster-whisper model: {local_model}")
            self._model = WhisperModel(local_model, device="cpu", compute_type="int8")
            print("[STT] Local model ready.")
        else:
            self._client = OpenAI(api_key=api_key)
            print("[STT] Using OpenAI Whisper API.")

    def transcribe(self, audio_np: np.ndarray) -> str:
        if self.use_local:
            return self._transcribe_local(audio_np)
        return self._transcribe_api(audio_np)

    def _transcribe_local(self, audio_np: np.ndarray) -> str:
        # faster-whisper expects float32 mono
        segments, _ = self._model.transcribe(audio_np.astype(np.float32), beam_size=5)
        return " ".join(s.text for s in segments).strip()

    def _transcribe_api(self, audio_np: np.ndarray) -> str:
        import io
        from scipy.io import wavfile
        buf = io.BytesIO()
        wavfile.write(buf, SAMPLE_RATE, (audio_np * 32767).astype(np.int16))
        buf.seek(0)
        buf.name = "audio.wav"  # OpenAI needs a filename hint
        result = self._client.audio.transcriptions.create(
            model="whisper-1",
            file=buf,
            response_format="text",
        )
        return result.strip()


class VoiceCommandNode(Node):

    def __init__(self, use_local_whisper=USE_LOCAL_WHISPER, api_key=OPENAI_API_KEY, llm_parse=False, llm_model="gpt-4o-mini",local_whisper_model=LOCAL_WHISPER_MODEL):
        super().__init__("voice_command_node")

        self._use_local_whisper = use_local_whisper
        self._local_whisper_model = local_whisper_model
        self._api_key = api_key
        self._llm_parse = llm_parse
        self._llm_model = llm_model

        self._max_messages = 10

        self._pub = self.create_publisher(String, ROS_TOPIC, self._max_messages)
        self._client = OpenAI(api_key=api_key)
        self._stt = WhisperBackend(use_local_whisper, api_key, local_whisper_model)

        self._audio_q: queue.Queue = queue.Queue()
        self._recording = False
        self._frames: list = []

        self.get_logger().info(
            f"Voice command node ready. "
            f"Hold [{TRIGGER_KEY}] to record. Publishing to [{ROS_TOPIC.value}]."
        )
        self._start_keyboard_listener()

    # ── Audio capture ──────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time, status):
        if self._recording:
            self._frames.append(indata.copy())

    def _start_recording(self):
        self._frames = []
        self._recording = True
        self.get_logger().info("🎙  Recording... (release SPACE to stop)")

    def _stop_and_process(self):
        self._recording = False
        if not self._frames:
            self.get_logger().warn("No audio captured.")
            return
        audio = np.concatenate(self._frames, axis=0).flatten()
        self.get_logger().info(f"Captured {len(audio)/SAMPLE_RATE:.1f}s of audio.")
        # Process in a thread so we don't block the ROS spin
        threading.Thread(target=self._pipeline, args=(audio,), daemon=True).start()

    # ── STT → LLM → publish ───────────────────────────────────────────────

    def _pipeline(self, audio: np.ndarray):
        try:
            # 1. Speech → text
            self.get_logger().info("Transcribing...")
            text = self._stt.transcribe(audio)
            if not text:
                self.get_logger().warn("Transcription returned empty string.")
                return
            self.get_logger().info(f"Transcribed: '{text}'")

            # 2. Text → JSON via GPT
            self.get_logger().info("Parsing command with GPT...")

            if self._llm_parse:
                response = self._client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": text},
                    ],
                    max_tokens=256,
                    temperature=0,
                )
                raw_json = response.choices[0].message.content.strip()

                # 3. Validate JSON
                parsed = json.loads(raw_json)  # raises if GPT hallucinated non-JSON
                payload = json.dumps(parsed, ensure_ascii=False)
            else:
                # If not using LLM parsing, just wrap the raw text in a JSON object
                payload = json.dumps({"raw": text}, ensure_ascii=False)

            # 4. Publish
            msg = String()
            msg.data = payload
            self._pub.publish(msg)
            self.get_logger().info(f"Published → {payload}")

        except json.JSONDecodeError as e:
            self.get_logger().error(f"GPT returned invalid JSON: {e}")
        except Exception as e:
            self.get_logger().error(f"Pipeline error: {e}")

    # ── Keyboard listener ─────────────────────────────────────────────────

    def _start_keyboard_listener(self):
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=self._audio_callback,
        )
        self._stream.start()

        def on_press(key):
            if key == TRIGGER_KEY and not self._recording:
                self._start_recording()

        def on_release(key):
            if key == TRIGGER_KEY and self._recording:
                self._stop_and_process()

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        listener.start()


def main(args=None):
    rclpy.init(args=args)
    node = VoiceCommandNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._stream.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()