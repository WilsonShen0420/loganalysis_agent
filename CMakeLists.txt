cmake_minimum_required(VERSION 3.0.2)
project(loganalysis_agent)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  message_generation
)

# Message and service files
add_message_files(FILES
  DiagResult.msg
)

add_service_files(FILES
  LogDiagQuery.srv
)

generate_messages(DEPENDENCIES
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS rospy std_msgs message_runtime
)

# Install Python package
catkin_python_setup()

# Install scripts
catkin_install_python(PROGRAMS
  scripts/logdiag_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

# Install launch and config
install(DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
)

install(DIRECTORY config/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/config
)
