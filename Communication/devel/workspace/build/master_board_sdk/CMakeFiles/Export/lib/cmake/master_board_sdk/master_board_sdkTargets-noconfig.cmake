#----------------------------------------------------------------
# Generated CMake target import file.
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "master_board_sdk::master_board_sdk" for configuration ""
set_property(TARGET master_board_sdk::master_board_sdk APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(master_board_sdk::master_board_sdk PROPERTIES
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/lib/libmaster_board_sdk.so"
  IMPORTED_SONAME_NOCONFIG "libmaster_board_sdk.so"
  )

list(APPEND _IMPORT_CHECK_TARGETS master_board_sdk::master_board_sdk )
list(APPEND _IMPORT_CHECK_FILES_FOR_master_board_sdk::master_board_sdk "${_IMPORT_PREFIX}/lib/libmaster_board_sdk.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
