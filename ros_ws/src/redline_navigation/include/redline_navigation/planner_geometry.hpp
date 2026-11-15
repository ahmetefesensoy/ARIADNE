#pragma once
#include <mutex>
#include <sstream>
#include "nav2_core/planner_exceptions.hpp"
#include "nav2_costmap_2d/footprint_collision_checker.hpp"
#include "nav2_costmap_2d/cost_values.hpp"
#include "redline_navigation/path_interpolation.hpp"

namespace redline_navigation
{
inline nav_msgs::msg::Path checkedPath(
  nav_msgs::msg::Path path, const geometry_msgs::msg::PoseStamped & goal,
  double step, nav2_costmap_2d::Costmap2D & map,
  const nav2_costmap_2d::Footprint & footprint,
  const geometry_msgs::msg::PoseStamped * actual_start = nullptr)
{
  if (path.poses.empty()) {return path;}
  if (!std::isfinite(step) || step <= 0 || step > 0.2) {
    throw std::invalid_argument("Collision sampling step must be in (0, 0.2] m");
  }
  if (footprint.size() < 3) {throw std::invalid_argument("Planner requires a polygon footprint");}
  double radius = 0;
  for (const auto & vertex : footprint) {
    if (!std::isfinite(vertex.x) || !std::isfinite(vertex.y)) {
      throw std::invalid_argument("Invalid footprint vertex");
    }
    radius = std::max(radius, std::hypot(vertex.x, vertex.y));
  }
  std::unique_lock<nav2_costmap_2d::Costmap2D::mutex_t> lock(*map.getMutex());
  if (path.poses.size() == 1) {
    // Jazzy Smac's same-cell special case returns the START position, even
    // when the requested goal is metres away inside a coarse cell.
    if (actual_start) {path.poses.front().pose = actual_start->pose;}
    // Nav2's route is planar, like Smac's normal (non-special-case) output.
    // Map/terrain altitude belongs to TF and independent physical evaluation.
    path.poses.front().pose.position.z = 0.0;
    const auto & start = path.poses.front().pose.position;
    if (!std::isfinite(start.x) || !std::isfinite(start.y) ||
      !std::isfinite(goal.pose.position.x) || !std::isfinite(goal.pose.position.y))
    {
      throw std::invalid_argument("Invalid same-cell endpoint");
    }
    unsigned int sx, sy, gx, gy;
    if (!map.worldToMap(start.x, start.y, sx, sy) ||
      !map.worldToMap(goal.pose.position.x, goal.pose.position.y, gx, gy) ||
      sx != gx || sy != gy)
    {
      throw nav2_core::NoValidPathCouldBeFound("Single-pose route is not in the goal cell");
    }
    auto endpoint = goal;
    endpoint.header = path.header;
    endpoint.pose.position.z = 0.0;
    path.poses.push_back(endpoint);
  }
  auto result = densifyPath(path, step, radius);
  nav2_costmap_2d::FootprintCollisionChecker<nav2_costmap_2d::Costmap2D *> checker(&map);
  for (const auto & p : result.poses) {
    const auto & v = p.pose.position;
    const auto q = unitQuaternion(p.pose.orientation);
    unsigned int mx, my;
    const double yaw = std::atan2(2*(q[3]*q[2]+q[0]*q[1]), 1-2*(q[1]*q[1]+q[2]*q[2]));
    const double footprint_cost = checker.footprintCostAtPose(v.x, v.y, yaw, footprint);
    if (!map.worldToMap(v.x, v.y, mx, my) ||
      map.getCost(mx, my) >= nav2_costmap_2d::INSCRIBED_INFLATED_OBSTACLE ||
      !std::isfinite(footprint_cost) || footprint_cost < 0 ||
      // 253 is a center-exclusion inflation cost, not occupied geometry at a
      // footprint edge. Match Jazzy Smac: reject center >=253, edge >=254.
      // Unknown (255), outside-map, and lethal cells remain rejected.
      footprint_cost >= nav2_costmap_2d::LETHAL_OBSTACLE)
    {
      std::ostringstream reason;
      reason << "Interpolated route hits occupied/unknown costmap at (" << v.x << ", " <<
        v.y << "), yaw=" << yaw << ", footprint_cost=" << footprint_cost;
      if (map.worldToMap(v.x, v.y, mx, my)) {
        reason << ", center_cost=" << static_cast<unsigned int>(map.getCost(mx, my));
      }
      throw nav2_core::NoValidPathCouldBeFound(reason.str());
    }
  }
  return result;
}
}  // namespace redline_navigation
