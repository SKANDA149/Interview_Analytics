"""
research_visual_gating/profiling.py

Timing/CPU/RAM instrumentation isolated to whatever code block is measured
(callers are responsible for only wrapping the visual/VAD stage they mean
to measure - e.g. VAD time is logged separately from YuNet time, never
folded together, per the design doc's "do not include VAD time inside the
visual runtime" requirement).

Wall time:    time.perf_counter() (monotonic, unaffected by system clock
              adjustments).
CPU-seconds:  psutil.Process().cpu_times() sampled before/after and
              summed (user + system) - this repo's existing research/
              scripts only ever measured wall time and peak RSS, never
              CPU-seconds, so this is new, not reused.
Peak RSS:     resource.getrusage(RUSAGE_SELF).ru_maxrss - on Linux this is
              already a monotonic high-water mark in KiB for the whole
              process since start, so no background sampling thread is
              needed for the peak figure.
Mean RSS:     best-effort - a background thread samples psutil RSS at a
              fixed interval for the duration of the measured block and
              reports the mean. Optional (per spec: "if feasible");
              disabled by default because it adds a thread per run and
              this pilot cares most about peak RSS and CPU-seconds.
"""
from __future__ import annotations

import resource
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

import psutil


@dataclass
class Measurement:
    wall_time_s: float = 0.0
    cpu_seconds: float = 0.0
    peak_rss_mb: float = 0.0
    mean_rss_mb: float = None
    rss_samples_mb: list = field(default_factory=list)


@contextmanager
def measure(sample_rss: bool = False, sample_interval_s: float = 0.05):
    """Usage:
        with measure() as m:
            ... code to time ...
        print(m.wall_time_s, m.cpu_seconds, m.peak_rss_mb)
    """
    proc = psutil.Process()
    m = Measurement()

    stop_flag = threading.Event()
    sampler_thread = None
    if sample_rss:
        def _sample():
            while not stop_flag.is_set():
                try:
                    m.rss_samples_mb.append(proc.memory_info().rss / (1024 * 1024))
                except Exception:
                    pass
                stop_flag.wait(sample_interval_s)
        sampler_thread = threading.Thread(target=_sample, daemon=True)
        sampler_thread.start()

    cpu_before = proc.cpu_times()
    t0 = time.perf_counter()
    try:
        yield m
    finally:
        elapsed = time.perf_counter() - t0
        cpu_after = proc.cpu_times()
        cpu_seconds = (cpu_after.user - cpu_before.user) + (cpu_after.system - cpu_before.system)

        if sampler_thread is not None:
            stop_flag.set()
            sampler_thread.join(timeout=1.0)

        m.wall_time_s = round(elapsed, 4)
        m.cpu_seconds = round(cpu_seconds, 4)
        m.peak_rss_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 2)
        if m.rss_samples_mb:
            m.mean_rss_mb = round(sum(m.rss_samples_mb) / len(m.rss_samples_mb), 2)
