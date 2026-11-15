cmake_minimum_required(VERSION 3.8)
project(redline_env)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(PROGRAMS scripts/sim_clock scripts/rad_replay scripts/scenario_player scripts/env_server scripts/scout_stub scripts/scout_flight DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  # Nodes import redline_core (numba, scipy): tests use the REDLINE venv Python (D009).
  if(NOT REDLINE_PYTHON AND DEFINED ENV{REDLINE_VENV})
    set(REDLINE_PYTHON "$ENV{REDLINE_VENV}/bin/python")
  endif()
  if(NOT REDLINE_PYTHON OR NOT EXISTS "${REDLINE_PYTHON}")
    message(FATAL_ERROR "redline_env tests need the REDLINE venv Python: source scripts/common.sh "
                        "(REDLINE_VENV) or pass -DREDLINE_PYTHON=<python>")
  endif()
  # ROS pytest plugins (launch_testing needs lark) are not in the venv; without this
  # ament's pytest probe fails and the test would be skipped silently.
  set(ENV{PYTEST_DISABLE_PLUGIN_AUTOLOAD} 1)
  ament_has_pytest(redline_has_pytest PYTHON_EXECUTABLE "${REDLINE_PYTHON}")
  if(NOT redline_has_pytest)
    message(FATAL_ERROR "pytest is not usable with ${REDLINE_PYTHON}; refusing to skip node tests")
  endif()
  ament_add_pytest_test(sim_clock_node test/test_sim_clock.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 60
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=81 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(rad_replay_node test/test_rad_replay.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 60
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=88 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(env_server_node test/test_env_server.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 60
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=91 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(scout_stub_node test/test_scout_stub.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 120
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=96 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(scout_flight_node test/test_scout_flight.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}" TIMEOUT 60
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=162 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(scenario_player_node test/test_scenario_player.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 60
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=94 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
endif()
ament_package()
