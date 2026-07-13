"""
Video deduplication via perceptual hashing (pHash).
Extracts frames from output videos, computes pHash, and checks similarity.
"""
import subprocess
import os
import tempfile
from pathlib import Path


def extract_frames(video_path: str, interval: float = 5.0, max_frames: int = 24) -> list:
    """Extract frames at interval seconds from a video. Returns list of frame image paths."""
    temp_dir = tempfile.mkdtemp(prefix="dedup_frames_")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"fps=1/{interval}",
        "-frames:v", str(max_frames),
        "-qscale:v", "2",
        f"{temp_dir}/frame_%03d.jpg",
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)
    frames = sorted(Path(temp_dir).glob("frame_*.jpg"))
    return [str(f) for f in frames]


def compute_phash(image_path: str) -> str:
    """Compute perceptual hash for an image using ffmpeg's signature filter."""
    cmd = [
        "ffmpeg", "-i", image_path,
        "-vf", "signature=detectmode=full:format=xml",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    # Extract signature from stderr (ffmpeg outputs signature info to stderr)
    output = result.stderr
    # Simple approach: use average pixel value as lightweight "hash"
    # For production: use imagehash library (pip install imagehash Pillow)
    cmd2 = [
        "ffmpeg", "-i", image_path,
        "-vf", "scale=8:8,format=gray",
        "-frames:v", "1", "-f", "rawvideo", "pipe:1",
    ]
    result2 = subprocess.run(cmd2, capture_output=True, timeout=10)
    if result2.returncode == 0 and result2.stdout:
        return result2.stdout.hex()
    return output[:64] if output else ""


def hamming_distance(h1: str, h2: str) -> int:
    """Compute Hamming distance between two hash strings."""
    if len(h1) != len(h2):
        max_len = max(len(h1), len(h2))
        h1 = h1.ljust(max_len, '0')
        h2 = h2.ljust(max_len, '0')
    dist = 0
    for c1, c2 in zip(h1, h2):
        xor = ord(c1) ^ ord(c2)
        dist += bin(xor).count('1')
    return dist


def video_fingerprint(video_path: str, sample_count: int = 4) -> list[str]:
    """Generate a fingerprint for a video: list of pHash values from sampled frames."""
    interval = max(1, 30 / sample_count)  # spread across ~30 seconds
    frames = extract_frames(video_path, interval=interval, max_frames=sample_count)
    hashes = []
    for frame in frames:
        h = compute_phash(frame)
        if h:
            hashes.append(h)
    # Cleanup temp frames
    for frame in frames:
        try:
            os.remove(frame)
        except OSError:
            pass
    if frames:
        try:
            os.rmdir(os.path.dirname(frames[0]))
        except OSError:
            pass
    return hashes


def check_duplicate(video1_path: str, video2_path: str, threshold: float = 0.3) -> bool:
    """
    Check if two videos are duplicates.
    Returns True if they are too similar (similarity > threshold).
    """
    fp1 = video_fingerprint(video1_path)
    fp2 = video_fingerprint(video2_path)

    if not fp1 or not fp2:
        return False

    # Compare each hash pair, count matches within tolerance
    matches = 0
    comparisons = 0
    for h1 in fp1:
        for h2 in fp2:
            dist = hamming_distance(h1, h2)
            comparisons += 1
            if dist < 8:  # Hamming distance threshold
                matches += 1

    if comparisons == 0:
        return False

    similarity = matches / comparisons
    return similarity > threshold


def dedup_outputs(video_paths: list[str], similarity_threshold: float = 0.3) -> list[str]:
    """
    Filter a list of video paths, removing near-duplicates.
    Returns paths that are sufficiently unique.
    """
    if len(video_paths) <= 1:
        return video_paths

    # Compute fingerprints for all videos
    fingerprints = {}
    for path in video_paths:
        fp = video_fingerprint(path)
        if fp:
            fingerprints[path] = fp

    keep = [video_paths[0]]
    for path in video_paths[1:]:
        is_dup = False
        fp_current = fingerprints.get(path, [])
        for kept_path in keep:
            fp_kept = fingerprints.get(kept_path, [])
            if not fp_current or not fp_kept:
                continue
            matches = sum(
                1 for h1 in fp_current for h2 in fp_kept
                if hamming_distance(h1, h2) < 8
            )
            total = len(fp_current) * len(fp_kept)
            if total > 0 and matches / total > similarity_threshold:
                is_dup = True
                break
        if not is_dup:
            keep.append(path)

    return keep
