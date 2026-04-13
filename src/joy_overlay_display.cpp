#include "joy_overlay_tools/joy_overlay_display.h"

#include <algorithm>
#include <cstdint>
#include <iomanip>
#include <sstream>

#include <OGRE/Overlay/OgreOverlay.h>
#include <OGRE/Overlay/OgreOverlayContainer.h>
#include <OGRE/Overlay/OgreOverlayManager.h>
#include <OGRE/Overlay/OgreTextAreaOverlayElement.h>
#include <OGRE/OgreColourValue.h>
#include <pluginlib/class_list_macros.h>
#include <QColor>
#include <QProcess>
#include <rviz/display_context.h>
#include <rviz/properties/color_property.h>
#include <rviz/properties/float_property.h>
#include <rviz/properties/int_property.h>
#include <rviz/properties/ros_topic_property.h>
#include <rviz/tool.h>
#include <rviz/tool_manager.h>

namespace joy_overlay_tools
{

namespace
{
double clampAxis(double value)
{
  return std::max(-1.0, std::min(value, 1.0));
}

Ogre::ColourValue toOgreColor(const QColor& color, float alpha)
{
  return Ogre::ColourValue(color.redF(), color.greenF(), color.blueF(), alpha);
}
}  // namespace

JoyOverlayDisplay::JoyOverlayDisplay()
  : overlay_(nullptr)
  , panel_(nullptr)
  , text_(nullptr)
  , topic_property_(new rviz::RosTopicProperty("Joy Topic", "/joy", "sensor_msgs/Joy",
                                               "sensor_msgs/Joy topic to show in the RViz overlay.", this))
  , left_property_(new rviz::IntProperty("Left", 20, "Overlay left position in pixels.", this))
  , top_property_(new rviz::IntProperty("Top", 20, "Overlay top position in pixels.", this))
  , width_property_(new rviz::IntProperty("Width", 360, "Overlay width in pixels.", this))
  , height_property_(new rviz::IntProperty("Height", 260, "Overlay height in pixels.", this))
  , max_buttons_property_(new rviz::IntProperty("Max Buttons", 16, "Maximum number of buttons to draw.", this))
  , max_axes_property_(new rviz::IntProperty("Max Axes", 8, "Maximum number of axes to draw.", this))
  , timeout_property_(new rviz::FloatProperty("Timeout", 1.0f, "Seconds before the overlay reports stale input.", this))
  , bg_color_property_(new rviz::ColorProperty("Background Color", QColor(27, 31, 38),
                                               "Reserved for future filled-panel rendering.", this))
  , text_color_property_(new rviz::ColorProperty("Text Color", QColor(237, 242, 247),
                                                 "Overlay text color.", this))
  , accent_color_property_(new rviz::ColorProperty("Accent Color", QColor(63, 208, 255),
                                                   "Reserved for future filled-panel rendering.", this))
  , require_redraw_(true)
{
  left_property_->setMin(0);
  top_property_->setMin(0);
  width_property_->setMin(120);
  height_property_->setMin(80);
  max_buttons_property_->setMin(0);
  max_buttons_property_->setMax(64);
  max_axes_property_->setMin(0);
  max_axes_property_->setMax(32);
  timeout_property_->setMin(0.1f);
}

JoyOverlayDisplay::~JoyOverlayDisplay()
{
  unsubscribe();
  destroyOverlay();
}

void JoyOverlayDisplay::onInitialize()
{
  std::stringstream ss;
  ss << "joy_overlay_tools_" << reinterpret_cast<std::uintptr_t>(this);
  overlay_name_ = ss.str();
  createOverlay();
}

void JoyOverlayDisplay::createOverlay()
{
  Ogre::OverlayManager& manager = Ogre::OverlayManager::getSingleton();
  overlay_ = manager.create(overlay_name_);
  overlay_->setZOrder(600);

  panel_ = static_cast<Ogre::OverlayContainer*>(
      manager.createOverlayElement("Panel", overlay_name_ + "/panel"));
  panel_->setMetricsMode(Ogre::GMM_PIXELS);
  panel_->setPosition(left_property_->getInt(), top_property_->getInt());
  panel_->setDimensions(width_property_->getInt(), height_property_->getInt());

  text_ = static_cast<Ogre::TextAreaOverlayElement*>(
      manager.createOverlayElement("TextArea", overlay_name_ + "/text"));
  text_->setMetricsMode(Ogre::GMM_PIXELS);
  text_->setPosition(0, 0);
  text_->setDimensions(width_property_->getInt(), height_property_->getInt());
  text_->setFontName("Liberation Sans");
  text_->setCharHeight(16);
  text_->setColour(toOgreColor(text_color_property_->getColor(), 1.0f));
  text_->setCaption("Joy Overlay\nwaiting for Joy input");

  panel_->addChild(text_);
  overlay_->add2D(panel_);
  overlay_->hide();
}

void JoyOverlayDisplay::destroyOverlay()
{
  if (!overlay_name_.empty()) {
    Ogre::OverlayManager& manager = Ogre::OverlayManager::getSingleton();
    if (overlay_) {
      overlay_->hide();
      overlay_->remove2D(panel_);
      manager.destroy(overlay_);
      overlay_ = nullptr;
    }
    if (text_) {
      manager.destroyOverlayElement(text_);
      text_ = nullptr;
    }
    if (panel_) {
      manager.destroyOverlayElement(panel_);
      panel_ = nullptr;
    }
  }
}

void JoyOverlayDisplay::onEnable()
{
  subscribe();
  if (overlay_) {
    overlay_->show();
  }
  require_redraw_ = true;
}

void JoyOverlayDisplay::onDisable()
{
  unsubscribe();
  if (overlay_) {
    overlay_->hide();
  }
}

void JoyOverlayDisplay::subscribe()
{
  const std::string topic = topic_property_->getTopicStd();
  if (topic.empty() || topic == subscribed_topic_) {
    return;
  }

  unsubscribe();
  subscribed_topic_ = topic;
  joy_sub_ = nh_.subscribe(subscribed_topic_, 10, &JoyOverlayDisplay::processMessage, this);
}

void JoyOverlayDisplay::unsubscribe()
{
  joy_sub_.shutdown();
  subscribed_topic_.clear();
}

void JoyOverlayDisplay::processMessage(const sensor_msgs::Joy::ConstPtr& msg)
{
  std::lock_guard<std::mutex> lock(mutex_);
  latest_joy_ = msg;
  last_msg_time_ = ros::WallTime::now();
  require_redraw_ = true;
}

void JoyOverlayDisplay::update(float wall_dt, float ros_dt)
{
  (void)wall_dt;
  (void)ros_dt;

  if (!isEnabled()) {
    return;
  }

  if (topic_property_->getTopicStd() != subscribed_topic_) {
    subscribe();
    require_redraw_ = true;
  }

  redraw();
}

void JoyOverlayDisplay::redraw()
{
  if (!overlay_ || !panel_ || !text_) {
    return;
  }

  sensor_msgs::Joy::ConstPtr joy;
  ros::WallTime last_msg_time;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    joy = latest_joy_;
    last_msg_time = last_msg_time_;
  }

  const bool stale =
      !joy || (ros::WallTime::now() - last_msg_time).toSec() > timeout_property_->getFloat();
  if (!require_redraw_ && !stale) {
    return;
  }
  require_redraw_ = false;

  panel_->setPosition(left_property_->getInt(), top_property_->getInt());
  panel_->setDimensions(width_property_->getInt(), height_property_->getInt());
  text_->setDimensions(width_property_->getInt(), height_property_->getInt());
  text_->setColour(toOgreColor(text_color_property_->getColor(), 1.0f));
  text_->setCaption(formatJoyText(joy, stale));

  if (!overlay_->isVisible()) {
    overlay_->show();
  }
}

std::string JoyOverlayDisplay::formatJoyText(const sensor_msgs::Joy::ConstPtr& joy, bool stale) const
{
  std::ostringstream out;
  out << "Joy Overlay\n";
  out << "topic: " << (subscribed_topic_.empty() ? topic_property_->getTopicStd() : subscribed_topic_) << "\n";

  if (!joy) {
    out << "waiting for Joy input\n";
    return out.str();
  }
  if (stale) {
    out << "stale input\n";
  }

  const int button_count = std::min<int>(joy->buttons.size(), max_buttons_property_->getInt());
  out << "buttons:";
  for (int i = 0; i < button_count; ++i) {
    out << " B" << i << "=" << (joy->buttons[i] ? "1" : "0");
  }
  out << "\n";

  const int axis_count = std::min<int>(joy->axes.size(), max_axes_property_->getInt());
  out << std::fixed << std::setprecision(2);
  for (int i = 0; i < axis_count; ++i) {
    const double value = clampAxis(joy->axes[i]);
    out << "A" << i << "=" << value;
    if (i + 1 < axis_count) {
      out << "  ";
    }
    if ((i + 1) % 4 == 0) {
      out << "\n";
    }
  }

  return out.str();
}

}  // namespace joy_overlay_tools

PLUGINLIB_EXPORT_CLASS(joy_overlay_tools::JoyOverlayDisplay, rviz::Display)

namespace joy_overlay_tools
{

class OpenPythonJoyOverlayTool : public rviz::Tool
{
public:
  void onInitialize() override
  {
    setName("Open Joy Overlay");
  }

  void activate() override
  {
    QProcess::startDetached("rosrun", QStringList() << "joy_overlay_tools" << "joy_overlay_visualizer.py");
    if (context_ && context_->getToolManager()) {
      context_->getToolManager()->setCurrentTool(nullptr);
    }
  }

  void deactivate() override {}
};

}  // namespace joy_overlay_tools

PLUGINLIB_EXPORT_CLASS(joy_overlay_tools::OpenPythonJoyOverlayTool, rviz::Tool)
