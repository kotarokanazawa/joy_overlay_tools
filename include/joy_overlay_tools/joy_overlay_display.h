#ifndef JOY_OVERLAY_TOOLS_JOY_OVERLAY_DISPLAY_H
#define JOY_OVERLAY_TOOLS_JOY_OVERLAY_DISPLAY_H

#include <mutex>
#include <string>

#include <ros/ros.h>
#include <sensor_msgs/Joy.h>

#include <rviz/display.h>

namespace Ogre
{
class Overlay;
class OverlayContainer;
class TextAreaOverlayElement;
}  // namespace Ogre

namespace rviz
{
class ColorProperty;
class FloatProperty;
class IntProperty;
class RosTopicProperty;
}  // namespace rviz

namespace joy_overlay_tools
{

class JoyOverlayDisplay : public rviz::Display
{
public:
  JoyOverlayDisplay();
  ~JoyOverlayDisplay() override;

protected:
  void onInitialize() override;
  void onEnable() override;
  void onDisable() override;
  void update(float wall_dt, float ros_dt) override;

private:
  void subscribe();
  void unsubscribe();
  void processMessage(const sensor_msgs::Joy::ConstPtr& msg);
  void redraw();
  void createOverlay();
  void destroyOverlay();
  std::string formatJoyText(const sensor_msgs::Joy::ConstPtr& joy, bool stale) const;

  ros::NodeHandle nh_;
  ros::Subscriber joy_sub_;
  sensor_msgs::Joy::ConstPtr latest_joy_;
  ros::WallTime last_msg_time_;
  std::mutex mutex_;

  Ogre::Overlay* overlay_;
  Ogre::OverlayContainer* panel_;
  Ogre::TextAreaOverlayElement* text_;
  std::string overlay_name_;

  rviz::RosTopicProperty* topic_property_;
  rviz::IntProperty* left_property_;
  rviz::IntProperty* top_property_;
  rviz::IntProperty* width_property_;
  rviz::IntProperty* height_property_;
  rviz::IntProperty* max_buttons_property_;
  rviz::IntProperty* max_axes_property_;
  rviz::FloatProperty* timeout_property_;
  rviz::ColorProperty* bg_color_property_;
  rviz::ColorProperty* text_color_property_;
  rviz::ColorProperty* accent_color_property_;

  std::string subscribed_topic_;
  bool require_redraw_;
};

}  // namespace joy_overlay_tools

#endif
