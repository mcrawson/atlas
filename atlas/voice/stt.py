"""Speech-to-text using OpenAI Whisper for ATLAS."""

import io
import tempfile
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger("atlas.voice.stt")


class WhisperSTT:
    """Speech-to-text using OpenAI Whisper."""

    def __init__(self, model_size: str = "base.en"):
        """Initialize Whisper STT.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
                        Append .en for English-only models (faster)
        """
        self.model_size = model_size
        self._model = None
        self._available = None

    def _load_model(self):
        """Lazy load the Whisper model."""
        if self._model is None:
            try:
                import whisper
                logger.info(f"Loading Whisper model: {self.model_size}")
                self._model = whisper.load_model(self.model_size)
                self._available = True
            except ImportError:
                logger.warning("whisper not installed. Run: pip install openai-whisper")
                self._available = False
            except Exception as e:
                logger.error(f"Failed to load Whisper: {e}")
                self._available = False

        return self._model

    def is_available(self) -> bool:
        """Check if Whisper is available."""
        if self._available is None:
            self._load_model()
        return self._available

    def transcribe_file(self, audio_path: Path) -> Optional[str]:
        """Transcribe audio from a file.

        Args:
            audio_path: Path to audio file (wav, mp3, etc.)

        Returns:
            Transcribed text or None on failure
        """
        model = self._load_model()
        if not model:
            return None

        try:
            result = model.transcribe(str(audio_path))
            return result["text"].strip()
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    def transcribe_bytes(self, audio_data: bytes, format: str = "wav") -> Optional[str]:
        """Transcribe audio from bytes.

        Args:
            audio_data: Raw audio data
            format: Audio format (wav, mp3, etc.)

        Returns:
            Transcribed text or None on failure
        """
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=True) as f:
            f.write(audio_data)
            f.flush()
            return self.transcribe_file(Path(f.name))


class AudioRecorder:
    """Simple audio recorder using sounddevice."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """Initialize audio recorder.

        Args:
            sample_rate: Recording sample rate (16000 recommended for Whisper)
            channels: Number of audio channels
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self._available = None

    def is_available(self) -> bool:
        """Check if audio recording is available."""
        if self._available is None:
            try:
                import sounddevice
                import numpy
                self._available = True
            except ImportError:
                self._available = False
        return self._available

    def record_until_silence(
        self,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        max_duration: float = 30.0,
    ) -> Optional[bytes]:
        """Record audio until silence is detected.

        Args:
            silence_threshold: RMS threshold for silence detection
            silence_duration: Seconds of silence to stop recording
            max_duration: Maximum recording duration

        Returns:
            WAV audio data or None
        """
        if not self.is_available():
            return None

        try:
            import sounddevice as sd
            import numpy as np
            import wave
            import io

            frames = []
            silence_frames = 0
            frames_per_silence = int(silence_duration * self.sample_rate / 1024)

            def callback(indata, frame_count, time_info, status):
                nonlocal silence_frames
                frames.append(indata.copy())

                # Check for silence
                rms = np.sqrt(np.mean(indata**2))
                if rms < silence_threshold:
                    silence_frames += 1
                else:
                    silence_frames = 0

            max_frames = int(max_duration * self.sample_rate / 1024)

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                blocksize=1024,
                callback=callback,
            ):
                while len(frames) < max_frames:
                    sd.sleep(100)
                    if silence_frames >= frames_per_silence and len(frames) > 10:
                        break

            if not frames:
                return None

            # Convert to WAV
            audio_data = np.concatenate(frames)
            audio_int16 = (audio_data * 32767).astype(np.int16)

            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())

            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Recording failed: {e}")
            return None

    def record_duration(self, duration: float = 5.0) -> Optional[bytes]:
        """Record audio for a fixed duration.

        Args:
            duration: Recording duration in seconds

        Returns:
            WAV audio data or None
        """
        if not self.is_available():
            return None

        try:
            import sounddevice as sd
            import numpy as np
            import wave
            import io

            frames = int(duration * self.sample_rate)
            recording = sd.rec(frames, samplerate=self.sample_rate, channels=self.channels, dtype=np.float32)
            sd.wait()

            # Convert to WAV
            audio_int16 = (recording * 32767).astype(np.int16)

            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())

            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Recording failed: {e}")
            return None
