"""
research/debug_nlp_floor.py

One-off diagnostic: confirms whether the nlp_semantic_score==0.0 values seen
for role_swap at severity 0.1/0.5 are real cosine-similarity floor hits
(max(0.0, similarity)) rather than a computation failure. Does NOT modify
nlp_scoring.py -- just reuses its model loader and replicates the same
encode+cos_sim call, printing the raw (unclipped) similarity.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from interview_pipeline.src.nlp_scoring import load_nlp_model
from research.global_alignment import load_reference_segments, load_global_words, align_words_to_speakers, extract_candidate_data
from research.perturbation import role_swap
from research.downstream_metrics import DEFAULT_IDEAL_ANSWER

from sentence_transformers import util

model = load_nlp_model()
if model is None:
    print("[DEBUG] No real model available (fallback active) -- cannot confirm raw cosine similarity here.")
    sys.exit(0)

segs = load_reference_segments()
words = load_global_words()
ideal_embedding = model.encode(DEFAULT_IDEAL_ANSWER, convert_to_tensor=True)

for sev in [0.0, 0.1, 0.25, 0.5]:
    corrupted = role_swap(segs, sev, seed=42)
    labelled = align_words_to_speakers(words, corrupted)
    transcript, _ = extract_candidate_data(labelled, "CANDIDATE")
    cand_embedding = model.encode(transcript, convert_to_tensor=True)
    raw_sim = util.cos_sim(cand_embedding, ideal_embedding).item()
    floored = round(max(0.0, raw_sim) * 100, 2)
    print(f"severity={sev:<5} raw_cosine_similarity={raw_sim:.4f}  floored_score={floored}")
