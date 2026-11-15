cmake_minimum_required(VERSION 3.8)
project(redline_navigation)

find_package(ament_cmake REQUIRED)
find_package(nav2_core REQUIRED)
find_package(nav2_costmap_2d REQUIRED)
find_package(pluginlib REQUIRED)
find_package(nav_msgs REQUIRED)

add_library(interpolating_planner SHARED src/interpolating_planner.cpp)
target_compile_features(interpolating_planner PUBLIC cxx_std_17)
target_include_directories(interpolating_planner PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
ament_target_dependencies(interpolating_planner nav2_core nav2_costmap_2d pluginlib nav_msgs)
pluginlib_export_plugin_description_file(nav2_core planner_plugin.xml)
install(TARGETS interpolating_planner LIBRARY DESTINATION lib)
install(DIRECTORY include/ DESTINATION include)

install(DIRECTORY launch config behavior_trees rviz
  DESTINATION share/${PROJECT_NAME}
)
install(FILES README.md DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_path_interpolation test/test_path_interpolation.cpp)
  target_include_directories(test_path_interpolation PRIVATE include)
  ament_target_dependencies(test_path_interpolation nav_msgs nav2_core nav2_costmap_2d)
  ament_add_pytest_test(navigation_contracts test/test_navigation_contracts.py TIMEOUT 60)
  ament_add_pytest_test(launch_contracts test/test_launch_contracts.py TIMEOUT 60)
endif()

ament_package()
