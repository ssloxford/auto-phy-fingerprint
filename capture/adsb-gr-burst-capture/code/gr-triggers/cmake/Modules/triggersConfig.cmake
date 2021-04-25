INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_TRIGGERS triggers)

FIND_PATH(
    TRIGGERS_INCLUDE_DIRS
    NAMES triggers/api.h
    HINTS $ENV{TRIGGERS_DIR}/include
        ${PC_TRIGGERS_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    TRIGGERS_LIBRARIES
    NAMES gnuradio-triggers
    HINTS $ENV{TRIGGERS_DIR}/lib
        ${PC_TRIGGERS_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/triggersTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(TRIGGERS DEFAULT_MSG TRIGGERS_LIBRARIES TRIGGERS_INCLUDE_DIRS)
MARK_AS_ADVANCED(TRIGGERS_LIBRARIES TRIGGERS_INCLUDE_DIRS)
