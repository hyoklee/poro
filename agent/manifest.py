#!/usr/bin/env python3
"""Build the list of PoroTomo DASV records to analyse.

Lists s3://nrel-pds-porotomo/DAS/H5/DASV/<day>/ anonymously over HTTPS and
keeps every `--stride`-th 30 s record (stride 20 = one record per 10 min).
Writes one S3 key per line.

    manifest.py --stride 20 -o agent/results/manifest.txt
"""
import argparse
import re
import urllib.parse
import urllib.request

BUCKET = "https://nrel-pds-porotomo.s3.amazonaws.com"


def list_keys(prefix, delimiter=None):
    keys, prefixes, token = [], [], None
    while True:
        q = {"list-type": "2", "prefix": prefix}
        if delimiter:
            q["delimiter"] = delimiter
        if token:
            q["continuation-token"] = token
        with urllib.request.urlopen(f"{BUCKET}/?{urllib.parse.urlencode(q)}") as r:
            body = r.read().decode()
        keys += re.findall(r"<Key>([^<]+)</Key>", body)
        prefixes += re.findall(r"<Prefix>([^<]+)</Prefix>", body)
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", body)
        if not m:
            return keys, [p for p in prefixes if p != prefix]
        token = m.group(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="DAS/H5/DASV/")
    ap.add_argument("--stride", type=int, default=20)
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    _, days = list_keys(a.prefix, "/")
    keys = []
    for d in sorted(days):
        k, _ = list_keys(d)
        k = sorted(x for x in k if x.endswith(".h5"))
        print(f"{d}: {len(k)} records")
        keys += k
    keys.sort(key=lambda k: k.rsplit("_", 1)[-1])  # by yymmddHHMMSS
    sel = keys[:: a.stride]
    with open(a.out, "w") as f:
        f.write("\n".join(sel) + "\n")
    print(f"total {len(keys)} records, selected {len(sel)} (stride {a.stride}) -> {a.out}")


if __name__ == "__main__":
    main()
