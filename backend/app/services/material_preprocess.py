"""
Material preprocessing: transcode uploaded videos to uniform format for efficient editing.
"""
import subprocess
import os
from pathlib import Path


def transcode_to_h264(input_path: str, output_dir: str) -> str:
    """Transcode video to H.264/AAC for consistent editing input."""
    os.makedirs(output_dir, exist_ok=True)
    filename = Path(input_path).stem + "_transcoded.mp4"
    output_path = os.path.join(output_dir, filename)

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)
    return output_path


def generate_thumbnail(input_path: str, output_path: str, time_pos: str = "00:00:01"):
    """Generate a thumbnail from video at given time position."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ss", time_pos, "-vframes", "1",
        "-q:v", "2", output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=30)
    return output_path


def get_video_metadata(input_path: str) -> dict:
    """Extract video metadata using ffprobe."""
    import json
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    video_streams = [s for s in data.get("streams", []) if s["codec_type"] == "video"]

    return {
        "duration": float(fmt.get("duration", 0)),
        "size": int(fmt.get("size", 0)),
        "width": video_streams[0]["width"] if video_streams else 0,
        "height": video_streams[0]["height"] if video_streams else 0,
        "codec": video_streams[0].get("codec_name", "") if video_streams else "",
    }
