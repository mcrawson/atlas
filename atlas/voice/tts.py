"""Text-to-speech using Piper for ATLAS."""

import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("atlas.voice.tts")


class PiperTTS:
    """Text-to-speech using Piper with British voice."""

    # Default models directory
    DEFAULT_MODELS_DIR = Path.home() / "ai-workspace" / "atlas" / "models" / "piper"

    # British voice models (in order of preference)
    BRITISH_VOICES = [
        "en_GB-alan-medium",
        "en_GB-alba-medium",
        "en_GB-cori-high",
        "en_GB-jenny_dioco-medium",
    ]

    def __init__(
        self,
        voice: str = "en_GB-alan-medium",
        models_dir: Optional[Path] = None,
        speed: float = 1.2,  # 1.0 = normal, higher = faster
    ):
        """Initialize Piper TTS.

        Args:
            voice: Voice model name
            models_dir: Directory containing voice models
            speed: Speech speed multiplier (1.0 = normal, 1.2 = 20% faster)
        """
        self.voice = voice
        self.models_dir = models_dir or self.DEFAULT_MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.speed = speed
        # length_scale is inverse of speed (lower = faster)
        self.length_scale = 1.0 / speed

        self._piper_path = shutil.which("piper")
        self._available = None

    def is_available(self) -> bool:
        """Check if Piper TTS is available."""
        if self._available is None:
            if self._piper_path:
                self._available = True
            else:
                # Try Python piper-tts package
                try:
                    import piper
                    self._available = True
                except ImportError:
                    self._available = False

        return self._available

    def _get_model_path(self) -> Optional[Path]:
        """Get the path to the voice model."""
        # Check for model file
        model_file = self.models_dir / f"{self.voice}.onnx"
        if model_file.exists():
            return model_file

        # Check for model in common locations
        common_paths = [
            Path(f"/usr/share/piper-voices/{self.voice}.onnx"),
            Path.home() / ".local" / "share" / "piper-voices" / f"{self.voice}.onnx",
        ]

        for path in common_paths:
            if path.exists():
                return path

        return None

    def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize speech from text.

        Args:
            text: Text to speak

        Returns:
            WAV audio data or None on failure
        """
        if not self.is_available():
            logger.warning("Piper TTS not available")
            return None

        # Try Python library first (supports speed control)
        result = self._synthesize_python(text)
        if result:
            return result

        # Fall back to CLI if Python fails
        if self._piper_path:
            return self._synthesize_cli(text)

        return None

    def _synthesize_cli(self, text: str) -> Optional[bytes]:
        """Synthesize using piper CLI."""
        model_path = self._get_model_path()

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
                cmd = [self._piper_path]

                if model_path:
                    cmd.extend(["--model", str(model_path)])
                else:
                    cmd.extend(["--model", self.voice])

                cmd.extend(["--output_file", f.name])

                proc = subprocess.run(
                    cmd,
                    input=text,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if proc.returncode != 0:
                    logger.error(f"Piper failed: {proc.stderr}")
                    return None

                return Path(f.name).read_bytes()

        except subprocess.TimeoutExpired:
            logger.error("Piper synthesis timed out")
            return None
        except Exception as e:
            logger.error(f"Piper synthesis failed: {e}")
            return None

    def _synthesize_python(self, text: str) -> Optional[bytes]:
        """Synthesize using piper Python library."""
        try:
            from piper import PiperVoice
            from piper.config import SynthesisConfig
            import wave
            import io

            model_path = self._get_model_path()
            if not model_path:
                logger.error(f"Voice model not found: {self.voice}")
                return None

            voice = PiperVoice.load(str(model_path))

            # Configure synthesis speed (lower length_scale = faster)
            syn_config = SynthesisConfig(
                length_scale=self.length_scale,  # 0.83 = ~20% faster
            )

            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(voice.config.sample_rate)

                # Synthesize returns AudioChunk objects
                for chunk in voice.synthesize(text, syn_config=syn_config):
                    wav.writeframes(chunk.audio_int16_bytes)

            return buffer.getvalue()

        except ImportError:
            logger.warning("piper-tts not installed")
            return None
        except Exception as e:
            logger.error(f"Python Piper synthesis failed: {e}")
            return None

    def speak(self, text: str) -> bool:
        """Synthesize and play speech.

        Args:
            text: Text to speak

        Returns:
            True if successful
        """
        audio_data = self.synthesize(text)
        if not audio_data:
            return False

        return self._play_audio(audio_data)

    def _play_audio(self, audio_data: bytes) -> bool:
        """Play WAV audio data."""
        # Try Python sounddevice first (most reliable for WSL2)
        try:
            import sounddevice as sd
            import numpy as np
            import wave
            import io

            with wave.open(io.BytesIO(audio_data), 'rb') as wav:
                frames = wav.readframes(wav.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767
                sd.play(audio, wav.getframerate())
                sd.wait()
                return True
        except Exception as e:
            logger.warning(f"sounddevice playback failed: {e}")

        # Fallback to paplay (PulseAudio)
        paplay = shutil.which("paplay")
        if paplay:
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(audio_data)
                    f.flush()
                    subprocess.run([paplay, f.name], timeout=30)
                    Path(f.name).unlink(missing_ok=True)
                    return True
            except Exception as e:
                logger.warning(f"paplay failed: {e}")

        # Fallback to aplay (ALSA)
        aplay = shutil.which("aplay")
        if aplay:
            try:
                proc = subprocess.run(
                    [aplay, "-q", "-"],
                    input=audio_data,
                    timeout=30,
                )
                return proc.returncode == 0
            except Exception as e:
                logger.warning(f"aplay failed: {e}")

        return False

    def download_voice(self, voice_name: Optional[str] = None) -> bool:
        """Download a voice model.

        Args:
            voice_name: Voice to download (defaults to self.voice)

        Returns:
            True if successful
        """
        voice = voice_name or self.voice

        # Piper voices are hosted on Hugging Face
        base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB"

        # Extract voice components
        parts = voice.replace("en_GB-", "").split("-")
        if len(parts) >= 2:
            speaker = parts[0]
            quality = parts[1]
        else:
            logger.error(f"Invalid voice format: {voice}")
            return False

        model_url = f"{base_url}/{speaker}/{quality}/{voice}.onnx"
        config_url = f"{base_url}/{speaker}/{quality}/{voice}.onnx.json"

        model_path = self.models_dir / f"{voice}.onnx"
        config_path = self.models_dir / f"{voice}.onnx.json"

        try:
            import urllib.request

            logger.info(f"Downloading {voice} model...")
            urllib.request.urlretrieve(model_url, model_path)

            logger.info(f"Downloading {voice} config...")
            urllib.request.urlretrieve(config_url, config_path)

            logger.info(f"Voice downloaded to {model_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download voice: {e}")
            return False
