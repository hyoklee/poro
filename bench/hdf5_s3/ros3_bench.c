/*
 * ros3_bench.c - time HDF5 reads of a PoroTomo DASV record through the HDF5
 * read-only S3 VFD (ROS3, HDF5 >= 2.0, aws-c-s3 backend), a local file (sec2),
 * or an in-memory file image (core).
 *
 *   ros3_bench <s3://bucket/key | /local/path> <pattern> [reps] [page_buf_MiB]
 *
 * pattern:
 *   meta     open the file, list every root dataset's shape and dtype, close
 *   full     read all of /das (30000 x 384 float32, 46 MB)
 *   window   read a 1 s window of /das: rows 10000-10999, all 384 channels
 *   channel  read one channel of /das: column 200, all 30000 rows
 * Every repetition opens the file fresh, so caches start cold.
 *
 * Environment:
 *   ROS3_REGION    AWS region (default us-west-2)
 *   ROS3_ENDPOINT  S3 endpoint URL for an S3-compatible server (optional)
 *   HDF5_ROS3_VFD_DEBUG=1 makes the VFD print each S3 request to stderr
 *
 * Output: one line per rep, "pattern rep open_ms read_ms total_ms bytes".
 */
#include <hdf5.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static double now_ms(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return ts.tv_sec * 1e3 + ts.tv_nsec / 1e6;
}

static herr_t list_cb(hid_t g, const char *name, const H5L_info2_t *info, void *op) {
  (void)info;
  size_t *n = (size_t *)op;
  hid_t d = H5Dopen2(g, name, H5P_DEFAULT);
  if (d < 0) return 0;
  hid_t s = H5Dget_space(d), t = H5Dget_type(d);
  hsize_t dims[8];
  int nd = H5Sget_simple_extent_dims(s, dims, NULL);
  *n += (size_t)nd + H5Tget_size(t);
  H5Tclose(t);
  H5Sclose(s);
  H5Dclose(d);
  return 0;
}

int main(int argc, char **argv) {
  if (argc < 3) {
    fprintf(stderr, "usage: %s <s3://bucket/key|path> <meta|full|window|channel> [reps] [page_buf_MiB]\n", argv[0]);
    return 2;
  }
  const char *url = argv[1], *pat = argv[2];
  int reps = argc > 3 ? atoi(argv[3]) : 3;
  size_t pbuf = argc > 4 ? (size_t)atol(argv[4]) * 1024 * 1024 : 0;
  int is_s3 = strncmp(url, "s3://", 5) == 0 || strncmp(url, "https://", 8) == 0;

  for (int r = 1; r <= reps; r++) {
    hid_t fapl = H5Pcreate(H5P_FILE_ACCESS);
    if (is_s3) {
      H5FD_ros3_fapl_t fa;
      memset(&fa, 0, sizeof fa);
      fa.version = H5FD_CURR_ROS3_FAPL_T_VERSION;
      fa.authenticate = false;
      const char *reg = getenv("ROS3_REGION");
      strncpy(fa.aws_region, reg && *reg ? reg : "us-west-2", H5FD_ROS3_MAX_REGION_LEN);
      if (H5Pset_fapl_ros3(fapl, &fa) < 0) { fprintf(stderr, "set_fapl_ros3 failed\n"); return 1; }
      const char *ep = getenv("ROS3_ENDPOINT");
      if (ep && *ep) H5Pset_fapl_ros3_endpoint(fapl, ep);
    }
    if (pbuf) H5Pset_page_buffer_size(fapl, pbuf, 0, 0);

    double t0 = now_ms();
    hid_t f = H5Fopen(url, H5F_ACC_RDONLY, fapl);
    if (f < 0) { fprintf(stderr, "H5Fopen failed for %s\n", url); return 1; }
    double t1 = now_ms();
    size_t bytes = 0;
    if (!strcmp(pat, "meta")) {
      size_t n = 0;
      H5Literate2(f, H5_INDEX_NAME, H5_ITER_NATIVE, NULL, list_cb, &n);
      bytes = n;
    } else {
      hid_t d = H5Dopen2(f, "/das", H5P_DEFAULT);
      hid_t fs = H5Dget_space(d);
      hsize_t dims[2];
      H5Sget_simple_extent_dims(fs, dims, NULL);
      hsize_t start[2] = {0, 0}, count[2] = {dims[0], dims[1]};
      if (!strcmp(pat, "window")) { start[0] = 10000; count[0] = 1000; }
      else if (!strcmp(pat, "channel")) { start[1] = 200; count[1] = 1; }
      else if (strcmp(pat, "full")) { fprintf(stderr, "unknown pattern %s\n", pat); return 2; }
      H5Sselect_hyperslab(fs, H5S_SELECT_SET, start, NULL, count, NULL);
      hid_t ms = H5Screate_simple(2, count, NULL);
      size_t n = (size_t)(count[0] * count[1]);
      float *buf = malloc(n * sizeof(float));
      if (H5Dread(d, H5T_NATIVE_FLOAT, ms, fs, H5P_DEFAULT, buf) < 0) { fprintf(stderr, "H5Dread failed\n"); return 1; }
      double sum = 0;  /* touch the data so the read cannot be skipped */
      for (size_t i = 0; i < n; i += 997) sum += buf[i];
      if (sum == 12345.678) puts("");
      bytes = n * sizeof(float);
      free(buf);
      H5Sclose(ms);
      H5Sclose(fs);
      H5Dclose(d);
    }
    double t2 = now_ms();
    H5Fclose(f);
    H5Pclose(fapl);
    double t3 = now_ms();
    printf("%s %d %.1f %.1f %.1f %zu\n", pat, r, t1 - t0, t2 - t1, t3 - t0, bytes);
    fflush(stdout);
  }
  return 0;
}
