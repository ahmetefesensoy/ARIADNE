cmake_minimum_required(VERSION 3.8)
project(redline_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(action_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/FieldTile.msg"
  "msg/Provenance.msg"
  "msg/CellState.msg"
  "msg/CellDelta.msg"
  "msg/ScalarField.msg"
  "msg/MarginField.msg"
  "msg/RedLine.msg"
  "msg/Consumables.msg"
  "msg/CrewState.msg"
  "msg/Station.msg"
  "msg/PlanLeg.msg"
  "msg/EVAPlan.msg"
  "msg/Alert.msg"
  "msg/RuleViolation.msg"
  "msg/DoseRate.msg"
  "msg/EnvState.msg"
  "msg/EvidenceRecord.msg"
  "msg/InstrumentProduct.msg"
  "msg/SampleRecord.msg"
  "msg/DecisionRecord.msg"
  "msg/CommandOwner.msg"
  "msg/MissionState.msg"
  "srv/SetCommandOwner.srv"
  "srv/PlanEva.srv"
  "srv/QueryCell.srv"
  "srv/ScenarioControl.srv"
  "srv/GetManifest.srv"
  "action/SurveyArea.action"
  "action/InspectTarget.action"
  "action/ContactScience.action"
  "action/RemoteLibs.action"
  "action/MultispectralImage.action"
  "action/NeutronSurvey.action"
  "action/Drill.action"
  "action/CacheSample.action"
  "action/DeployStation.action"
  "action/ReturnToShelter.action"
  "action/ExecuteScout.action"
  DEPENDENCIES action_msgs builtin_interfaces geometry_msgs nav_msgs std_msgs
)

ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(interface_contracts test/test_interface_contracts.py
    TIMEOUT 60
    APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_BINARY_DIR}/rosidl_generator_py
  )
endif()

ament_package()
