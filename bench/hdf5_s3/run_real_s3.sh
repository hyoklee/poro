#!/bin/bash
# Real-S3 comparison on one PoroTomo DASV record (public NREL bucket, us-west-2).
# Writes results/real_s3_<stamp>/{curl,ros3,clio}.txt
HERE=$(cd "$(dirname "$0")" && pwd)
B=nrel-pds-porotomo; K=DAS/H5/DASV/20160317/PoroTomo_iDAS025_160318160317.h5; R=us-west-2
O=$HERE/results/real_s3_$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$O"
URL=https://$B.s3.$R.amazonaws.com/$K
echo "# kind rep seconds bytes" > "$O/curl.txt"
for i in 1 2 3 4 5; do   # per-request latency (1 byte) and whole-object bandwidth
  curl -s -o /dev/null -r 0-0 -w "range1B $i %{time_total} %{size_download}\n" "$URL" >> "$O/curl.txt"
  curl -s -o /dev/null -r 0-3071999 -w "range3MB $i %{time_total} %{size_download}\n" "$URL" >> "$O/curl.txt"
  curl -s -o /dev/null -w "full $i %{time_total} %{size_download}\n" "$URL" >> "$O/curl.txt"
done
export LD_LIBRARY_PATH=$HOME/miniconda3/envs/iowarp/lib AWS_EC2_METADATA_DISABLED=true
echo "# pattern rep open_ms read_ms total_ms bytes" > "$O/ros3.txt"
for p in meta full window channel; do "$HERE/build/ros3_bench" "s3://$B/$K" $p 5 >> "$O/ros3.txt"; done
HDF5_ROS3_VFD_DEBUG=1 "$HERE/build/ros3_bench" "s3://$B/$K" window 1 2>&1 >/dev/null | grep -E "^ -- (GET|HEAD)" > "$O/ros3_requests_window.txt"
HDF5_ROS3_VFD_DEBUG=1 "$HERE/build/ros3_bench" "s3://$B/$K" channel 1 2>&1 >/dev/null | grep -E "^ -- (GET|HEAD)" > "$O/ros3_requests_channel.txt"
for i in 1 2 3; do
  echo "# run $i" >> "$O/clio.txt"
  "$HERE/run_clio.sh" $B $K $R 3 2>/dev/null | grep -E "^(stage|read|meta|full|window|channel) " >> "$O/clio.txt"
done
echo "$O"
