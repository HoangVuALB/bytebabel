"""Soniox real-time WebSocket transcription + translation engine."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import Callable, Iterator

from soniox import SonioxClient
from soniox.errors import SonioxRealtimeError
from soniox.types import RealtimeSTTConfig, Token, TranslationConfig

from ..logger import get_logger

log = get_logger("transcription.soniox")


def _join_tokens(tokens: list[Token]) -> str:
    """Concatenate token texts."""
    return "".join(t.text for t in tokens)


# Characters that mark a sentence boundary in the original or translation stream.
_SENTENCE_ENDS = frozenset("。.!?！？")


def _build_display_segments(
    orig_sealed: list[str],
    trans_sealed: list[str],
    orig_pending: str,
    trans_pending: str,
) -> list[tuple[str, str]]:
    """Pair sealed sentence segments; append any in-progress partial as the last entry."""
    segs = [
        (
            orig_sealed[i],
            trans_sealed[i] if i < len(trans_sealed) else "",
        )
        for i in range(len(orig_sealed))
    ]
    if orig_pending:
        segs.append((orig_pending, trans_pending))
    return segs


@dataclass
class TranscriptUpdate:
    """Emitted on every token update from Soniox."""

    final_text: str
    non_final_text: str
    # Each entry is (original_sentence, translated_sentence); translation may be ""
    # if it hasn't arrived from Soniox yet.
    segments: list[tuple[str, str]] = field(default_factory=list)
    final_tokens: list[Token] = field(default_factory=list)
    non_final_tokens: list[Token] = field(default_factory=list)
    translated_final_text: str = ""
    translated_non_final_text: str = ""
    error: str | None = None
    finished: bool = False


class SonioxTranscriber:
    """
    Wraps the Soniox real-time WebSocket SDK.

    Usage:
        transcriber = SonioxTranscriber(api_key=..., on_update=callback)
        transcriber.start(audio_capture.get_stream())
        # ... later ...
        transcriber.stop()
    """

    def __init__(
        self,
        api_key: str,
        on_update: Callable[[TranscriptUpdate], None],
        language: str = "auto",
        enable_diarization: bool = False,
        translation_target: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._on_update = on_update
        self._language = language
        self._enable_diarization = enable_diarization
        self._translation_target = translation_target

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._session = None  # active RealtimeSTTSession for force-close
        self._final_tokens: list[Token] = []
        self._non_final_tokens: list[Token] = []
        self._trans_final_tokens: list[Token] = []
        self._trans_non_final_tokens: list[Token] = []
        # Sentence-level segment tracking
        self._orig_segments: list[str] = []  # sealed (sentence-ended) originals
        self._trans_segments: list[str] = []  # sealed translations
        self._orig_pending: list[Token] = []  # accumulating until sentence end
        self._trans_pending: list[Token] = []  # accumulating until sentence end
        self._prev_final_end: int = 0
        self._prev_trans_end: int = 0

    def start(self, audio_stream: Iterator[bytes]) -> None:
        self._stop_event.clear()
        self._final_tokens.clear()
        self._non_final_tokens.clear()
        self._trans_final_tokens.clear()
        self._trans_non_final_tokens.clear()
        self._orig_segments = []
        self._trans_segments = []
        self._orig_pending = []
        self._trans_pending = []
        self._prev_final_end = 0
        self._prev_trans_end = 0
        self._thread = threading.Thread(
            target=self._run,
            args=(audio_stream,),
            daemon=True,
            name="soniox-transcriber",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        # Force-close the active WebSocket session to unblock receive_events()
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None

    def _build_config(self) -> RealtimeSTTConfig:
        language_hints: list[str] = [] if self._language == "auto" else [self._language]
        translation = None
        if self._translation_target:
            translation = TranslationConfig(
                type="one_way",
                target_language=self._translation_target,
            )
        return RealtimeSTTConfig(
            model="stt-rt-v4",
            audio_format="pcm_s16le",
            sample_rate=16000,
            num_channels=1,
            enable_endpoint_detection=False,
            enable_speaker_diarization=self._enable_diarization,
            language_hints=language_hints,
            translation=translation,
        )

    def _run(self, audio_stream: Iterator[bytes]) -> None:
        import os
        import time

        os.environ.setdefault("SONIOX_API_KEY", self._api_key)

        # Shared queue between audio producer and Soniox sender
        audio_q: queue.Queue[bytes | None] = queue.Queue(maxsize=500)

        def _audio_producer() -> None:
            try:
                for chunk in self._guarded_stream(audio_stream):
                    try:
                        audio_q.put(chunk, timeout=1)
                    except queue.Full:
                        pass
            finally:
                audio_q.put(None)  # sentinel

        producer = threading.Thread(
            target=_audio_producer, daemon=True, name="audio-producer"
        )
        producer.start()

        try:
            client = SonioxClient(api_key=self._api_key)
            config = self._build_config()

            while not self._stop_event.is_set():
                log.info(
                    "Connecting to Soniox (model=stt-rt-v4, lang=%s, diarization=%s)",
                    self._language,
                    self._enable_diarization,
                )
                try:
                    self._run_session(client, config, audio_q)
                except RuntimeError as exc:
                    err_msg = str(exc)
                    if "No audio received" in err_msg:
                        if self._stop_event.is_set():
                            break
                        log.warning("No audio received — retrying in 2s")
                        time.sleep(2)
                        continue
                    log.error("Soniox fatal error: %s", exc)
                    raise
                except Exception as exc:
                    if self._stop_event.is_set():
                        break
                    log.warning("Soniox session dropped: %s — reconnecting in 1s", exc)
                    time.sleep(1)
                    continue

                if self._stop_event.is_set():
                    break
                log.info("Soniox server closed session — reconnecting in 1s")
                time.sleep(1)

            log.info(
                "Soniox finished — %d final token(s), %d translated token(s)",
                len(self._final_tokens),
                len(self._trans_final_tokens),
            )
            # Flush any partial sentence that never hit a sentence-end marker
            if self._orig_pending:
                self._orig_segments.append(_join_tokens(self._orig_pending).strip())
                self._orig_pending.clear()
            if self._trans_pending:
                self._trans_segments.append(_join_tokens(self._trans_pending).strip())
                self._trans_pending.clear()
            _final_segments = [
                (
                    self._orig_segments[i],
                    self._trans_segments[i] if i < len(self._trans_segments) else "",
                )
                for i in range(len(self._orig_segments))
            ]
            self._on_update(
                TranscriptUpdate(
                    final_text=_join_tokens(self._final_tokens),
                    non_final_text="",
                    segments=_final_segments,
                    translated_final_text=_join_tokens(self._trans_final_tokens),
                    translated_non_final_text="",
                    finished=True,
                )
            )

        except Exception as exc:
            log.error("Soniox error: %s", exc, exc_info=True)
            if self._orig_pending:
                self._orig_segments.append(_join_tokens(self._orig_pending).strip())
            if self._trans_pending:
                self._trans_segments.append(_join_tokens(self._trans_pending).strip())
            _err_segments = [
                (
                    self._orig_segments[i],
                    self._trans_segments[i] if i < len(self._trans_segments) else "",
                )
                for i in range(len(self._orig_segments))
            ]
            self._on_update(
                TranscriptUpdate(
                    final_text=_join_tokens(self._final_tokens),
                    non_final_text="",
                    segments=_err_segments,
                    translated_final_text=_join_tokens(self._trans_final_tokens),
                    translated_non_final_text="",
                    error=str(exc),
                )
            )

    # Per Soniox docs: send keep_alive at least every 20s when idle.
    # Using 10s is recommended (5–10s is common).
    _KEEPALIVE_INTERVAL = 10  # seconds between keep-alive when no audio

    def _run_session(
        self,
        client: SonioxClient,
        config: RealtimeSTTConfig,
        audio_q: queue.Queue,
    ) -> None:
        """Run a single Soniox session. Returns when the session ends."""
        with client.realtime.stt.connect(config=config) as session:
            self._session = session
            log.info("Soniox WebSocket connected")

            sender_done = threading.Event()

            def _send_audio() -> None:
                chunks_sent = 0
                idle_seconds = 0.0
                try:
                    while not self._stop_event.is_set():
                        try:
                            chunk = audio_q.get(timeout=0.5)
                        except queue.Empty:
                            idle_seconds += 0.5
                            # Per Soniox docs: connection drops after 20s without
                            # audio or keepalive. Send keep_alive every 10s.
                            if idle_seconds >= self._KEEPALIVE_INTERVAL:
                                try:
                                    session.keep_alive()
                                    log.debug(
                                        "Sent keep_alive after %.0fs idle", idle_seconds
                                    )
                                except (SonioxRealtimeError, Exception):
                                    break
                                idle_seconds = 0.0
                            continue
                        idle_seconds = 0.0
                        if chunk is None:
                            audio_q.put(None)  # re-post sentinel for reconnect
                            break
                        try:
                            session.send_bytes(chunk)
                            chunks_sent += 1
                        except (SonioxRealtimeError, Exception) as exc:
                            log.warning(
                                "Sender stopped: %s (sent %d chunks)", exc, chunks_sent
                            )
                            break
                    log.info("Sender finished — sent %d chunk(s)", chunks_sent)
                    try:
                        session.finish()
                    except (SonioxRealtimeError, Exception):
                        pass
                finally:
                    sender_done.set()

            sender = threading.Thread(
                target=_send_audio, daemon=True, name="soniox-sender"
            )
            sender.start()

            for event in session.receive_events():
                if event.error_code:
                    raise RuntimeError(
                        f"Soniox error {event.error_code}: {event.error_message}"
                    )

                if event.tokens:
                    log.debug(
                        "Event: %d token(s), final=%d",
                        len(event.tokens),
                        sum(1 for t in event.tokens if t.is_final),
                    )
                for token in event.tokens:
                    is_translation = (
                        getattr(token, "translation_status", None) == "translation"
                    )
                    if is_translation:
                        if token.is_final:
                            self._trans_final_tokens.append(token)
                        else:
                            self._trans_non_final_tokens.append(token)
                    else:
                        if token.is_final:
                            self._final_tokens.append(token)
                        else:
                            self._non_final_tokens.append(token)

                # ── Build sentence segments (boundary-detected) ───────────
                new_orig = self._final_tokens[self._prev_final_end :]
                new_trans = self._trans_final_tokens[self._prev_trans_end :]
                self._prev_final_end = len(self._final_tokens)
                self._prev_trans_end = len(self._trans_final_tokens)

                if new_orig:
                    self._orig_pending.extend(new_orig)
                    text = _join_tokens(self._orig_pending).rstrip()
                    if text and text[-1] in _SENTENCE_ENDS:
                        self._orig_segments.append(text)
                        self._orig_pending.clear()

                if new_trans:
                    self._trans_pending.extend(new_trans)
                    text = _join_tokens(self._trans_pending).rstrip()
                    if text and text[-1] in _SENTENCE_ENDS:
                        self._trans_segments.append(text)
                        self._trans_pending.clear()

                segments = _build_display_segments(
                    self._orig_segments,
                    self._trans_segments,
                    _join_tokens(self._orig_pending).strip(),
                    _join_tokens(self._trans_pending).strip(),
                )

                self._on_update(
                    TranscriptUpdate(
                        final_text=_join_tokens(self._final_tokens),
                        non_final_text=_join_tokens(self._non_final_tokens),
                        segments=segments,
                        final_tokens=list(self._final_tokens),
                        non_final_tokens=list(self._non_final_tokens),
                        translated_final_text=_join_tokens(self._trans_final_tokens),
                        translated_non_final_text=_join_tokens(
                            self._trans_non_final_tokens
                        ),
                    )
                )
                self._non_final_tokens.clear()
                self._trans_non_final_tokens.clear()

            log.info("receive_events() ended")
            sender_done.wait(timeout=3)
            self._session = None

    def _guarded_stream(self, audio_stream: Iterator[bytes]) -> Iterator[bytes]:
        """Wrap audio stream so it stops when transcriber is stopped."""
        for chunk in audio_stream:
            if self._stop_event.is_set():
                break
            yield chunk
