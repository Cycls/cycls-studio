"""A call to a renderer that isn't a Cycls deployment, on the wire: JSON and raw bytes, never a
pickle.

    frame  := b"CYS1" · u32 header length · header · the blobs, end to end
    header := {"meta": {…}, "blobs": [[name, size], …]}        (JSON)

Both ends read this one file: engine.py in the agent, and the renderer (engine/modal_fn.py),
which is shipped a copy. Stdlib only.
"""
import json
import struct

MAGIC = b"CYS1"


def encode(meta, blobs=None):
    blobs = {n: v.encode() if isinstance(v, str) else bytes(v) for n, v in (blobs or {}).items()}
    head = json.dumps({"meta": meta, "blobs": [[n, len(v)] for n, v in blobs.items()]},
                      separators=(",", ":")).encode()
    return b"".join([MAGIC, struct.pack(">I", len(head)), head, *blobs.values()])


def decode(data):
    """→ (meta, {name: bytes}); ValueError for anything that isn't a whole frame."""
    if len(data) < 8 or data[:4] != MAGIC:
        raise ValueError("not a Studio frame")
    (n,) = struct.unpack(">I", data[4:8])
    try:
        head = json.loads(data[8:8 + n])
        meta, sizes = head["meta"], head["blobs"]
    except (ValueError, KeyError, TypeError):
        raise ValueError("a Studio frame with a broken header") from None
    at, blobs = 8 + n, {}
    for entry in sizes:
        if not (isinstance(entry, list) and len(entry) == 2 and isinstance(entry[0], str)
                and isinstance(entry[1], int) and 0 <= entry[1] <= len(data) - at):
            raise ValueError("a Studio frame cut short")
        blobs[entry[0]] = data[at:at + entry[1]]
        at += entry[1]
    if at != len(data):
        raise ValueError("a Studio frame with bytes left over")
    return meta, blobs
