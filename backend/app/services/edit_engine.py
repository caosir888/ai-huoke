"""
FFmpeg-based video editing engine.
Generates edited videos by combining materials with templates.
"""
import os
import subprocess
import random
import json
import tempfile
from pathlib import Path
from dataclasses import dataclass

from app.services.dedup import dedup_outputs


@dataclass
class EditParams:
    material_paths: list[str]
    count: int = 5           # how many output videos
    duration: int = 30       # target duration per video (seconds)
    ratio: str = "9:16"      # aspect ratio
    voice: str = "none"      # female/male/none
    subtitle_style: str = "white_black_border"
    template_id: str = "default"


TEMPLATES = {
    "talk_show": {
        "name": "口播型",
        "structure": [
            {"type": "intro", "weight": 0.1, "min_dur": 2, "max_dur": 3},
            {"type": "talk", "weight": 0.5, "min_dur": 5, "max_dur": 15},
            {"type": "product", "weight": 0.25, "min_dur": 5, "max_dur": 10},
            {"type": "outro", "weight": 0.15, "min_dur": 2, "max_dur": 5},
        ],
    },
    "product_show": {
        "name": "产品展示型",
        "structure": [
            {"type": "hook", "weight": 0.1, "min_dur": 1, "max_dur": 2},
            {"type": "product", "weight": 0.55, "min_dur": 10, "max_dur": 20},
            {"type": "detail", "weight": 0.25, "min_dur": 5, "max_dur": 10},
            {"type": "cta", "weight": 0.1, "min_dur": 2, "max_dur": 3},
        ],
    },
    "fast_cut": {
        "name": "卡点型",
        "structure": [
            {"type": "beat", "weight": 0.2, "min_dur": 0.5, "max_dur": 1},
            {"type": "product", "weight": 0.15, "min_dur": 0.5, "max_dur": 1},
            {"type": "beat", "weight": 0.2, "min_dur": 0.5, "max_dur": 1},
            {"type": "highlight", "weight": 0.25, "min_dur": 1, "max_dur": 2},
            {"type": "beat", "weight": 0.1, "min_dur": 0.3, "max_dur": 0.5},
            {"type": "cta", "weight": 0.1, "min_dur": 2, "max_dur": 3},
        ],
    },
    "mix": {
        "name": "混搭型",
        "structure": [
            {"type": "hook", "weight": 0.1, "min_dur": 1, "max_dur": 2},
            {"type": "talk", "weight": 0.2, "min_dur": 3, "max_dur": 8},
            {"type": "product", "weight": 0.2, "min_dur": 5, "max_dur": 10},
            {"type": "broll", "weight": 0.2, "min_dur": 3, "max_dur": 8},
            {"type": "talk", "weight": 0.15, "min_dur": 2, "max_dur": 5},
            {"type": "cta", "weight": 0.15, "min_dur": 2, "max_dur": 4},
        ],
    },
    "flash": {
        "name": "快闪型",
        "structure": [
            {"type": "text_flash", "weight": 0.3, "min_dur": 0.3, "max_dur": 0.8},
            {"type": "product", "weight": 0.25, "min_dur": 0.5, "max_dur": 1},
            {"type": "text_flash", "weight": 0.2, "min_dur": 0.3, "max_dur": 0.5},
            {"type": "highlight", "weight": 0.15, "min_dur": 0.5, "max_dur": 1},
            {"type": "cta", "weight": 0.1, "min_dur": 1, "max_dur": 2},
        ],
    },
    "before_after": {
        "name": "前后对比型",
        "structure": [
            {"type": "hook", "weight": 0.08, "min_dur": 1, "max_dur": 2},
            {"type": "before", "weight": 0.25, "min_dur": 3, "max_dur": 8},
            {"type": "transition", "weight": 0.04, "min_dur": 0.5, "max_dur": 1},
            {"type": "after", "weight": 0.3, "min_dur": 5, "max_dur": 10},
            {"type": "detail", "weight": 0.2, "min_dur": 3, "max_dur": 8},
            {"type": "cta", "weight": 0.13, "min_dur": 2, "max_dur": 5},
        ],
    },
    "tutorial": {
        "name": "教程型",
        "structure": [
            {"type": "hook", "weight": 0.08, "min_dur": 1, "max_dur": 2},
            {"type": "step1", "weight": 0.2, "min_dur": 3, "max_dur": 8},
            {"type": "step2", "weight": 0.2, "min_dur": 3, "max_dur": 8},
            {"type": "step3", "weight": 0.2, "min_dur": 3, "max_dur": 8},
            {"type": "result", "weight": 0.2, "min_dur": 3, "max_dur": 8},
            {"type": "tip", "weight": 0.12, "min_dur": 2, "max_dur": 5},
        ],
    },
    "review": {
        "name": "测评型",
        "structure": [
            {"type": "hook", "weight": 0.1, "min_dur": 1, "max_dur": 2},
            {"type": "unbox", "weight": 0.15, "min_dur": 3, "max_dur": 6},
            {"type": "feature", "weight": 0.15, "min_dur": 3, "max_dur": 6},
            {"type": "feature", "weight": 0.15, "min_dur": 3, "max_dur": 6},
            {"type": "pros", "weight": 0.15, "min_dur": 3, "max_dur": 6},
            {"type": "cons", "weight": 0.1, "min_dur": 2, "max_dur": 4},
            {"type": "verdict", "weight": 0.2, "min_dur": 3, "max_dur": 8},
        ],
    },
}

# Transitions for variety
TRANSITIONS = ["fade", "wipeleft", "wiperight", "slideup", "slidedown", "dissolve"]


def get_video_duration(path: str) -> float:
    """Get video duration using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format",
        "-show_streams", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def sample_clip_range(duration: float, min_dur: float, max_dur: float) -> tuple[float, float]:
    """Sample a random clip range from a video."""
    max_dur = min(max_dur, duration)
    if duration <= max_dur:
        return 0, duration
    start = random.uniform(0, duration - max_dur)
    clip_dur = random.uniform(min_dur, min(max_dur, duration - start))
    return start, start + clip_dur


def generate_ffmpeg_command(
    materials: list[str],
    output_path: str,
    params: EditParams,
    template_key: str,
    tts_audio_path: str | None = None,
    subtitle_path: str | None = None,
) -> list[str]:
    """Generate FFmpeg command for a single output video."""
    template = TEMPLATES.get(template_key, TEMPLATES["talk_show"])
    total_duration = params.duration

    # Build filter parts and segment clips
    filter_parts = []
    seg_count = len(template["structure"])
    clip_index = 0

    for seg_idx, segment in enumerate(template["structure"]):
        seg_dur = segment["weight"] * total_duration
        seg_min = segment["min_dur"]
        seg_max = min(segment["max_dur"], seg_dur * 1.5)

        mat = random.choice(materials)
        try:
            dur = get_video_duration(mat)
        except Exception:
            dur = 30

        start, end = sample_clip_range(dur, seg_min, seg_max)
        clip_label = f"v{seg_idx}"
        filter_parts.append(
            f"[{seg_idx}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,"
            f"scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[{clip_label}];"
        )

    # Input: one instance of each unique material file
    unique_materials = []
    seen = set()
    # Map each segment to a unique material index
    material_indices = []
    for seg_idx in range(seg_count):
        mat = random.choice(materials)
        if mat not in seen:
            seen.add(mat)
            unique_materials.append(mat)
        material_indices.append(unique_materials.index(mat))

    inputs = []
    for mat in unique_materials:
        inputs.extend(["-i", mat])

    if tts_audio_path and os.path.exists(tts_audio_path):
        inputs.extend(["-i", tts_audio_path])
        audio_idx = len(unique_materials)
    else:
        audio_idx = None

    # Rebuild filter parts with correct input indices
    filter_parts = []
    for seg_idx in range(seg_count):
        seg = template["structure"][seg_idx]
        seg_dur = seg["weight"] * total_duration
        seg_min = seg["min_dur"]
        seg_max = min(seg["max_dur"], seg_dur * 1.5)

        mat_idx = material_indices[seg_idx]
        mat = unique_materials[mat_idx]
        try:
            dur = get_video_duration(mat)
        except Exception:
            dur = 30
        start, end = sample_clip_range(dur, seg_min, seg_max)
        clip_label = f"v{seg_idx}"
        filter_parts.append(
            f"[{mat_idx}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS,"
            f"scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[{clip_label}];"
        )

    # Build concat chain with xfade transitions
    concat_chain = "".join(filter_parts)
    if seg_count == 1:
        concat_chain += "[v0]null[vout];"
    else:
        current = "v0"
        for i in range(1, seg_count):
            tr = random.choice(TRANSITIONS)
            next_label = f"x{i}"
            if i == seg_count - 1:
                next_label = "vout"
            concat_chain += f"[{current}][v{i}]xfade=transition={tr}:duration=0.3[{next_label}];"
            current = next_label

    # Audio
    if audio_idx is not None:
        concat_chain += f"[{audio_idx}:a]atrim=0:{total_duration}[aout];"
    else:
        concat_chain += f"aevalsrc=0:duration={total_duration}[aout];"

    cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", concat_chain]

    if subtitle_path and os.path.exists(subtitle_path):
        cmd.extend(["-vf", f"subtitles={subtitle_path}"])

    cmd.extend([
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(total_duration),
        "-movflags", "+faststart",
        output_path,
    ])

    return cmd


class EditEngine:
    """Main editing engine that orchestrates FFmpeg operations."""

    def __init__(self, work_dir: str = "/tmp/ai_huoke_edits"):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def run_edit_task(
        self, task_id: str, material_paths: list[str], params: dict,
        progress_callback=None,
    ) -> list[str]:
        """Run a full edit task, returning list of output video paths."""
        p = EditParams(
            material_paths=material_paths,
            count=params.get("count", 5),
            duration=params.get("duration", 30),
            ratio=params.get("ratio", "9:16"),
            voice=params.get("voice", "none"),
            subtitle_style=params.get("subtitle_style", "white_black_border"),
            template_id=params.get("template_id", "mix"),
        )

        output_paths = []
        task_dir = self.work_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Pick template based on params
        template_keys = list(TEMPLATES.keys())
        if p.template_id in TEMPLATES:
            primary_template = p.template_id
        else:
            primary_template = random.choice(template_keys)

        for i in range(p.count):
            # Cycle through templates for variety
            tmpl = template_keys[(template_keys.index(primary_template) + i) % len(template_keys)]
            output_path = str(task_dir / f"output_{i:03d}.mp4")

            cmd = generate_ffmpeg_command(
                materials=p.material_paths,
                output_path=output_path,
                params=p,
                template_key=tmpl,
            )

            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=300)
                if os.path.exists(output_path):
                    output_paths.append(output_path)
            except subprocess.CalledProcessError as e:
                print(f"FFmpeg error for output {i}: {e.stderr.decode()[:500]}")
                continue

            if progress_callback:
                progress_callback((i + 1) / p.count * 100)

        # Dedup: remove near-duplicate outputs
        if len(output_paths) > 1:
            output_paths = dedup_outputs(output_paths)

        return output_paths
