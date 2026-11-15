#include "nav2_core/global_planner.hpp"
#include "pluginlib/class_loader.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "redline_navigation/planner_geometry.hpp"

namespace redline_navigation
{
class InterpolatingPlanner : public nav2_core::GlobalPlanner
{
public:
  void configure(
    const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
    std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
    std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap) override
  {
    auto node = parent.lock();
    if (!node) {throw std::runtime_error("Planner lifecycle node expired");}
    if (!node->has_parameter(name + ".delegate_plugin")) {
      node->declare_parameter(name + ".delegate_plugin", "nav2_smac_planner::SmacPlannerHybrid");
    }
    if (!node->has_parameter(name + ".densification_step")) {
      node->declare_parameter(name + ".densification_step", 0.2);
    }
    const auto plugin = node->get_parameter(name + ".delegate_plugin").as_string();
    if (plugin != "nav2_smac_planner::SmacPlannerHybrid") {
      throw std::invalid_argument("Only SmacPlannerHybrid delegation is supported");
    }
    step_ = node->get_parameter(name + ".densification_step").as_double();
    if (!std::isfinite(step_) || step_ <= 0 || step_ > .2) {throw std::invalid_argument("Interpolation step must be in (0, 0.2] m");}
    loader_ = std::make_unique<pluginlib::ClassLoader<nav2_core::GlobalPlanner>>(
      "nav2_core", "nav2_core::GlobalPlanner");
    delegate_ = loader_->createSharedInstance(plugin);
    costmap_ = costmap;
    delegate_->configure(parent, name, tf, costmap);
  }
  void cleanup() override {delegate_->cleanup(); delegate_.reset(); loader_.reset(); costmap_.reset();}
  void activate() override {delegate_->activate();}
  void deactivate() override {delegate_->deactivate();}
  nav_msgs::msg::Path createPlan(
    const geometry_msgs::msg::PoseStamped & start,
    const geometry_msgs::msg::PoseStamped & goal, std::function<bool()> cancel_checker) override
  {
    auto path = delegate_->createPlan(start, goal, cancel_checker);
    if (cancel_checker()) {throw nav2_core::PlannerCancelled("Planning canceled before interpolation");}
    return checkedPath(path, goal, step_, *costmap_->getCostmap(), costmap_->getRobotFootprint(), &start);
  }
private:
  double step_{0.2};
  std::unique_ptr<pluginlib::ClassLoader<nav2_core::GlobalPlanner>> loader_;
  std::shared_ptr<nav2_core::GlobalPlanner> delegate_;
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_;
};
}  // namespace redline_navigation
PLUGINLIB_EXPORT_CLASS(redline_navigation::InterpolatingPlanner, nav2_core::GlobalPlanner)
