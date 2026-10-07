# The Studio worker's parent side, outside Blender:  uv run --with pytest pytest test_render_fn.py
# A stand-in `blender` runs the real worker.py over one fake op. POSIX only (pipes and select).
import os
import signal
import sys
import time

import pytest

import render_fn

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the worker's pipes and select need POSIX")

BLENDER = """#!{python}
import sys
script = sys.argv[sys.argv.index("-P") + 1]
exec(compile(open(script).read(), script, "exec"), {{"__name__": "__main__", "__file__": script}})
"""

OPS = '''
import os, signal, time


def _op(job, jobdir):
    p = job["params"]
    if p.get("say"):
        os.write(1, b"x" * p["say"])                 # Blender's chatter, straight to the log
    if p.get("die"):
        os.kill(os.getpid(), signal.SIGSEGV)
    hog = b"x" * p.get("hog", 0)                     # resident memory, held while it sleeps
    time.sleep(p.get("sleep", 0))
    with open(os.path.join(jobdir, "made.bin"), "wb") as f:
        f.write(b"bytes")
    return {"pid": os.getpid()}


OPS = {"evaluate": _op}
'''


@pytest.fixture
def studio(tmp_path, monkeypatch):
    """_studio("evaluate", params) against the stand-in: unsandboxed, everything under tmp_path."""
    blender = tmp_path / "bin" / "blender"
    blender.parent.mkdir()
    blender.write_text(BLENDER.format(python=sys.executable))
    blender.chmod(0o755)
    monkeypatch.setenv("PATH", f"{blender.parent}{os.pathsep}{os.environ['PATH']}")
    root = str(tmp_path / "studio")
    for name, value in (("ROOT", root), ("JOBS_ROOT", root + "/jobs"), ("CACHE_ROOT", root + "/cache"),
                        ("LOG", root + "/blender.log"), ("STUDIO_BPY_SRC", OPS)):
        monkeypatch.setattr(render_fn, name, value)
    for name, value in (("_cycls_sandbox", "none"), ("_cycls_blender", None), ("_cycls_scene_ns", None)):
        monkeypatch.setattr(sys, name, value, raising=False)
    yield lambda **params: render_fn._studio("evaluate", {}, None, params)
    if sys._cycls_blender:
        render_fn._kill(sys._cycls_blender)


def test_a_job_answers_with_its_result_and_files_and_the_worker_stays_warm(studio):
    r = studio()
    assert r["ok"] and r["spawned"] and r["files"] == {"made.bin": b"bytes"}
    again = studio()
    assert not again["spawned"] and again["result"]["pid"] == r["result"]["pid"]


def test_a_crash_is_reported_as_one_and_the_next_job_gets_a_fresh_worker(studio):
    assert studio(die=True) == {"ok": False, "error": f"Blender crashed during evaluate (exit {-signal.SIGSEGV})"}
    assert studio()["spawned"]


def test_a_hung_job_is_stopped_at_its_timeout(studio, monkeypatch):
    monkeypatch.setitem(render_fn.OP_TIMEOUT, "evaluate", 1)
    assert studio(sleep=30) == {"ok": False, "error": "evaluate took longer than 1s — stopped"}
    monkeypatch.setitem(render_fn.OP_TIMEOUT, "evaluate", 60)
    assert studio()["spawned"]


def test_a_job_that_eats_the_instances_memory_is_stopped_while_it_can_still_answer(studio, monkeypatch):
    monkeypatch.setattr(render_fn, "MEM_MAX", 150 * 2**20)
    began = time.monotonic()
    r = studio(hog=400 * 2**20, sleep=30)
    assert not r["ok"] and r["error"].startswith("evaluate ran out of memory (0.")
    assert time.monotonic() - began < 10                        # not its sleep, nor the op's timeout
    after = studio()
    assert after["spawned"] and 0 < after["mem_mb"] < 150       # a fresh worker, and what it holds is told


def test_the_log_is_emptied_past_its_cap_under_a_running_worker(studio, monkeypatch):
    monkeypatch.setattr(render_fn, "LOG_MAX", 10_000)
    pids = {studio(say=30_000)["result"]["pid"] for _ in range(4)}
    assert len(pids) == 1                                       # one worker, appending all along
    assert os.path.getsize(render_fn.LOG) == 30_000            # the last job's output, not all four


def test_a_new_worker_starts_the_log_over(studio):
    studio(say=1000)
    render_fn._kill(sys._cycls_blender)
    studio()
    assert os.path.getsize(render_fn.LOG) == 0
