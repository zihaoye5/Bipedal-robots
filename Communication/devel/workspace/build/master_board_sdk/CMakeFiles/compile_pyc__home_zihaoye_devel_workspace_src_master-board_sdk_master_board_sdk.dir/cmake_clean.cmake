file(REMOVE_RECURSE
  "example/com_analyser.pyc"
  "example/example.pyc"
  "example/listener.pyc"
)

# Per-language clean rules from dependency scanning.
foreach(lang )
  include(CMakeFiles/compile_pyc__home_zihaoye_devel_workspace_src_master-board_sdk_master_board_sdk.dir/cmake_clean_${lang}.cmake OPTIONAL)
endforeach()
