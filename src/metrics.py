"""
Custom Prometheus metrics module for model-service.
Implements Counter, Gauge, and Histogram metrics without external libraries.
"""

import os
import threading
from collections import defaultdict


class MetricsRegistry:
    def __init__(self):
        self._lock = threading.Lock()

        # Counter: Total predictions
        self._predictions_total = defaultdict(int)

        # Gauge: Latest confidence score
        self._confidence_score = 0.0
        self._confidence_labels = {}

        # Histogram: Inference duration
        self._inference_buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._inference_counts = defaultdict(lambda: defaultdict(int))
        self._inference_sum = defaultdict(float)
        self._inference_count = defaultdict(int)

        # Version label for A/B testing (read from environment)
        self.version = os.getenv("MODEL_VERSION", "stable")

    def inc_predictions(self, result: str, count: int = 1):
        """Increment prediction counter."""
        with self._lock:
            key = f'result="{result}",version="{self.version}"'
            self._predictions_total[key] += count

    def set_confidence(self, score: float):
        """Set the current confidence score gauge."""
        with self._lock:
            self._confidence_score = score
            self._confidence_labels = {"version": self.version}

    def observe_inference_duration(self, duration: float):
        """Record inference duration in histogram."""
        with self._lock:
            version_key = f'version="{self.version}"'
            self._inference_sum[version_key] += duration
            self._inference_count[version_key] += 1

            for bucket in self._inference_buckets:
                if duration <= bucket:
                    bucket_key = f'le="{bucket}",version="{self.version}"'
                    self._inference_counts[version_key][bucket_key] += 1

            # +Inf bucket (always incremented)
            inf_key = f'le="+Inf",version="{self.version}"'
            self._inference_counts[version_key][inf_key] += 1

    def format_metrics(self) -> str:
        """Format all metrics in Prometheus text exposition format."""
        lines = []

        # Predictions Counter
        lines.append("# HELP model_predictions_total Total number of predictions made by the ML model")
        lines.append("# TYPE model_predictions_total counter")
        with self._lock:
            if self._predictions_total:
                for labels, value in self._predictions_total.items():
                    lines.append(f"model_predictions_total{{{labels}}} {value}")
            else:
                # Output zero value if no predictions yet
                lines.append(f'model_predictions_total{{result="spam",version="{self.version}"}} 0')
                lines.append(f'model_predictions_total{{result="ham",version="{self.version}"}} 0')

        # Confidence Gauge
        lines.append("# HELP model_confidence_score Latest prediction confidence score")
        lines.append("# TYPE model_confidence_score gauge")
        with self._lock:
            if self._confidence_labels:
                labels = ",".join([f'{k}="{v}"' for k, v in self._confidence_labels.items()])
                lines.append(f"model_confidence_score{{{labels}}} {self._confidence_score}")
            else:
                lines.append(f'model_confidence_score{{version="{self.version}"}} 0')

        # Inference Duration Histogram
        lines.append("# HELP model_inference_duration_seconds ML model inference duration in seconds")
        lines.append("# TYPE model_inference_duration_seconds histogram")
        with self._lock:
            if self._inference_counts:
                for version_key, buckets in self._inference_counts.items():
                    # Sort buckets properly (numeric order, +Inf last)
                    sorted_buckets = sorted(
                        buckets.items(), key=lambda x: float("inf") if "+Inf" in x[0] else float(x[0].split('"')[1])
                    )
                    for bucket_key, count in sorted_buckets:
                        lines.append(f"model_inference_duration_seconds_bucket{{{bucket_key}}} {count}")
                    lines.append(
                        f"model_inference_duration_seconds_sum{{{version_key}}} {self._inference_sum[version_key]}"
                    )
                    lines.append(
                        f"model_inference_duration_seconds_count{{{version_key}}} {self._inference_count[version_key]}"
                    )
            else:
                # Output empty histogram
                version_key = f'version="{self.version}"'
                for bucket in self._inference_buckets:
                    lines.append(f'model_inference_duration_seconds_bucket{{le="{bucket}",version="{self.version}"}} 0')
                lines.append(f'model_inference_duration_seconds_bucket{{le="+Inf",version="{self.version}"}} 0')
                lines.append(f"model_inference_duration_seconds_sum{{{version_key}}} 0")
                lines.append(f"model_inference_duration_seconds_count{{{version_key}}} 0")

        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
