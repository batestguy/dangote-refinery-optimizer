# ruff: noqa: E501 — the ASS style template has fixed, unbreakable format lines
"""Assemble the demo video from recorded frames + beat cards.

Pipeline (spec §9):
  frames/*/frames.json + cards/*.png  ->  per-block 1920x1080 60 fps clips
  music: [55.000, 121.128] looped 3x with 1 s crossfades, trimmed to 150 s,
         faded out at 147 s, loudness-normalised to -14 LUFS
  captions: CAPTIONS -> captions.ass (burned in) + demo_v1.srt (sidecar)
  concat -> burn -> mux AAC 192k -> +faststart

Usage:
    PYTHONUTF8=1 uv run python scripts/build_demo_video.py
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from demo_timeline import BLOCKS, CAPTIONS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "demo"
FRAMES = OUT / "frames"
CARDS = OUT / "cards"
CLIPS = OUT / "clips"
AUDIO_SRC = ROOT / "Odeal - Blur (Official Lyric Video) - Odeal.mp3"

FPS = 60
W, H = 1920, 1080
TOTAL = 150.0
LOOP_IN, LOOP_OUT = 55.000, 121.128
NAVY = "0x171d64"


def run(args: list[str], label: str, cwd: pathlib.Path | None = None) -> None:
    print(f"[build] {label}", flush=True)
    proc = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr[-3000:])
        raise SystemExit(f"ffmpeg failed: {label}")


def ff(*args: str) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args]


def probe_duration(path: pathlib.Path) -> float:
    exe = shutil.which("ffprobe") or "ffprobe.exe"
    try:
        proc = subprocess.run(
            [
                exe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(proc.stdout.strip())
    except Exception as exc:  # noqa: BLE001 — metadata only, never fail the build
        print(f"[build] ffprobe unavailable ({type(exc).__name__}); duration unverified")
        return 0.0


def load_frames(block_id: str) -> tuple[list[pathlib.Path], float]:
    meta_path = FRAMES / block_id / "frames.json"
    if not meta_path.exists():
        raise SystemExit(f"missing {meta_path} — run the capture phase first")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    frames = [pathlib.Path(f["path"]) for f in meta["list"]]
    if not frames:
        raise SystemExit(f"no frames for {block_id}")
    stamps = [f["ts"] for f in meta["list"]]
    span = floats_span(stamps)
    return frames, span


def floats_span(stamps: list[float]) -> float:
    if len(stamps) < 2:
        return 0.0
    return max(stamps) - min(stamps)


def build_screencast_clip(block: dict, manifest: dict) -> pathlib.Path:
    """Frames are a VFR screencast: static stretches emit no frames at all, so each
    frame is given its real duration and the last one is held (tpad) to fill the
    slot. Assuming a uniform fps here would silently distort the pacing."""
    bid, dur = block["id"], float(block["dur"])
    frames, span = load_frames(bid)
    stamps = json.loads((FRAMES / bid / "frames.json").read_text(encoding="utf-8"))["list"]
    ts = [f["ts"] for f in stamps]
    deltas = [min(2.5, max(0.008, b - a)) for a, b in zip(ts, ts[1:], strict=True)]
    tail = deltas[-1] if deltas else 1 / 25
    durations = deltas + [tail]
    src_dur = sum(durations)

    lines = [
        f"file '{frame.as_posix()}'\nduration {d:.4f}"
        for frame, d in zip(frames, durations, strict=True)
    ]
    lines.append(f"file '{frames[-1].as_posix()}'")
    list_path = CLIPS / f"{bid}_frames.txt"
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Compress over-long footage instead of truncating it (the capture can run
    # slightly long); gentle 1.1-1.3x is invisible at these scroll speeds.
    speed = min(1.6, max(1.0, src_dur / dur))
    vf = []
    if speed > 1.01:
        vf.append(f"setpts=PTS/{speed:.6f}")
    vf += [
        f"scale={W}:{H}:flags=lanczos",
        "setsar=1",
        f"fps={FPS}",
        "tpad=stop_mode=clone:stop_duration=3",
        "format=yuv420p",
    ]
    clip = CLIPS / f"{bid}.mp4"
    if clip.exists() and clip.stat().st_size > 0:
        print(f"[build] {bid}: reusing existing clip")
        return clip
    run(
        ff(
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-vf",
            ",".join(vf),
            "-t",
            f"{dur:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(clip),
        ),
        f"{bid}: {len(frames)} frames -> {dur:.1f}s (source {src_dur:.1f}s, speed {speed:.2f}x)",
    )
    entry = manifest.get("blocks", {}).get(bid, {})
    if entry.get("solve_wait_s"):
        print(
            f"[build]   {bid}: real solve wait {entry['solve_wait_s']}s "
            f"compressed {speed:.2f}x"
            + (f", runtime {entry['runtime_text']}s" if entry.get("runtime_text") else "")
        )
    return clip


def build_still_clip(block: dict) -> pathlib.Path:
    bid, dur = block["id"], float(block["dur"])
    clip = CLIPS / f"{bid}.mp4"
    if clip.exists() and clip.stat().st_size > 0:
        print(f"[build] {bid}: reusing existing clip")
        return clip
    if block["kind"] == "card":
        src = CARDS / f"{block['card']}.png"
        if not src.exists():
            raise SystemExit(f"missing card {src}")
        run(
            ff(
                "-loop",
                "1",
                "-framerate",
                str(FPS),
                "-i",
                str(src),
                "-t",
                f"{dur:.3f}",
                "-vf",
                f"scale={W}:{H},setsar=1,fps={FPS},format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "16",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(FPS),
                "-an",
                str(clip),
            ),
            f"{bid}: card {block['card']} -> {dur:.1f}s",
        )
    else:  # fade to navy
        run(
            ff(
                "-f",
                "lavfi",
                "-i",
                f"color=c={NAVY}:s={W}x{H}:r={FPS}:d={dur:.3f}",
                "-vf",
                "format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "16",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(FPS),
                "-an",
                str(clip),
            ),
            f"{bid}: fade -> {dur:.1f}s",
        )
    return clip


def build_audio() -> pathlib.Path:
    if not AUDIO_SRC.exists():
        raise SystemExit(f"missing music source: {AUDIO_SRC}")
    seg = OUT / "music_seg.m4a"
    run(
        ff(
            "-ss",
            f"{LOOP_IN}",
            "-to",
            f"{LOOP_OUT}",
            "-i",
            str(AUDIO_SRC),
            "-af",
            "afade=t=in:d=0.05",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            str(seg),
        ),
        f"music: extract {LOOP_IN}-{LOOP_OUT}s",
    )
    looped = OUT / "music_looped.m4a"
    run(
        ff(
            "-i",
            str(seg),
            "-i",
            str(seg),
            "-i",
            str(seg),
            "-filter_complex",
            "[0][1]acrossfade=d=1:c1=tri:c2=tri[a];[a][2]acrossfade=d=1:c1=tri:c2=tri[b];"
            f"[b]atrim=0:{TOTAL},asetpts=N/SR/TB,"
            f"afade=t=out:st={TOTAL - 3}:d=3,loudnorm=I=-14:TP=-1:LRA=11[aout]",
            "-map",
            "[aout]",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            str(looped),
        ),
        f"music: loop 3x, trim {TOTAL}s, fade + loudnorm -14 LUFS",
    )
    return looped


def ass_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def srt_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Arial,46,&H00FFFFFF,&H00FFFFFF,&H00202020,&H66641D17,0,0,0,0,100,100,0,0,3,14,0,2,150,150,72,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_captions() -> tuple[pathlib.Path, pathlib.Path]:
    ass_lines, srt_blocks = [], []
    t0 = 0.0
    idx = 1
    for blk in BLOCKS:
        for offset, dur, text in CAPTIONS.get(blk["id"], []):
            start, end = t0 + offset, t0 + offset + dur
            ass_lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Cap,,0,0,0,,{text}")
            srt_blocks.append(f"{idx}\n{srt_time(start)} --> {srt_time(end)}\n{text}\n")
            idx += 1
        t0 += float(blk["dur"])
    ass_path = OUT / "captions.ass"
    srt_path = OUT / "demo_v1.srt"
    ass_path.write_text(ASS_HEAD + "\n".join(ass_lines) + "\n", encoding="utf-8")
    srt_path.write_text("\n".join(srt_blocks), encoding="utf-8")
    print(f"[build] captions: {idx - 1} lines -> {ass_path.name}, {srt_path.name}")
    return ass_path, srt_path


def main() -> int:
    CLIPS.mkdir(parents=True, exist_ok=True)
    manifest = {}
    man_path = OUT / "record_manifest.json"
    if man_path.exists():
        manifest = json.loads(man_path.read_text(encoding="utf-8"))

    clips = []
    for blk in BLOCKS:
        if blk["kind"] in ("card", "fade"):
            clips.append(build_still_clip(blk))
        else:
            clips.append(build_screencast_clip(blk, manifest))

    concat_list = OUT / "concat.txt"
    concat_list.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")

    audio = build_audio()
    ass_path, srt_path = write_captions()

    # cwd=OUT and a bare filename: the `ass` filter parses ':' as an option
    # separator, so an absolute Windows path (D:/...) makes it read the path as
    # original_size and fail.
    final = OUT / "demo_v1.mp4"
    run(
        ff(
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-i",
            str(audio),
            "-vf",
            f"ass={ass_path.name}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            "-t",
            f"{TOTAL:.3f}",
            final.name,
        ),
        f"final: burn captions + mux audio -> {final.name}",
        cwd=OUT,
    )

    dur = probe_duration(final)
    size_mb = final.stat().st_size / 1e6
    print(f"[build] done: {final}  {dur:.2f}s  {size_mb:.1f} MB  (target {TOTAL}s)")
    print(f"[build] sidecar: {srt_path}")
    (OUT / "build.json").write_text(
        json.dumps(
            {
                "file": str(final),
                "duration_s": round(dur, 3),
                "size_mb": round(size_mb, 2),
                "fps": FPS,
                "resolution": f"{W}x{H}",
                "captions": len([1 for b in BLOCKS for _ in CAPTIONS.get(b["id"], [])]),
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
