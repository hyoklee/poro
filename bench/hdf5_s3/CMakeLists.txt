cmake_minimum_required(VERSION 3.20)
project(poro_hdf5_s3_bench C CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# HDF5 >= 2.0 with the ROS3 VFD (conda-forge hdf5 has it; PyPI h5py does not).
find_package(HDF5 REQUIRED COMPONENTS C)
add_executable(ros3_bench ros3_bench.c)
target_include_directories(ros3_bench PRIVATE ${HDF5_INCLUDE_DIRS})
target_link_libraries(ros3_bench PRIVATE ${HDF5_LIBRARIES})

# clio-core installed with CLIO_CORE_ENABLE_CAE, CLIO_CORE_ENABLE_HDF5 and
# CAE_ENABLE_S3. Point CMAKE_PREFIX_PATH at its install prefix.
# With cfs:: destinations on, the installed CAE targets reference
# clio::cte::filesystem_client, but iowarp-coreConfig.cmake never loads that
# package, so clio-core reports itself NOT FOUND. Loading that package first
# fails on its own missing ctp:: targets, so declare an empty stand-in; the
# CAE client library carries its real dependency (DT_NEEDED + RPATH).
if(NOT TARGET clio::cte::filesystem_client)
  add_library(clio::cte::filesystem_client INTERFACE IMPORTED)
endif()
find_package(clio-core CONFIG REQUIRED)
if(clio-core_FOUND)
  add_executable(clio_s3_bench clio_s3_bench.cc)
  target_include_directories(clio_s3_bench PRIVATE ${HDF5_INCLUDE_DIRS})
  target_link_libraries(clio_s3_bench PRIVATE clio::cae::core_client
                        clio::cte::core_client ${HDF5_LIBRARIES})
endif()
