cmake_minimum_required(VERSION 3.20)
project(cae_omni_hdf5_roundtrip CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# An installed clio-core built with CLIO_CORE_ENABLE_HDF5=ON. Point
# CMAKE_PREFIX_PATH at its install prefix.
find_package(clio-core CONFIG REQUIRED)
find_package(HDF5 REQUIRED COMPONENTS C)

add_executable(cae_omni_hdf5_roundtrip test_omni_hdf5_roundtrip.cc)
target_link_libraries(cae_omni_hdf5_roundtrip PRIVATE
  clio::cae::core_client
  clio::cte::core_client
  ctp::configure              # yaml-cpp, for loading the OMNI file
  ${HDF5_LIBRARIES}
)
target_include_directories(cae_omni_hdf5_roundtrip PRIVATE ${HDF5_INCLUDE_DIRS})

message(STATUS "clio-core found: ${clio-core_FOUND}; HDF5 ${HDF5_VERSION}")
