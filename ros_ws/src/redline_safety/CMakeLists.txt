cmake_minimum_required(VERSION 3.8)
project(redline_safety)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(PROGRAMS scripts/rule_monitor DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  # Nodes import redline_core (numba, scipy): tests use the REDLINE venv Python (D009).
  if(NOT REDLINE_PYTHON AND DEFINED ENV{REDLINE_VENV})
    set(REDLINE_PYTHON "$ENV{REDLINE_VENV}/bin/python")
  endif()
  if(NOT REDLINE_PYTHON OR NOT EXISTS "${REDLINE_PYTHON}")
    message(FATAL_ERROR "redline_safety tests need the REDLINE venv Python: source scripts/common.sh "
                        "(REDLINE_VENV) or pass -DREDLINE_PYTHON=<python>")
  endif()
  # ROS pytest plugins (launch_testing needs lark) are not in the venv; without this
  # ament's pytest probe fails and the test would be skipped silently.
  set(ENV{PYTEST_DISABLE_PLUGIN_AUTOLOAD} 1)
  ament_has_pytest(redline_has_pytest PYTHON_EXECUTABLE "${REDLINE_PYTHON}")
  if(NOT redline_has_pytest)
    message(FATAL_ERROR "pytest is not usable with ${REDLINE_PYTHON}; refusing to skip node tests")
  endif()
  ament_add_pytest_test(rule_monitor_node test/test_rule_monitor.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 90
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=99 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
endif()
ament_package()
