INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_STREAMER streamer)

FIND_PATH(
    STREAMER_INCLUDE_DIRS
    NAMES streamer/api.h
    HINTS $ENV{STREAMER_DIR}/include
        ${PC_STREAMER_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    STREAMER_LIBRARIES
    NAMES gnuradio-streamer
    HINTS $ENV{STREAMER_DIR}/lib
        ${PC_STREAMER_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/streamerTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(STREAMER DEFAULT_MSG STREAMER_LIBRARIES STREAMER_INCLUDE_DIRS)
MARK_AS_ADVANCED(STREAMER_LIBRARIES STREAMER_INCLUDE_DIRS)
