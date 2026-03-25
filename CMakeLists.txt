cmake_minimum_required(VERSION 3.0.2)
project(joy_overlay_tools)

find_package(catkin REQUIRED COMPONENTS
  rospy
  sensor_msgs
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/joy_overlay_visualizer.py
  scripts/virtual_joy_gui.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
