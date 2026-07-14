"""
Video deduplication via perceptual hashing (pHash).
Extracts frames from output videos, computes pHash using imagehash, and checks similarity.
"""
import subprocess
import os
import tempfile
from pathlib import Path

try:
    from PIL import Image
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False


def extract_frames(video_path: str, interval: float = 5.0, max_frames: int = 4) -> list[str]:
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
    """Compute perceptual hash for an image. Returns hex string or empty string on failure."""
    if not HAS_IMAGEHASH:
        return _fallback_hash(image_path)
    try:
        img = Image.open(image_path)
        return str(imagehash.phash(img))
    except Exception:
        return _fallback_hash(image_path)


def _fallback_hash(image_path: str) -> str:
    """Fallback: scale to 8x8 grayscale and return hex of raw pixels."""
    cmd = [
        "ffmpeg", "-i", image_path,
        "-vf", "scale=8:8,format=gray",
        "-frames:v", "1", "-f", "rawvideo", "pipe:1",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=10)
    if result.returncode == 0 and result.stdout:
        return result.stdout.hex()
    return ""


def hamming_distance(h1: str, h2: str) -> int:
    """Compute Hamming distance between two hex hash strings."""
    # Convert hex strings to binary integers for efficient comparison
    try:
        if h1 == h2:
            return 0
        # Pad to equal length
        max_len = max(len(h1), len(h2))
        h1 = h1.ljust(max_len, '0')
        h2 = h2.ljust(max_len, '0')
        # Compare byte by byte
        dist = 0
        for c1, c2 in zip(h1, h2):
            xor = ord(c1) ^ ord(c2)
            dist += bin(xor).count('1')
        return dist
    except Exception:
        return 999


def video_fingerprint(video_path: str, sample_count: int = 4) -> list[str]:
    """Generate a fingerprint for a video: list of pHash values from sampled frames."""
    duration = _get_duration(video_path)
    interval = max(1, duration / (sample_count + 1))
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


def _get_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 30.0


def check_duplicate(video1_path: str, video2_path: str, threshold: float = 0.3) -> bool:
    """
    Check if two videos are duplicates.
    Returns True if they are too similar (similarity > threshold).
    """
    fp1 = video_fingerprint(video1_path)
    fp2 = video_fingerprint(video2_path)
    if not fp1 or not fp2:
        return False
    matches = 0
    comparisons = 0
    for h1 in fp1:
        for h2 in fp2:
            comparisons += 1
            if hamming_distance(h1, h2) < 8:
                matches += 1
    if comparisons == 0:
        return False
    return matches / comparisons > threshold


def dedup_outputs(video_paths: list[str], similarity_threshold: float = 0.3) -> list[str]:
    """Filter a list of video paths, removing near-duplicates. Returns unique paths."""
    if len(video_paths) <= 1:
        return video_paths
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


def compute_quality_report(video_paths: list[str]) -> dict:
    """
    Compute deduplication quality report for a set of videos.
    Returns: {
        "unique_count": int, "total_count": int, "dedup_ratio": float (0-1),
        "avg_similarity": float (0-1), "passed": bool, "details": [...]
    }
    A dedup_ratio closer to 1.0 means all videos are unique (good).
    A high avg_similarity means videos are too similar (bad).
    """
    n = len(video_paths)
    if n <= 1:
        return {
            "unique_count": n, "total_count": n, "dedup_ratio": 1.0,
            "avg_similarity": 0.0, "passed": True, "details": []
        }

    # Compute fingerprints
    fingerprints = {}
    for path in video_paths:
        fp = video_fingerprint(path)
        if fp:
            fingerprints[path] = fp

    # Compare all pairs
    similarities = []
    details = []
    for i in range(n):
        for j in range(i + 1, n):
            fp_i = fingerprints.get(video_paths[i], [])
            fp_j = fingerprints.get(video_paths[j], [])
            if not fp_i or not fp_j:
                continue
            matches = sum(
                1 for h1 in fp_i for h2 in fp_j
                if hamming_distance(h1, h2) < 8
            )
            total = len(fp_i) * len(fp_j)
            sim = matches / total if total > 0 else 0
            similarities.append(sim)
            if sim > 0:
                details.append({
                    "pair": [Path(video_paths[i]).name, Path(video_paths[j]).name],
                    "similarity": round(sim, 3),
                })

    avg_similarity = sum(similarities) / len(similarities) if similarities else 0
    # unique_count estimate: videos with avg pairwise similarity below 0.3
    unique_count = len(dedup_outputs(video_paths, similarity_threshold=0.3))
    dedup_ratio = unique_count / n if n > 0 else 1.0
    passed = dedup_ratio >= 0.6  # at least 60% unique

    return {
        "unique_count": unique_count,
        "total_count": n,
        "dedup_ratio": round(dedup_ratio, 2),
        "avg_similarity": round(avg_similarity, 3),
        "passed": passed,
        "details": details[:10],  # limit detail items
    }
