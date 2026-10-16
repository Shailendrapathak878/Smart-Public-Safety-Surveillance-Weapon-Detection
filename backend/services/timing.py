import time


def timing_log(marker: str, event_id: str):
    print(f"[TIMING] {marker} event_id={event_id} perf_ns={time.perf_counter_ns()}", flush=True)