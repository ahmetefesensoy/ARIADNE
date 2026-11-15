cmake_minimum_required(VERSION 3.8)
project(redline_planner)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(PROGRAMS scripts/walkback_field scripts/planner_server DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  # Nodes import redline_core (numba, scipy): tests use the REDLINE venv Python (D009).
  if(NOT REDLINE_PYTHON AND DEFINED ENV{REDLINE_VENV})
    set(REDLINE_PYTHON "$ENV{REDLINE_VENV}/bin/python")
  endif()
  if(NOT REDLINE_PYTHON OR NOT EXISTS "${REDLINE_PYTHON}")
    message(FATAL_ERROR "redline_planner tests need the REDLINE venv Python: source scripts/common.sh "
                        "(REDLINE_VENV) or pass -DREDLINE_PYTHON=<python>")
  endif()
  # ROS pytest plugins (launch_testing needs lark) are not in the venv; without this
  # ament's pytest probe fails and the test would be skipped silently.
  set(ENV{PYTEST_DISABLE_PLUGIN_AUTOLOAD} 1)
  ament_has_pytest(redline_has_pytest PYTHON_EXECUTABLE "${REDLINE_PYTHON}")
  if(NOT redline_has_pytest)
    message(FATAL_ERROR "pytest is not usable with ${REDLINE_PYTHON}; refusing to skip node tests")
  endif()
  ament_add_pytest_test(walkback_field_node test/test_walkback_field.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 120
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=84 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(planner_server_node test/test_planner_server.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 120
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=101 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(s1_launch test/test_s1_launch.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 300
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=100 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
        "REDLINE_PYTHON=${REDLINE_PYTHON}")
  # The launch file and installed executables, started by `ros2 launch` (system Python).
  ament_add_pytest_test(t5_thread_launch test/test_t5_thread_launch.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 240
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=85 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
        "REDLINE_PYTHON=${REDLINE_PYTHON}")
endif()
ament_package()
