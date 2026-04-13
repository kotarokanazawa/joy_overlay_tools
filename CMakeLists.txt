cmake_minimum_required(VERSION 3.0.2)
project(joy_overlay_tools)

find_package(catkin REQUIRED COMPONENTS
  pluginlib
  roscpp
  rospy
  rviz
  sensor_msgs
)

find_package(Qt5 REQUIRED COMPONENTS Widgets)

catkin_package()

include_directories(
  include
  ${catkin_INCLUDE_DIRS}
)

add_library(${PROJECT_NAME}
  src/joy_overlay_display.cpp
)

target_link_libraries(${PROJECT_NAME}
  ${catkin_LIBRARIES}
  Qt5::Widgets
)

catkin_install_python(PROGRAMS
  scripts/joy_overlay_visualizer.py
  scripts/virtual_joy_gui.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

install(TARGETS ${PROJECT_NAME}
  LIBRARY DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
)

install(FILES plugin_description.xml
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

install(DIRECTORY include/${PROJECT_NAME}/
  DESTINATION ${CATKIN_PACKAGE_INCLUDE_DESTINATION}
)
