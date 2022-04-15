INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_BURSTFILE burstfile)

FIND_PATH(
    BURSTFILE_INCLUDE_DIRS
    NAMES burstfile/api.h
    HINTS $ENV{BURSTFILE_DIR}/include
        ${PC_BURSTFILE_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    BURSTFILE_LIBRARIES
    NAMES gnuradio-burstfile
    HINTS $ENV{BURSTFILE_DIR}/lib
        ${PC_BURSTFILE_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/burstfileTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(BURSTFILE DEFAULT_MSG BURSTFILE_LIBRARIES BURSTFILE_INCLUDE_DIRS)
MARK_AS_ADVANCED(BURSTFILE_LIBRARIES BURSTFILE_INCLUDE_DIRS)
