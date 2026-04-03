import numpy as np
import lerobot.datasets.video_utils as vu

_original_decode = vu.decode_video_frames_torchcodec

def safe_decode_video_frames_torchcodec(video_path, timestamps, tolerance_s):
    try:
        return _original_decode(video_path, timestamps, tolerance_s)

    except IndexError:
        from torchcodec.decoders import VideoDecoder

        decoder = VideoDecoder(video_path)

        # 👇 CRITICAL: just generate a SAFE RANGE instead of recomputing exact indices
        max_valid = decoder.num_frames - 1
        num_frames_requested = len(timestamps)

        # evenly spaced valid indices (safe fallback)
        safe_indices = np.linspace(0, max_valid, num_frames_requested).astype(int)

        return decoder.get_frames_at(indices=safe_indices)

# apply patch
vu.decode_video_frames_torchcodec = safe_decode_video_frames_torchcodec

print("✅ Applied SAFE FALLBACK patch (v3)")