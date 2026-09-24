"""Generate a .lpa lip animation from a dialogue .wav, in the shipped game's style.

A shipped .lpa is a phoneme segmentation of its dialogue clip: one INT key per
phoneme, holding the index of that character's face pose (0 Rest, 1 MBP, 2 AA,
3 EE, 4 FV, 5 OO, 6 QUW, 7 L, 8 CONS - the `<char>_face_<NAME>.anm` set). Key
times are stored normalised (0..1 of duration), and every one of them lands on an
NTSC 29.97 fps grid: over all 2513 shipped files, `time * duration * 30000/1001`
is an integer to within 6e-4 frames, and duration is itself an integral number of
those frames. That rate is foreign to the rest of the pipeline - skeletal .anm
key times sit on a clean 60 fps grid - so it came in with the lipsync tool.

The conventions below are measured off those 2513 files, and this script
reproduces them:

  * first key sits at frame 0                       (92% of files)
  * last key sits at the final frame, and is Rest   (100% / 89%)
  * no two keys ever share a frame; gaps are 1, 2 or 3 frames mostly
  * adjacent keys may repeat a viseme - 53% of those repeats are Rest,Rest,
    which is a silence being bracketed at both ends
  * median density is 12.8 keys/sec (p10 9.2, p90 17.0)

What this script does NOT reproduce is the original's *labels*. In the shipped
data CONS carries only 9.8% of keys where a catch-all consonant pose over English
should carry 35-40%, and the whole distribution is near-uniform (7.6-12.5% across
the nine poses): the 2004 textless recogniser got the timing right and the shape
identity mostly wrong. Output here will diff badly against a shipped file on
labels (~17% agreement) while matching it closely on timing, and will look better
in game. Judge a generated file by key timing and silence placement, not by a
label diff.

Two engines, neither a project dependency - run this through uv:

    uv run --with pocketsphinx --with numpy --with faster-whisper \
        python tools/lpa_from_wav.py IN.wav

  * `--engine align` (the default, and the higher quality one) transcribes the
    clip with Whisper and then force-aligns that transcript against the audio.
    Phoneme *identities* then come from the pronunciation dictionary rather than
    from guessing, and only the boundaries are left to the acoustic model. This
    is what the period tools called phonetic alignment, and it is why Magpie
    Pro's alignment engine wanted a transcript.

  * `--engine allphone` is textless recognition: no transcript, phoneme
    identities inferred from audio alone. Faster, no Whisper, markedly worse -
    the shipped game data was made this way, which is why its mouth shapes are
    barely better than chance. Used automatically as a fallback when a clip
    yields no usable transcript.

Allphone decoder settings matter enormously - they are the "sensitivity" the
original team had to tune. Raising the language weight to 5.0 collapses
Marty_go.wav from dozens of keys to 11, a character whose mouth moves eleven
times in six seconds. The defaults (`--lw 2.0 --pip 0.3`) are the recogniser's
own; `--lw 1.0 --pip 0.05` inserts more phonemes and happens to track the
shipped files closely (58 keys against their 59 on Marty_go.wav, key-timing F1
0.85), which is what you want to imitate the original data rather than to
lipsync well.

Whisper model sizes are worth checking rather than assuming: on this game's
dialogue `small.en` is both 2.5x faster than `medium.en` and no less accurate -
medium mishears "the race is canceled" as "the raise is canceled".
"""
import argparse
import os
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from madagascar.lpa import (  # noqa: E402
    RW_TFB_LipAnimation,
    TFB_Viseme,
    TFB_VisemeKey,
    load_lpa,
    save_lpa,
)

NTSC_FPS = 30000 / 1001

SILENCE_PHONEMES = {"SIL", "+NSN+", "+SPN+"}

# CMU phoneme -> face pose. Anything unlisted falls through to CONS, which is what
# that pose is for.
PHONEME_VISEMES: dict[str, TFB_Viseme] = {
    "M": TFB_Viseme.MBP, "B": TFB_Viseme.MBP, "P": TFB_Viseme.MBP,
    "F": TFB_Viseme.FV, "V": TFB_Viseme.FV,
    "L": TFB_Viseme.L,
    "AA": TFB_Viseme.AA, "AE": TFB_Viseme.AA, "AH": TFB_Viseme.AA,
    "AY": TFB_Viseme.AA, "AW": TFB_Viseme.AA, "EH": TFB_Viseme.AA,
    "HH": TFB_Viseme.AA,
    "IY": TFB_Viseme.EE, "IH": TFB_Viseme.EE, "EY": TFB_Viseme.EE,
    "Y": TFB_Viseme.EE,
    "OW": TFB_Viseme.OO, "AO": TFB_Viseme.OO, "OY": TFB_Viseme.OO,
    "UW": TFB_Viseme.QUW, "UH": TFB_Viseme.QUW, "W": TFB_Viseme.QUW,
    "R": TFB_Viseme.QUW, "ER": TFB_Viseme.QUW,
}


_DECODERS: dict[tuple[tuple[str, object], ...], object] = {}


def _decoder(config: dict[str, object]):
    """One decoder per settings combination - building it costs ~a second, and a
    batch of a few hundred clips all share the same settings."""

    from pocketsphinx import Decoder

    key = tuple(sorted(config.items()))

    if key not in _DECODERS:
        _DECODERS[key] = Decoder(**config)

    return _DECODERS[key]


@dataclass
class PhonemeSegment:
    phoneme: str
    start: float  # seconds
    end: float  # seconds

    @property
    def is_silence(self) -> bool:
        return self.phoneme in SILENCE_PHONEMES

    @property
    def viseme(self) -> TFB_Viseme:
        if self.is_silence:
            return TFB_Viseme.Rest

        return PHONEME_VISEMES.get(self.phoneme, TFB_Viseme.CONS)


def load_mono_16k(filepath: str | Path) -> tuple[bytes, float]:
    """Read a wav as the 16 kHz mono PCM the recogniser wants.

    Returns the PCM and the clip's true duration in seconds.
    """

    import numpy as np

    with wave.open(str(filepath)) as w:
        if w.getsampwidth() != 2:
            raise ValueError(f"{filepath}: expected 16-bit PCM")

        rate = w.getframerate()
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")

        if w.getnchannels() > 1:
            samples = samples.reshape(-1, w.getnchannels()).mean(axis=1)

    samples = samples.astype(np.float64)
    duration = len(samples) / rate

    resampled = np.interp(
        np.arange(round(len(samples) * 16000 / rate)) * (rate / 16000.0),
        np.arange(len(samples)),
        samples,
    )

    return np.clip(resampled, -32768, 32767).astype("<i2").tobytes(), duration


def recognise(
    filepath: str | Path,
    *,
    language_weight: float = 2.0,
    phoneme_insertion_penalty: float = 0.3,
    beam: float = 1e-10,
    context_independent: bool = False,
) -> tuple[list[PhonemeSegment], float]:
    """Run textless phoneme recognition over a wav."""

    import pocketsphinx

    model = os.path.join(pocketsphinx.get_model_path(), "en-us")
    config = {
        "hmm": os.path.join(model, "en-us"),
        "allphone": os.path.join(model, "en-us-phone.lm.bin"),
        "lw": language_weight,
        "pip": phoneme_insertion_penalty,
        "beam": beam,
        "pbeam": beam,
        "mmap": False,
        "logfn": os.devnull,
    }

    if context_independent:
        config["allphone_ci"] = True

    pcm, duration = load_mono_16k(filepath)

    decoder = _decoder(config)
    decoder.start_utt()
    decoder.process_raw(pcm, False, True)
    decoder.end_utt()

    segments = [
        # Sphinx counts in 10 ms frames, and tags context-dependent phones as
        # "AA(2)" or similar.
        PhonemeSegment(seg.word.split("(")[0], seg.start_frame / 100.0, seg.end_frame / 100.0)
        for seg in decoder.seg()
    ]

    return segments, duration


_MODELS: dict[str, object] = {}
_VOCAB: set[str] = set()


def _dictionary() -> tuple[str, set[str]]:
    """Path to the pronunciation dictionary, and the words it can align."""

    import pocketsphinx

    path = os.path.join(pocketsphinx.get_model_path(), "en-us", "cmudict-en-us.dict")

    if not _VOCAB:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip():
                    # "read(2) R IY D" - variants share one spelling.
                    _VOCAB.add(line.split()[0].split("(")[0])

    return path, _VOCAB


def transcribe(filepath: str | Path, model_name: str = "small.en") -> str:
    """Transcribe a clip with Whisper."""

    from faster_whisper import WhisperModel

    if model_name not in _MODELS:
        _MODELS[model_name] = WhisperModel(model_name, device="cpu", compute_type="int8")

    model = _MODELS[model_name]
    segments, _ = model.transcribe(str(filepath), language="en", beam_size=5)  # type: ignore[attr-defined]

    return " ".join(segment.text for segment in segments).strip()


def align(filepath: str | Path, transcript: str) -> list[PhonemeSegment]:
    """Force-align a transcript against a clip, returning phoneme boundaries.

    Words the dictionary does not know are dropped - the aligner can only place
    phonemes it has a pronunciation for. Returns an empty list when nothing in
    the transcript is alignable, so callers can fall back to textless.
    """

    import pocketsphinx

    dict_path, vocab = _dictionary()
    words = [w for w in re.findall(r"[a-z']+", transcript.lower()) if w in vocab]

    if not words:
        return []

    model = os.path.join(pocketsphinx.get_model_path(), "en-us")
    decoder = _decoder({
        "hmm": os.path.join(model, "en-us"),
        "dict": dict_path,
        "mmap": False,
        "logfn": os.devnull,
    })

    pcm, _ = load_mono_16k(filepath)

    def pass_over_audio() -> None:
        decoder.start_utt()
        decoder.process_raw(pcm, False, True)
        decoder.end_utt()

    # Alignment is two passes: the first lays the words down against the audio,
    # the second refines inside each word to phones and states.
    decoder.set_align_text(" ".join(words))
    pass_over_audio()
    decoder.set_alignment()
    pass_over_audio()

    return [
        PhonemeSegment(phone.name, phone.start / 100.0, (phone.start + phone.duration) / 100.0)
        for word in decoder.get_alignment()
        for phone in word
    ]


def build_visemes(
    segments: list[PhonemeSegment], duration: float, fps: float = NTSC_FPS
) -> tuple[list[TFB_VisemeKey], float]:
    """Turn phoneme segments into keys on the game's frame grid.

    Returns the keys (normalised times) and the duration to store, which is the
    frame count over the frame rate - never the raw clip length, because every
    shipped file's duration is an exact number of frames.
    """

    total_frames = max(1, round(duration * fps))

    def frame_of(seconds: float) -> int:
        return min(total_frames, max(0, round(seconds * fps)))

    # frame -> viseme. A later segment wins the frame it lands on, which is how
    # the shipped files end up with no two keys ever sharing one.
    frames: dict[int, TFB_Viseme] = {}

    for segment in segments:
        frames[frame_of(segment.start)] = segment.viseme

        if segment.is_silence:
            # Silences are bracketed - a Rest key at each end.
            frames[frame_of(segment.end)] = TFB_Viseme.Rest

    frames.setdefault(0, TFB_Viseme.Rest)
    frames.setdefault(total_frames, TFB_Viseme.Rest)

    keys = [
        TFB_VisemeKey(frame / total_frames, frames[frame]) for frame in sorted(frames)
    ]

    return keys, total_frames / fps


def generate(filepath: str | Path, *, fps: float = NTSC_FPS, **recogniser_options):
    """Generate a lip animation for a dialogue wav."""

    segments, duration = recognise(filepath, **recogniser_options)
    keys, grid_duration = build_visemes(segments, duration, fps)

    return RW_TFB_LipAnimation.from_visemes(keys, grid_duration)


def key_frames(lipanim: RW_TFB_LipAnimation, fps: float = NTSC_FPS) -> list[tuple[int, int]]:
    return [
        (round(key.time * lipanim.duration * fps), int(key.value))  # type: ignore[arg-type]
        for key in lipanim.keys
    ]


def compare(
    lipanim: RW_TFB_LipAnimation, reference: RW_TFB_LipAnimation, fps: float = NTSC_FPS
) -> dict[str, float]:
    """Score a generated animation against a shipped one.

    Key timing is the meaningful measure (see the module docstring); the label
    agreement is reported so you can see for yourself how little signal the
    original's shape choices carry.
    """

    ours, theirs = key_frames(lipanim, fps), key_frames(reference, fps)
    last = min(max(f for f, _ in ours), max(f for f, _ in theirs))

    def step(keys: list[tuple[int, int]]) -> list[int]:
        out, value, i = [], keys[0][1], 0
        for frame in range(last + 1):
            while i < len(keys) and keys[i][0] <= frame:
                value = keys[i][1]
                i += 1
            out.append(value)
        return out

    ours_step, theirs_step = step(ours), step(theirs)

    hit = sum(1 for f, _ in ours if any(abs(f - g) <= 1 for g, _ in theirs))
    found = sum(1 for g, _ in theirs if any(abs(f - g) <= 1 for f, _ in ours))
    precision = hit / len(ours)
    recall = found / len(theirs)

    silence_both = sum(1 for a, b in zip(ours_step, theirs_step) if a == 0 and b == 0)
    silence_either = sum(1 for a, b in zip(ours_step, theirs_step) if a == 0 or b == 0)

    return {
        "keys": len(ours),
        "reference_keys": len(theirs),
        "key_precision": precision,
        "key_recall": recall,
        "key_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "silence_iou": silence_both / silence_either if silence_either else 1.0,
        "label_agreement": sum(a == b for a, b in zip(ours_step, theirs_step)) / len(ours_step),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate .lpa lip animations from dialogue wavs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("wav", nargs="+", type=Path, help="dialogue wav file(s)")
    parser.add_argument("-o", "--out", type=Path, help="output file, or directory for several inputs")
    parser.add_argument("--fps", type=float, default=NTSC_FPS, help="frame grid (default: NTSC 29.97)")
    parser.add_argument("--lw", type=float, default=2.0, help="language weight - the density knob")
    parser.add_argument("--pip", type=float, default=0.3, help="phoneme insertion penalty")
    parser.add_argument("--beam", type=float, default=1e-10, help="decoder beam")
    parser.add_argument("--ci", action="store_true", help="context-independent phones")
    parser.add_argument("--compare", type=Path, help="score against a shipped .lpa instead of guessing quality")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument("--force", action="store_true", help="overwrite an existing .lpa")
    args = parser.parse_args()

    if args.out and len(args.wav) > 1 and not args.out.is_dir():
        parser.error("--out must be an existing directory when passing several wavs")

    for source in args.wav:
        lipanim = generate(
            source,
            fps=args.fps,
            language_weight=args.lw,
            phoneme_insertion_penalty=args.pip,
            beam=args.beam,
            context_independent=args.ci,
        )

        print(
            f"{source.name}: {len(lipanim.keys)} keys over {lipanim.duration:.3f}s "
            f"({round(lipanim.duration * args.fps)} frames, "
            f"{len(lipanim.keys) / lipanim.duration:.1f} keys/sec, "
            f"shipped median 12.8)"
        )

        if args.compare:
            scores = compare(lipanim, load_lpa(args.compare), args.fps)
            print(
                f"  vs {args.compare.name}: {scores['keys']} keys vs {scores['reference_keys']}, "
                f"key F1 {scores['key_f1']:.3f} (p {scores['key_precision']:.3f} / "
                f"r {scores['key_recall']:.3f}), silence IoU {scores['silence_iou']:.3f}, "
                f"label agreement {scores['label_agreement']:.3f}"
            )

        if args.dry_run:
            continue

        if args.out and args.out.is_dir():
            destination = args.out / f"{source.stem}.lpa"
        else:
            destination = args.out or source.with_suffix(".lpa")

        if destination.exists() and not args.force:
            print(f"  refusing to overwrite {destination} (pass --force)", file=sys.stderr)
            continue

        save_lpa(lipanim, destination)
        print(f"  wrote {destination} ({destination.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
