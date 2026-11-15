cmake_minimum_required(VERSION 3.8)
project(redline_science)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(PROGRAMS scripts/science_instruments scripts/lab_assay DESTINATION lib/${PROJECT_NAME})
if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  if(NOT REDLINE_PYTHON AND DEFINED ENV{REDLINE_VENV})
    set(REDLINE_PYTHON "$ENV{REDLINE_VENV}/bin/python")
  endif()
  if(NOT REDLINE_PYTHON OR NOT EXISTS "${REDLINE_PYTHON}")
    message(FATAL_ERROR "redline_science needs the REDLINE venv Python for meaningful node tests")
  endif()
  set(ENV{PYTEST_DISABLE_PLUGIN_AUTOLOAD} 1)
  ament_add_pytest_test(science_instruments_node test/test_science_instruments.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}" TIMEOUT 180
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=158 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(lab_assay_node test/test_lab_assay.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}" TIMEOUT 60
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=168 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
endif()
ament_package()
