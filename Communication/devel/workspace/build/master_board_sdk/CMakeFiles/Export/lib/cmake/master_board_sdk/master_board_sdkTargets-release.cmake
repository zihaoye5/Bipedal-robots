#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "master_board_sdk::master_board_sdk" for configuration "Release"
set_property(TARGET master_board_sdk::master_board_sdk APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(master_board_sdk::master_board_sdk PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libmaster_board_sdk.so"
  IMPORTED_SONAME_RELEASE "libmaster_board_sdk.so"
  )

list(APPEND _IMPORT_CHECK_TARGETS master_board_sdk::master_board_sdk )
list(APPEND _IMPORT_CHECK_FILES_FOR_master_board_sdk::master_board_sdk "${_IMPORT_PREFIX}/lib/libmaster_board_sdk.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
