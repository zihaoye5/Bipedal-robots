file(REMOVE_RECURSE
  "example/com_analyser.pyc"
  "example/example.pyc"
  "example/listener.pyc"
)

# Per-language clean rules from dependency scanning.
foreach(lang )
  include(CMakeFiles/python.dir/cmake_clean_${lang}.cmake OPTIONAL)
endforeach()
