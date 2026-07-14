"""
Lightweight video mixer using FFmpeg + edge-tts.
Takes multiple video files -> extracts clips -> concatenates -> TTS voiceover -> N outputs.
"""
import subprocess
import random
import sys
import os
import asyncio
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

# Windows Chinese fonts for drawtext (no Fontconfig needed)
WINDOWS_FONTS = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
]
FONT_PATH = None
for f in WINDOWS_FONTS:
    if os.path.exists(f):
        FONT_PATH = f
        break


def _run_ffmpeg(cmd: list[str]) -> bool:
    """Run ffmpeg/ffprobe command. Returns True on success."""
    result = subprocess.run(
        cmd, capture_output=True,
        encoding="utf-8", errors="replace",
    )
    return result.returncode == 0


def _run_ffprobe_output(cmd: list[str]) -> str:
    """Run ffprobe and return stdout as string."""
    result = subprocess.run(
        cmd, capture_output=True,
        encoding="utf-8", errors="replace",
    )
    return result.stdout.strip()


def get_video_duration(filepath: str) -> float:
    """Get video duration in seconds using ffprobe."""
    stdout = _run_ffprobe_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", filepath]
    )
    try:
        return float(stdout)
    except ValueError:
        return 5.0


def trim_clip(input_path: str, output_path: str, start: float, duration: float,
              keep_audio: bool = True) -> bool:
    """Extract a clip from the video. keep_audio=False strips source audio."""
    if Path(output_path).exists():
        return True
    if keep_audio:
        ok = _run_ffmpeg(
            ["ffmpeg", "-y", "-ss", str(start), "-i", input_path,
             "-t", str(duration), "-c:v", "libx264", "-c:a", "aac",
             "-preset", "ultrafast", "-crf", "28", output_path]
        )
        if ok:
            return True
    # No audio fallback
    return _run_ffmpeg(
        ["ffmpeg", "-y", "-ss", str(start), "-i", input_path,
         "-t", str(duration), "-c:v", "libx264",
         "-preset", "ultrafast", "-crf", "28", "-an", output_path]
    )


def concat_clips(clip_paths: list[str], output_path: str) -> bool:
    """Concatenate clips into one video (video only). Returns True on success."""
    concat_file = Path(output_path).with_suffix(".txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{Path(p).absolute().as_posix()}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c:v", "libx264",
        "-preset", "ultrafast", "-crf", "28", "-an", output_path,
    ]
    ok = _run_ffmpeg(cmd)
    concat_file.unlink(missing_ok=True)
    return ok


# Voice presets: {key: (edge_tts_voice, rate, pitch, description)}
VOICE_PRESETS = {
    # === 真人女声 ===
    "female_warm":      ("zh-CN-XiaoxiaoNeural", "+0%", "+0Hz",  "温暖女声"),
    "female_sweet":     ("zh-CN-XiaoxiaoNeural", "+3%", "-3Hz",  "甜美女声"),
    "female_news":      ("zh-CN-XiaoxiaoNeural", "+8%", "+0Hz",  "新闻女声"),
    "female_story":     ("zh-CN-XiaoxiaoNeural", "-8%", "-2Hz",  "故事女声"),
    "female_gentle":    ("zh-CN-XiaoyiNeural",   "-3%", "-2Hz",  "温柔女声"),
    "female_lively":    ("zh-CN-XiaoyiNeural",   "+5%", "+3Hz",  "活泼女声"),
    "female_tw":        ("zh-TW-HsiaoChenNeural","+0%", "+0Hz",  "台湾女声"),
    "female_tw_sweet":  ("zh-TW-HsiaoYuNeural",  "+0%", "+0Hz",  "台湾甜美女声"),
    # === 真人男声 ===
    "male_professional":("zh-CN-YunyangNeural",  "+0%", "+0Hz",  "专业男声"),
    "male_deep":        ("zh-CN-YunyangNeural",  "-5%", "-5Hz",  "深沉男声"),
    "male_sunshine":    ("zh-CN-YunxiNeural",    "+3%", "+0Hz",  "阳光男声"),
    "male_passion":     ("zh-CN-YunjianNeural",  "+5%", "+2Hz",  "激情男声"),
    "male_casual":      ("zh-CN-YunxiaNeural",   "-3%", "+0Hz",  "休闲男声"),
    "male_tw":          ("zh-TW-YunJheNeural",   "+0%", "+0Hz",  "台湾男声"),
    # === 方言特色 ===
    "dialect_liaoning": ("zh-CN-liaoning-XiaobeiNeural", "+0%", "+0Hz", "东北话"),
    "dialect_shaanxi":  ("zh-CN-shaanxi-XiaoniNeural",   "+0%", "+0Hz", "陕西话"),
    # === Legacy compatibility ===
    "female":           ("zh-CN-XiaoxiaoNeural", "+0%", "+0Hz",  "女声"),
    "male":             ("zh-CN-YunyangNeural",  "+0%", "+0Hz",  "男声"),
}


def generate_tts(text: str, output_path: str, voice: str = "female_warm") -> bool:
    """Generate TTS audio from text using edge-tts. Returns True on success."""
    if not text:
        return False
    preset = VOICE_PRESETS.get(voice, VOICE_PRESETS["female_warm"])
    voice_name, rate, pitch, _desc = preset

    try:
        cmd = ["edge-tts", "--text", text, "--voice", voice_name]
        if rate and rate != "+0%":
            cmd.append(f"--rate={rate}")
        if pitch and pitch != "+0Hz":
            cmd.append(f"--pitch={pitch}")
        cmd += ["--write-media", output_path]

        result = subprocess.run(cmd,
            capture_output=True,
            encoding="utf-8", errors="replace",
            timeout=25,
        )
        if result.returncode != 0:
            print(f"[TTS] edge-tts failed: {result.stderr[:200]}")
            return False
        ok = Path(output_path).exists() and Path(output_path).stat().st_size > 0
        if not ok:
            print("[TTS] output file empty or missing")
        return ok
    except subprocess.TimeoutExpired:
        print("[TTS] edge-tts timed out (25s)")
        return False
    except FileNotFoundError:
        print("[TTS] edge-tts not installed")
        return False
    except Exception as e:
        print(f"[TTS] error: {e}")
        return False


def add_audio_and_subtitles(video_path: str, audio_path: str, output_path: str,
                            subtitle_text: str = "") -> bool:
    """Merge video + TTS audio + optional subtitle overlay."""
    cmd = ["ffmpeg", "-y", "-i", video_path]

    # Add audio input (loop to match video duration)
    has_audio = audio_path and Path(audio_path).exists()
    if has_audio:
        cmd += ["-stream_loop", "-1", "-i", audio_path]

    # Build video filter for subtitles
    vf_parts = []
    if subtitle_text and FONT_PATH:
        # Escape special characters for drawtext
        safe_text = subtitle_text.replace("'", "\\'").replace(":", "\\:").replace("\\", "/")
        vf_parts.append(
            f"drawtext=fontfile='{FONT_PATH}':text='{safe_text}':"
            f"fontsize=22:fontcolor=white@0.9:"
            f"x=(w-text_w)/2:y=h-th-40:"
            f"box=1:boxcolor=black@0.4:boxborderw=6"
        )

    if has_audio:
        cmd += ["-c:v", "libx264", "-c:a", "aac",
                "-preset", "ultrafast", "-crf", "28",
                "-shortest"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"]

    if vf_parts:
        cmd.insert(-8 if has_audio else -5, "-vf")
        cmd.insert(-8 if has_audio else -5, ",".join(vf_parts))

    cmd.append(output_path)

    ok = _run_ffmpeg(cmd)
    # Fallback: try without subtitles
    if not ok and vf_parts:
        # Remove -vf and its argument
        new_cmd = [c for c in cmd if c != ",".join(vf_parts) and c != "-vf"]
        ok = _run_ffmpeg(new_cmd)
    return ok


def get_resolution(ratio: str) -> tuple[int, int]:
    """Convert ratio string to (width, height) for landscape/portrait/square."""
    mapping = {
        "9:16": (1080, 1920),
        "16:9": (1920, 1080),
        "1:1": (1080, 1080),
    }
    return mapping.get(ratio, (1920, 1080))


def image_to_clip(image_path: str, output_path: str, duration: float = 4.0,
                 effect: str = "kenburns", width: int = 1920, height: int = 1080) -> bool:
    """
    Convert a still image to a video clip with motion effect.
    - effect: "kenburns" = zoom 1.0→1.15 with random pan, "fade" = static with fade in/out
    Returns True on success.
    """
    if Path(output_path).exists():
        return True

    fps = 30
    total_frames = int(duration * fps)

    if effect == "kenburns":
        # Random pan direction: slight horizontal or vertical drift
        pan_x = random.choice([
            "iw/2-(iw/zoom/2)",                          # center
            "iw/4-(iw/zoom/4)",                          # left-ish
            "3*iw/4-(iw/zoom*3/4)",                       # right-ish
        ])
        pan_y = random.choice([
            "ih/2-(ih/zoom/2)",                          # center
            "ih/3-(ih/zoom/3)",                          # top-ish
            "2*ih/3-(ih/zoom*2/3)",                       # bottom-ish
        ])

        zoom_expr = f"zoompan=z='min(zoom+0.0015,1.15)':d={total_frames}:x='{pan_x}':y='{pan_y}':s={width}x{height}"
        vf = f"{zoom_expr},fps={fps},format=yuv420p"
    else:
        # Fade in/out — scale to target resolution so all clips share the same size
        fade_in_dur = min(0.5, duration / 3)
        fade_out_start = duration - min(0.5, duration / 3)
        scale = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        vf = f"{scale},fade=t=in:st=0:d={fade_in_dur},fade=t=out:st={fade_out_start}:d={duration - fade_out_start},fps={fps},format=yuv420p"

    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-t", str(duration), "-pix_fmt", "yuv420p",
        "-an", output_path,
    ]
    ok = _run_ffmpeg(cmd)
    if not ok:
        print(f"[MIXER] image_to_clip failed for {Path(image_path).name}")
    return ok


def mix_images(image_paths: list[str], output_dir: str, count: int = 5,
               total_duration: float = 30.0, subtitle: str = "",
               voice: str = "none", ratio: str = "16:9") -> list[str]:
    """
    Pure image-to-video mixing mode (for 图文成片 template).
    Each image becomes a 4s clip (random Ken Burns or fade effect).
    Clips are shuffled, concatenated, with optional TTS + subtitles.

    Returns list of output file paths (absolute).
    """
    tgt_w, tgt_h = get_resolution(ratio)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not image_paths:
        return []

    use_tts = subtitle and voice != "none"
    clip_duration = 4.0  # per user requirement: 4 seconds per image
    clips_dir = out_dir / "clips"
    clips_dir.mkdir(exist_ok=True)

    # Generate a pool of image clips
    all_clips = []
    for idx, img_path in enumerate(image_paths):
        # 75% Ken Burns, 25% fade
        effect = "fade" if random.random() < 0.25 else "kenburns"
        clip_path = str(clips_dir / f"img_clip_{idx:03d}.mp4")
        if image_to_clip(img_path, clip_path, clip_duration, effect, tgt_w, tgt_h):
            all_clips.append(clip_path)

    if len(all_clips) < 1:
        return []

    # Calculate how many clips needed to fill total_duration
    clips_needed = max(1, int(total_duration / clip_duration))

    outputs = []
    used_combos = set()
    for i in range(count):
        # Build a sequence: repeat/shuffle clips to fill duration
        selected = []
        for _ in range(clips_needed):
            selected.append(random.choice(all_clips))
        random.shuffle(selected)

        combo_key = tuple(selected)
        if combo_key in used_combos and len(all_clips) > 2:
            # Try to get a different combo
            for _attempt in range(20):
                random.shuffle(selected)
                combo_key = tuple(selected)
                if combo_key not in used_combos:
                    break
        used_combos.add(combo_key)

        if selected:
            _make_output(clips_dir, selected, out_dir, i, subtitle, voice, use_tts, outputs, tgt_w, tgt_h)

    # Cleanup clip temp files
    for c in clips_dir.iterdir():
        c.unlink(missing_ok=True)
    try:
        clips_dir.rmdir()
    except OSError:
        pass

    # Dedup
    if len(outputs) > 1:
        try:
            from app.services.dedup import dedup_outputs
            before = len(outputs)
            outputs = dedup_outputs(outputs)
            if len(outputs) < before:
                print(f"[MIXER] Image dedup: removed {before - len(outputs)} near-duplicate videos")
        except ImportError:
            pass

    return outputs


def mix_videos(input_files: list[str], output_dir: str, count: int = 5,
               total_duration: float = 30.0, subtitle: str = "",
               voice: str = "none", template: str = "mix",
               ratio: str = "16:9") -> list[str]:
    """
    Mix multiple videos/images into N different outputs.
    - template: "mix" (video mixing) or "image_to_video" (图片转视频)
    - total_duration: target video duration in seconds
    - subtitle: copywriting text (used for TTS + on-screen subtitles)
    - voice: "none" / "female" / "male"
    - ratio: "9:16" / "16:9" / "1:1"

    Returns list of output file paths (absolute).
    """
    tgt_w, tgt_h = get_resolution(ratio)

    if template == "image_to_video":
        return mix_images(input_files, output_dir, count, total_duration, subtitle, voice, ratio)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if len(input_files) < 1:
        return []

    use_tts = subtitle and voice != "none"
    keep_audio = not use_tts

    # Calculate clip duration: aim for 5-8 clips to reach total_duration
    target_clips = max(3, min(8, int(total_duration / 5)))
    clip_dur = total_duration / target_clips

    if len(input_files) == 1:
        dur = get_video_duration(input_files[0])
        if dur <= 0:
            return []
        # Single video: extract multiple segments
        clip_dur = min(clip_dur, dur * 0.3, 15.0)
        if clip_dur < 1.0:
            clip_dur = min(3.0, dur * 0.3)
        clips_dir = out_dir / "clips"
        clips_dir.mkdir(exist_ok=True)

        outputs = []
        for i in range(count):
            clip_paths = []
            needed = target_clips
            for j in range(needed):
                max_start = max(0, dur - clip_dur)
                start = (i * needed + j) * clip_dur * 0.7
                if start > max_start:
                    start = random.uniform(0, max_start)
                clip_path = str(clips_dir / f"clip_{i}_{j}.mp4")
                if trim_clip(input_files[0], clip_path, start, clip_dur, keep_audio):
                    clip_paths.append(clip_path)

            if clip_paths:
                _make_output(clips_dir, clip_paths, out_dir, i, subtitle, voice, use_tts, outputs)
        # Dedup single-file outputs
        if len(outputs) > 1:
            try:
                from app.services.dedup import dedup_outputs
                outputs = dedup_outputs(outputs)
            except ImportError:
                pass
        return outputs

    # Multiple videos
    video_info = []
    for f in input_files:
        d = get_video_duration(f)
        if d > 0.5:
            video_info.append((f, d))

    if not video_info:
        return []

    clips_dir = out_dir / "clips"
    clips_dir.mkdir(exist_ok=True)

    # For each video: calculate clip duration so we get enough segments
    avg_source_dur = sum(d for _, d in video_info) / len(video_info)
    per_video_clips = max(2, target_clips // len(video_info))
    clip_dur = min(clip_dur, avg_source_dur * 0.5, 20.0)
    if clip_dur < 1.0:
        clip_dur = min(5.0, avg_source_dur * 0.5)

    all_clips = []
    for vi, (fpath, dur) in enumerate(video_info):
        max_clips_possible = max(1, int(dur / clip_dur))
        num_clips = min(per_video_clips, max_clips_possible)
        for ci in range(num_clips):
            max_start = max(0, dur - clip_dur)
            start = ci * clip_dur * 0.8 if (ci + 1) * clip_dur <= dur else random.uniform(0, max_start)
            clip_path = str(clips_dir / f"clip_{vi}_{ci}.mp4")
            if trim_clip(fpath, clip_path, start, clip_dur, keep_audio):
                all_clips.append(clip_path)

    if len(all_clips) < 2:
        return []

    # Select enough clips to reach total_duration
    clips_needed = max(2, min(len(all_clips), target_clips))

    outputs = []
    used_combos = set()
    for i in range(count):
        for _attempt in range(20):
            random.shuffle(all_clips)
            selected = all_clips[:clips_needed]
            combo_key = tuple(sorted(selected))
            if combo_key not in used_combos:
                used_combos.add(combo_key)
                break

        if selected:
            _make_output(clips_dir, selected, out_dir, i, subtitle, voice, use_tts, outputs, tgt_w, tgt_h)

    # Clean up individual clips
    for c in clips_dir.iterdir():
        c.unlink(missing_ok=True)
    try:
        clips_dir.rmdir()
    except OSError:
        pass

    # Dedup: remove near-duplicate outputs before returning
    if len(outputs) > 1:
        try:
            from app.services.dedup import dedup_outputs
            before = len(outputs)
            outputs = dedup_outputs(outputs)
            if len(outputs) < before:
                print(f"[MIXER] Dedup: removed {before - len(outputs)} near-duplicate videos")
        except ImportError:
            pass

    return outputs


def check_dedup_quality(video_paths: list[str]) -> dict:
    """Check deduplication quality of output videos. Returns quality report dict."""
    try:
        from app.services.dedup import compute_quality_report
        return compute_quality_report(video_paths)
    except ImportError:
        return {
            "unique_count": len(video_paths), "total_count": len(video_paths),
            "dedup_ratio": 1.0, "avg_similarity": 0.0, "passed": True,
            "details": []
        }


def _make_output(clips_dir, clip_paths, out_dir, i, subtitle, voice, use_tts, outputs,
                 tgt_w: int = 1920, tgt_h: int = 1080):
    """Internal: resize clips to target resolution, concat, add TTS+subtitles, produce one output video."""
    # Resize all clips to target resolution so concat is safe
    scale = f"scale={tgt_w}:{tgt_h}:force_original_aspect_ratio=decrease,pad={tgt_w}:{tgt_h}:(ow-iw)/2:(oh-ih)/2"
    sized_clips = []
    for j, cp in enumerate(clip_paths):
        sized = str(Path(clips_dir) / f"sized_{i}_{j}.mp4")
        if not Path(sized).exists():
            ok = _run_ffmpeg([
                "ffmpeg", "-y", "-i", cp,
                "-vf", f"{scale},fps=30,format=yuv420p",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-an", sized
            ])
            if ok and Path(sized).exists() and Path(sized).stat().st_size > 0:
                sized_clips.append(sized)
            else:
                sized_clips.append(cp)  # fallback to original
        else:
            sized_clips.append(sized)

    merged = str(clips_dir / f"merged_{i}.mp4")
    if not concat_clips(sized_clips, merged):
        print(f"[MIXER] concat failed for output {i+1}")
        return

    out_path = str(out_dir / f"output_{i + 1:03d}.mp4")

    if use_tts:
        tts_audio = str(clips_dir / f"tts_{i}.mp3")
        sub_text = subtitle[:200]
        print(f"[MIXER] Generating TTS audio for output {i+1}...")
        tts_ok = generate_tts(sub_text, tts_audio, voice)
        if tts_ok:
            print(f"[MIXER] TTS OK, merging audio + subtitles...")
            add_audio_and_subtitles(merged, tts_audio, out_path, sub_text)
        else:
            print(f"[MIXER] TTS failed, falling back to video-only with subtitles")
            add_audio_and_subtitles(merged, "", out_path, sub_text)
        # Clean up temp files
        for tmp in [merged, tts_audio]:
            try:
                os.remove(tmp)
            except OSError:
                pass
    else:
        Path(out_path).unlink(missing_ok=True)
        os.rename(merged, out_path)

    if Path(out_path).exists():
        outputs.append(str(Path(out_path).absolute()))
    else:
        print(f"[MIXER] Output file missing: {out_path}")


def make_thumbnail(video_path: str) -> str | None:
    """Extract the first frame as a JPEG thumbnail. Returns thumbnail path or None."""
    thumb_path = Path(video_path).with_suffix(".thumb.jpg")
    ok = _run_ffmpeg(
        ["ffmpeg", "-y", "-i", video_path, "-vframes", "1", "-q:v", "3",
         str(thumb_path)]
    )
    return str(thumb_path.absolute()) if ok and thumb_path.exists() else None
