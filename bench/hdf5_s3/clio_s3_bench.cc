/*
 * clio_s3_bench.cc - time the CLIO stack's path from S3 to an HDF5 read.
 *
 *   clio_s3_bench <bucket> <key> <region> [warm_reps]
 *
 * 1. stage:   CAE S3FileAssimilator copies s3://<bucket>/<key> into a CTE tag
 *             (1 MiB "chunk_N" blobs, striped parallel ranged GETs). Timed from
 *             AsyncParseOmni to completion.
 * 2. read:    every chunk blob is read back from CTE into one memory buffer
 *             (all GetBlobs in flight at once).
 * 3. hdf5:    the buffer is opened as an HDF5 file image (core driver) and the
 *             four access patterns of ros3_bench run against it:
 *             meta, full, window (rows 10000-10999), channel (column 200).
 * Steps 2-3 repeat `warm_reps` times: once data is in CTE, later readers skip S3.
 *
 * Needs a running runtime (clio_run start) composed with CTE + CAE; the runtime
 * does the GET, so it must see AWS_NO_SIGN_REQUEST=1 for a public bucket.
 * Output lines: "stage ms", "read ms", "<pattern> rep open_ms read_ms bytes".
 */
#include <hdf5.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include <clio_runtime/clio_runtime.h>
#include <clio_cae/core/core_client.h>
#include <clio_cae/core/constants.h>
#include <clio_cae/core/factory/assimilation_ctx.h>
#include <clio_cte/core/core_client.h>

namespace {

double Ms(std::chrono::steady_clock::time_point t0) {
  return std::chrono::duration<double, std::milli>(
             std::chrono::steady_clock::now() - t0).count();
}

/* Read every chunk_N blob of the tag into one contiguous buffer. */
bool ReadAll(clio::cte::core::Client* cte, const clio::cte::core::TagId& tag,
             std::vector<char>& out) {
  auto list = cte->AsyncGetContainedBlobs(tag);
  list.Wait();
  size_t n = 0;
  for (const auto& b : list->blob_names_) n += b.rfind("chunk_", 0) == 0;
  std::vector<size_t> sizes(n);
  for (size_t i = 0; i < n; ++i) {
    auto s = cte->AsyncGetBlobSize(tag, "chunk_" + std::to_string(i));
    s.Wait();
    sizes[i] = s->size_;
  }
  std::vector<size_t> off(n + 1, 0);
  for (size_t i = 0; i < n; ++i) off[i + 1] = off[i] + sizes[i];
  out.resize(off[n]);
  struct Pending {
    decltype(CLIO_IPC->AllocateBuffer(0)) buf;
    clio::run::Future<clio::cte::core::GetBlobTask> fut;
  };
  std::vector<Pending> p(n);
  for (size_t i = 0; i < n; ++i) {
    p[i].buf = CLIO_IPC->AllocateBuffer(sizes[i]);
    ctp::ipc::ShmPtr<> shm = p[i].buf.shm_.template Cast<void>();
    p[i].fut = cte->AsyncGetBlob(tag, "chunk_" + std::to_string(i), 0, sizes[i], 0, shm);
  }
  bool ok = true;
  for (size_t i = 0; i < n; ++i) {
    p[i].fut.Wait();
    ok &= p[i].fut->GetReturnCode() == 0;
    std::memcpy(out.data() + off[i], p[i].buf.ptr_, sizes[i]);
    CLIO_IPC->FreeBuffer(p[i].buf);
  }
  return ok && n > 0;
}

herr_t ListCb(hid_t g, const char* name, const H5L_info2_t*, void* op) {
  hid_t d = H5Dopen2(g, name, H5P_DEFAULT);
  if (d < 0) return 0;
  hid_t s = H5Dget_space(d), t = H5Dget_type(d);
  hsize_t dims[8];
  *static_cast<size_t*>(op) += H5Sget_simple_extent_dims(s, dims, nullptr) + H5Tget_size(t);
  H5Tclose(t); H5Sclose(s); H5Dclose(d);
  return 0;
}

/* Open the in-memory image and run one pattern; returns false on error. */
bool RunPattern(std::vector<char>& img, const char* pat, int rep) {
  auto t0 = std::chrono::steady_clock::now();
  hid_t fapl = H5Pcreate(H5P_FILE_ACCESS);
  H5Pset_fapl_core(fapl, 64 * 1024 * 1024, 0);
  H5Pset_file_image(fapl, img.data(), img.size());  // copies the image
  hid_t f = H5Fopen("clio_image.h5", H5F_ACC_RDONLY, fapl);
  if (f < 0) return false;
  double open_ms = Ms(t0);
  auto t1 = std::chrono::steady_clock::now();
  size_t bytes = 0;
  if (!std::strcmp(pat, "meta")) {
    H5Literate2(f, H5_INDEX_NAME, H5_ITER_NATIVE, nullptr, ListCb, &bytes);
  } else {
    hid_t d = H5Dopen2(f, "/das", H5P_DEFAULT), fs = H5Dget_space(d);
    hsize_t dims[2];
    H5Sget_simple_extent_dims(fs, dims, nullptr);
    hsize_t start[2] = {0, 0}, count[2] = {dims[0], dims[1]};
    if (!std::strcmp(pat, "window")) { start[0] = 10000; count[0] = 1000; }
    if (!std::strcmp(pat, "channel")) { start[1] = 200; count[1] = 1; }
    H5Sselect_hyperslab(fs, H5S_SELECT_SET, start, nullptr, count, nullptr);
    hid_t ms = H5Screate_simple(2, count, nullptr);
    std::vector<float> buf(count[0] * count[1]);
    if (H5Dread(d, H5T_NATIVE_FLOAT, ms, fs, H5P_DEFAULT, buf.data()) < 0) return false;
    bytes = buf.size() * sizeof(float);
    H5Sclose(ms); H5Sclose(fs); H5Dclose(d);
  }
  H5Fclose(f);
  H5Pclose(fapl);
  std::printf("%s %d %.1f %.1f %zu\n", pat, rep, open_ms, Ms(t1), bytes);
  std::fflush(stdout);
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 4) {
    std::fprintf(stderr, "usage: %s <bucket> <key> <region> [warm_reps]\n", argv[0]);
    return 2;
  }
  std::setvbuf(stdout, nullptr, _IOLBF, 0);  // keep results if teardown aborts
  std::string bucket = argv[1], key = argv[2], region = argv[3];
  int reps = argc > 4 ? std::atoi(argv[4]) : 3;

  if (!clio::run::CLIO_INIT(clio::run::RuntimeMode::kClient, false)) {
    std::fprintf(stderr, "CLIO_INIT failed (is clio_run started?)\n");
    return 1;
  }
  clio::cte::core::CLIO_CTE_CLIENT_INIT();
  CLIO_CAE_CLIENT_INIT();
  clio::cae::core::Client cae(clio::cae::core::kCaePoolId);
  auto* cte = CLIO_CTE_CLIENT;

  // A fresh tag per run so nothing is served from an earlier stage.
  std::string tag_name = "s3bench_" + std::to_string(
      std::chrono::system_clock::now().time_since_epoch().count());
  clio::cae::core::AssimilationCtx ctx;
  ctx.src = "s3://" + bucket + "/" + key;
  ctx.dst = "iowarp::" + tag_name;
  ctx.format = "binary";
  ctx.s3_region = region;
  auto t0 = std::chrono::steady_clock::now();
  auto parse = cae.AsyncParseOmni(std::vector<clio::cae::core::AssimilationCtx>{ctx});
  parse.Wait();
  double stage_ms = Ms(t0);
  if (parse->GetReturnCode() != 0 || parse->result_code_ != 0 ||
      parse->num_tasks_scheduled_ == 0) {
    std::fprintf(stderr, "stage failed: rc=%d result=%d scheduled=%d msg=%s\n",
                 (int)parse->GetReturnCode(), (int)parse->result_code_,
                 (int)parse->num_tasks_scheduled_, parse->error_message_.str().c_str());
    return 1;
  }
  std::printf("stage %.1f\n", stage_ms);

  auto tag = cte->AsyncGetOrCreateTag(tag_name);
  tag.Wait();
  const char* pats[] = {"meta", "full", "window", "channel"};
  for (int r = 1; r <= reps; ++r) {
    std::vector<char> img;
    auto t1 = std::chrono::steady_clock::now();
    if (!ReadAll(cte, tag->tag_id_, img)) { std::fprintf(stderr, "readback failed\n"); return 1; }
    std::printf("read %d %.1f %zu\n", r, Ms(t1), img.size());
    for (const char* p : pats) {
      if (!RunPattern(img, p, r)) { std::fprintf(stderr, "HDF5 %s failed\n", p); return 1; }
    }
  }
  auto del = cte->AsyncDelTag(tag_name);
  del.Wait();
  return 0;
}
