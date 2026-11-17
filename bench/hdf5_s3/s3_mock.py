#!/usr/bin/env python3
"""Minimal read-only S3-compatible server for HDF5 ROS3 layout experiments.

    s3_mock.py --root DIR --bucket NAME [--port 9123] [--delay-ms 0]
               [--mbps 0] [--log requests.jsonl]

Serves DIR/<key> as s3://NAME/<key> over plain HTTP, path-style
(http://127.0.0.1:PORT/NAME/<key>), anonymous only. Supports HEAD and GET with
a single "Range: bytes=a-b" header, which is all the HDF5 ROS3 VFD needs.

--delay-ms adds a fixed delay before each response (time to first byte), and
--mbps caps each response's transfer rate, so a run can mimic the latency and
per-stream bandwidth measured against real S3. Every request is appended to
--log as one JSON line (method, key, range start/end, bytes sent, seconds).
"""
import argparse
import json
import os
import re
import threading
import time
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()


def make_handler(root, bucket, delay_s, bps, log):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):  # quiet
            pass

        def _path(self):
            parts = self.path.split("?", 1)[0].lstrip("/").split("/", 1)
            if len(parts) != 2 or parts[0] != bucket:
                return None, None
            key = parts[1]
            p = os.path.realpath(os.path.join(root, key))
            if not p.startswith(os.path.realpath(root) + os.sep) or not os.path.isfile(p):
                return key, None
            return key, p

        def _record(self, method, key, a, b, n, t0):
            if log:
                with LOCK, open(log, "a") as f:
                    f.write(json.dumps(dict(method=method, key=key, start=a, end=b, bytes=n,
                                            s=round(time.time() - t0, 4))) + "\n")

        def _meta_headers(self, p):
            st = os.stat(p)
            self.send_header("ETag", '"%016x%016x"' % (int(st.st_mtime), st.st_size))  # no '-': aws-c-s3 reads '-N' as a part count
            self.send_header("Last-Modified", formatdate(st.st_mtime, usegmt=True))

        def do_HEAD(self):
            t0 = time.time()
            key, p = self._path()
            time.sleep(delay_s)
            if p is None:
                self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers()
                return
            size = os.path.getsize(p)
            self.send_response(200)
            self.send_header("Content-Length", str(size))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Type", "binary/octet-stream")
            self._meta_headers(p)
            self.end_headers()
            self._record("HEAD", key, None, None, 0, t0)

        def do_GET(self):
            t0 = time.time()
            key, p = self._path()
            time.sleep(delay_s)
            if p is None:
                body = b"<Error><Code>NoSuchKey</Code></Error>"
                self.send_response(404); self.send_header("Content-Length", str(len(body))); self.end_headers()
                self.wfile.write(body)
                return
            size = os.path.getsize(p)
            a, b = 0, size - 1
            m = re.match(r"bytes=(\d+)-(\d*)", self.headers.get("Range", ""))
            if m:
                a = int(m.group(1)); b = min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
                self.send_response(206)
                self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
            else:
                self.send_response(200)
            n = b - a + 1
            self._meta_headers(p)
            self.send_header("Content-Length", str(n))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Type", "binary/octet-stream")
            self.end_headers()
            with open(p, "rb") as f:
                f.seek(a)
                left, step = n, 1 << 20
                while left:
                    t = time.time()
                    chunk = f.read(min(step, left))
                    self.wfile.write(chunk)
                    left -= len(chunk)
                    if bps:  # pace to the target rate
                        time.sleep(max(0.0, len(chunk) / bps - (time.time() - t)))
            self._record("GET", key, a, b, n, t0)

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--port", type=int, default=9123)
    ap.add_argument("--delay-ms", type=float, default=0)
    ap.add_argument("--mbps", type=float, default=0, help="per-response MB/s cap (0 = none)")
    ap.add_argument("--log", default=None)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port),
                              make_handler(a.root, a.bucket, a.delay_ms / 1000, a.mbps * 1e6, a.log))
    print(f"serving {a.root} as s3://{a.bucket} on 127.0.0.1:{a.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
