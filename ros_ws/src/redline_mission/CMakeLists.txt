cmake_minimum_required(VERSION 3.8)
project(redline_mission)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(PROGRAMS scripts/cell_store scripts/mission_manager scripts/voi_tasker scripts/campaign_controller scripts/campaign_robot_pose DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  # Nodes import redline_core (numba, scipy): tests use the REDLINE venv Python (D009).
  if(NOT REDLINE_PYTHON AND DEFINED ENV{REDLINE_VENV})
    set(REDLINE_PYTHON "$ENV{REDLINE_VENV}/bin/python")
  endif()
  if(NOT REDLINE_PYTHON OR NOT EXISTS "${REDLINE_PYTHON}")
    message(FATAL_ERROR "redline_mission tests need the REDLINE venv Python: source scripts/common.sh "
                        "(REDLINE_VENV) or pass -DREDLINE_PYTHON=<python>")
  endif()
  # ROS pytest plugins (launch_testing needs lark) are not in the venv; without this
  # ament's pytest probe fails and the test would be skipped silently.
  set(ENV{PYTEST_DISABLE_PLUGIN_AUTOLOAD} 1)
  ament_has_pytest(redline_has_pytest PYTHON_EXECUTABLE "${REDLINE_PYTHON}")
  if(NOT redline_has_pytest)
    message(FATAL_ERROR "pytest is not usable with ${REDLINE_PYTHON}; refusing to skip node tests")
  endif()
  ament_add_pytest_test(cell_store_node test/test_cell_store.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}"
    TIMEOUT 90
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=83 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(eva_intro_node test/test_eva_intro_node.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}" TIMEOUT 60
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=92 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(voi_tasker_node test/test_voi_tasker.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}" TIMEOUT 120
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=97 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(mission_precursor_node test/test_mission_precursor_node.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}" TIMEOUT 120
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=98 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(mission_flow_node test/test_mission_flow_node.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}" TIMEOUT 90
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=95 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(campaign_controller_node test/test_campaign_controller.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}" TIMEOUT 120
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=179 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(campaign_robot_pose_node test/test_campaign_robot_pose.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}" TIMEOUT 60
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=161 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  ament_add_pytest_test(mission_leak_node test/test_mission_leak_node.py
    PYTHON_EXECUTABLE "${REDLINE_PYTHON}" TIMEOUT 90
    ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ROS_DOMAIN_ID=102 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
endif()
ament_package()
