# Model provenance - research_visual_gating

## Silero VAD
- File: `models/silero_vad/silero_vad.onnx`
- Source: extracted from the official PyPI wheel `silero-vad==6.2.1`
  (`silero_vad/data/silero_vad.onnx` inside the wheel), NOT downloaded
  loose from a random mirror.
- sha256: 1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3
- We did NOT `pip install silero-vad` as a runtime dependency (it hard-
  imports torch+torchaudio even on its onnx path, and default `pip install
  torch` pulls a multi-GB CUDA toolkit). `research_visual_gating/vad.py` is
  a from-scratch NumPy + ONNX Runtime reimplementation of
  `silero_vad.utils_vad.get_speech_timestamps`'s windowing/state-machine
  logic, ported by reading that module's source at v6.2.1, then verified
  against known small synthetic tone/silence signals in
  `research_visual_gating/tests/test_vad.py`.

## YuNet
- File: `models/yunet/face_detection_yunet_2023mar.onnx` (already present
  in the repo, used unmodified by `interview_pipeline/src/visual_presence.py`).
- This study reuses `interview_pipeline.src.visual_presence.detect_faces`
  and its frozen `FACE_CONFIDENCE_THRESHOLD = 0.6` unchanged. BlazePose /
  pose detection from that module is NOT used here (face-presence only,
  per approved scope).
