// Evaluation only: observe an RViz goal and its actual DDS writer, never command.
// Jazzy rclpy omits publisher_gid from callback metadata; rclcpp preserves it.
#include <algorithm>
#include <iomanip>
#include <memory>
#include <sstream>
#include <string>

#include <geometry_msgs/msg/pose_stamped.hpp>
#include <nlohmann/json.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>

class RvizGoalObserver : public rclcpp::Node
{
public:
  RvizGoalObserver() : Node("rviz_goal_observer")
  {
    const auto goal_topic = declare_parameter<std::string>("goal_topic", "/rover_1/goal_pose");
    const auto evidence_topic = declare_parameter<std::string>(
      "evidence_topic", "/redline/t3/rviz_goal_evidence");
    evidence_ = create_publisher<std_msgs::msg::String>(evidence_topic, 10);
    goal_ = create_subscription<geometry_msgs::msg::PoseStamped>(goal_topic, 10,
      [this, goal_topic](geometry_msgs::msg::PoseStamped::ConstSharedPtr pose,
      const rclcpp::MessageInfo & info) {observe(goal_topic, *pose, info);});
  }

private:
  void observe(const std::string & topic, const geometry_msgs::msg::PoseStamped & pose,
    const rclcpp::MessageInfo & info)
  {
    const auto & metadata = info.get_rmw_message_info();
    const auto & gid = metadata.publisher_gid;
    if (std::all_of(std::begin(gid.data), std::end(gid.data), [](auto b) {return b == 0;})) {
      return;
    }
    for (const auto & endpoint : get_publishers_info_by_topic(topic)) {
      if (!std::equal(endpoint.endpoint_gid().begin(), endpoint.endpoint_gid().end(), gid.data)) {
        continue;
      }
      if (endpoint.node_name() != "rviz_navigation" && endpoint.node_name() != "rviz2") {
        return;
      }
      std::ostringstream hex;
      hex << std::hex << std::setfill('0');
      for (auto byte : gid.data) {hex << std::setw(2) << static_cast<unsigned>(byte);}
      const auto & p = pose.pose.position;
      const auto & q = pose.pose.orientation;
      const nlohmann::json value = {
        {"schema", "redline.t3.rviz-goal.v1"}, {"goal_topic", topic},
        {"source_timestamp_ns", metadata.source_timestamp},
        {"publisher", {{"node_name", endpoint.node_name()},
          {"node_namespace", endpoint.node_namespace()}, {"publisher_gid", hex.str()}}},
        {"pose", {{"stamp_sec", pose.header.stamp.sec},
          {"stamp_nanosec", pose.header.stamp.nanosec}, {"frame_id", pose.header.frame_id},
          {"position", {p.x, p.y, p.z}}, {"orientation", {q.x, q.y, q.z, q.w}}}}
      };
      std_msgs::msg::String message;
      message.data = value.dump();
      evidence_->publish(message);
      RCLCPP_INFO(get_logger(), "Observed RViz goal from %s%s GID=%s",
        endpoint.node_namespace().c_str(), endpoint.node_name().c_str(), hex.str().c_str());
      return;
    }
    RCLCPP_WARN(get_logger(), "Goal DDS writer is unresolved; no acceptance evidence emitted");
  }

  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr evidence_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr goal_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<RvizGoalObserver>());
  rclcpp::shutdown();
  return 0;
}
