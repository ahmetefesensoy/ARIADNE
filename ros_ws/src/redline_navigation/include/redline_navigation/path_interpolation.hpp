#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>
#include "nav_msgs/msg/path.hpp"

namespace redline_navigation
{
inline std::array<double, 4> unitQuaternion(const geometry_msgs::msg::Quaternion & q)
{
  std::array<double, 4> a{q.x, q.y, q.z, q.w};
  double norm = 0.0;
  for (double v : a) {norm += v * v;}
  if (!std::isfinite(norm) || norm < 1e-12) {
    throw std::invalid_argument("Invalid planner quaternion");
  }
  for (double & v : a) {v /= std::sqrt(norm);}
  return a;
}

// Retain every original vertex. Interpolate each existing segment separately;
// never shortcut a corner or create a new route through unknown space.
inline nav_msgs::msg::Path densifyPath(const nav_msgs::msg::Path & input, double step, double rotation_radius = 0.0)
{
  if (!std::isfinite(step) || step <= 0.0 || !std::isfinite(rotation_radius) || rotation_radius < 0.0) {
    throw std::invalid_argument("Interpolation step must be positive and finite");
  }
  constexpr size_t limit = 100000;
  nav_msgs::msg::Path out;
  out.header = input.header;
  if (input.poses.empty()) {return out;}
  for (const auto & p : input.poses) {
    const auto & v = p.pose.position;
    if (!std::isfinite(v.x) || !std::isfinite(v.y) || !std::isfinite(v.z)) {
      throw std::invalid_argument("Nonfinite planner position");
    }
    unitQuaternion(p.pose.orientation);
  }
  out.poses.push_back(input.poses.front());
  for (size_t i = 1; i < input.poses.size(); ++i) {
    const auto & a = input.poses[i - 1];
    const auto & b = input.poses[i];
    const auto & pa = a.pose.position;
    const auto & pb = b.pose.position;
    auto qa = unitQuaternion(a.pose.orientation);
    auto qb = unitQuaternion(b.pose.orientation);
    double dot = 0;
    for (size_t k = 0; k < 4; ++k) {dot += qa[k] * qb[k];}
    if (dot < 0) {for (double & v : qb) {v = -v;} dot = -dot;}
    dot = std::clamp(dot, 0.0, 1.0);
    double count = std::ceil((
      std::hypot(std::hypot(pb.x-pa.x, pb.y-pa.y), pb.z-pa.z) +
      2 * std::acos(dot) * rotation_radius) / step);
    if (!std::isfinite(count) || count > limit || out.poses.size() + count + 1 > limit) {
      throw std::length_error("Planner interpolation exceeds point budget");
    }
    size_t n = std::max<size_t>(1, static_cast<size_t>(count));
    for (size_t j = 1; j < n; ++j) {
      const double t = static_cast<double>(j) / n;
      auto pose = a;
      pose.pose.position.x = pa.x + t * (pb.x-pa.x);
      pose.pose.position.y = pa.y + t * (pb.y-pa.y);
      pose.pose.position.z = pa.z + t * (pb.z-pa.z);
      double wa = 1.0-t, wb = t;
      if (dot < 0.9995) {
        const double angle = std::acos(dot);
        wa = std::sin((1-t)*angle) / std::sin(angle);
        wb = std::sin(t*angle) / std::sin(angle);
      }
      geometry_msgs::msg::Quaternion q;
      q.x = wa*qa[0]+wb*qb[0]; q.y = wa*qa[1]+wb*qb[1];
      q.z = wa*qa[2]+wb*qb[2]; q.w = wa*qa[3]+wb*qb[3];
      auto normalized = unitQuaternion(q);
      q.x = normalized[0]; q.y = normalized[1]; q.z = normalized[2]; q.w = normalized[3];
      pose.pose.orientation = q;
      out.poses.push_back(pose);
    }
    out.poses.push_back(b);
  }
  return out;
}
}  // namespace redline_navigation
