#include <limits>
#include "gtest/gtest.h"
#include "redline_navigation/path_interpolation.hpp"
#include "redline_navigation/planner_geometry.hpp"

using redline_navigation::densifyPath;
geometry_msgs::msg::PoseStamped pose(double x, double y, double yaw = 0)
{
  geometry_msgs::msg::PoseStamped p;
  p.header.frame_id = "map";
  p.pose.position.x = x; p.pose.position.y = y;
  p.pose.orientation.z = std::sin(yaw/2); p.pose.orientation.w = std::cos(yaw/2);
  return p;
}
TEST(PathInterpolation, ActualSparseTenMetreRegression)
{
  nav_msgs::msg::Path path; path.header.frame_id = "map";
  path.poses = {pose(145, -289, -1.5708), pose(145, -299, -1.5708)};
  auto out = densifyPath(path, .2);
  ASSERT_GE(out.poses.size(), 51u);
  EXPECT_EQ(out.header, path.header);
  EXPECT_EQ(out.poses.front(), path.poses.front());
  EXPECT_EQ(out.poses.back(), path.poses.back());
  for (size_t i = 1; i < out.poses.size(); ++i) {
    auto a=out.poses[i-1].pose.position, b=out.poses[i].pose.position;
    EXPECT_LE(std::hypot(b.x-a.x, b.y-a.y), .20000001);
    EXPECT_DOUBLE_EQ(b.x, 145);
  }
}
TEST(PathInterpolation, CornersAndShortestQuaternionArc)
{
  nav_msgs::msg::Path path;
  path.poses = {pose(0, 0, 3.1), pose(1, 0, -3.1), pose(1, 1, -3.1)};
  auto out = densifyPath(path, .2);
  EXPECT_EQ(out.poses[5], path.poses[1]);
  for (const auto & p : out.poses) {
    EXPECT_TRUE(p.pose.position.y == 0 || p.pose.position.x == 1);
    EXPECT_NEAR(std::hypot(p.pose.orientation.z, p.pose.orientation.w), 1, 1e-12);
    EXPECT_GT(std::abs(p.pose.orientation.z), .99);
  }
}
TEST(PathInterpolation, RotationSweepHasBoundedFootprintTravel)
{
  nav_msgs::msg::Path path; path.poses={pose(1,1,0), pose(1,1,3.141592653589793)};
  auto out=densifyPath(path,.2,1.0);
  EXPECT_GE(out.poses.size(),17u);
  EXPECT_EQ(out.poses.front(),path.poses.front());
  EXPECT_EQ(out.poses.back(),path.poses.back());
}
TEST(PathInterpolation, EmptyDuplicateAndInvalidInputs)
{
  nav_msgs::msg::Path path;
  EXPECT_TRUE(densifyPath(path, .2).poses.empty());
  path.poses = {pose(1, 1), pose(1, 1)};
  EXPECT_EQ(densifyPath(path, .2).poses.size(), 2u);
  EXPECT_THROW(densifyPath(path, 0), std::invalid_argument);
  path.poses.back().pose.position.x = 2;
  EXPECT_THROW(densifyPath(path, 1e-12), std::length_error);
  path.poses.back().pose.position.x = std::numeric_limits<double>::infinity();
  EXPECT_THROW(densifyPath(path, .2), std::invalid_argument);
  path.poses = {pose(0, 0), pose(1, 0)};
  path.poses.back().pose.orientation.w = 0;
  EXPECT_THROW(densifyPath(path, .2), std::invalid_argument);
}

TEST(PathInterpolation, SameCoarseCellMustReachRequestedEndpoint)
{
  nav2_costmap_2d::Costmap2D map(10, 10, 4.0, 0, 0, 0);
  nav2_costmap_2d::Footprint footprint;
  for (auto xy : {std::array<double, 2>{-.5,-.5}, {.5,-.5}, {.5,.5}, {-.5,.5}}) {
    geometry_msgs::msg::Point p; p.x=xy[0]; p.y=xy[1]; footprint.push_back(p);
  }
  nav_msgs::msg::Path path; path.header.frame_id="map"; path.poses={pose(5,5)};
  path.poses.front().pose.position.z=-3598.5;
  auto goal=pose(7.5, 5);
  auto out=redline_navigation::checkedPath(path, goal, .2, map, footprint);
  EXPECT_EQ(out.poses.back().pose, goal.pose);
  EXPECT_GE(out.poses.size(), 14u);
  EXPECT_LT(out.poses.size(), 20u);
  EXPECT_DOUBLE_EQ(out.poses.front().pose.position.z,0.0);
  EXPECT_THROW(redline_navigation::checkedPath(path, goal, .3, map, footprint), std::invalid_argument);
  EXPECT_THROW(redline_navigation::checkedPath(path, goal, .2, map, {}), std::invalid_argument);
  EXPECT_THROW(redline_navigation::checkedPath(path, pose(9,5), .2, map, footprint),
    nav2_core::NoValidPathCouldBeFound);
  map.setCost(1, 1, nav2_costmap_2d::NO_INFORMATION);
  EXPECT_THROW(redline_navigation::checkedPath(path, goal, .2, map, footprint),
    nav2_core::NoValidPathCouldBeFound);
}

TEST(PathInterpolation, RejectObstacleAlongSegmentAndOutsideFootprint)
{
  nav2_costmap_2d::Costmap2D map(30, 30, .2, 0, 0, 0);
  nav2_costmap_2d::Footprint footprint;
  for (auto xy : {std::array<double,2>{-.3,-.3}, {.3,-.3}, {.3,.3}, {-.3,.3}}) {
    geometry_msgs::msg::Point p; p.x=xy[0]; p.y=xy[1]; footprint.push_back(p);
  }
  nav_msgs::msg::Path path; path.poses={pose(1,1), pose(5,1)};
  EXPECT_NO_THROW(redline_navigation::checkedPath(path, path.poses.back(), .2, map, footprint));
  map.setCost(15,5,nav2_costmap_2d::LETHAL_OBSTACLE);
  EXPECT_THROW(redline_navigation::checkedPath(path, path.poses.back(), .2, map, footprint),
    nav2_core::NoValidPathCouldBeFound);
  path.poses={pose(.1,.1),pose(1,1)};
  EXPECT_THROW(redline_navigation::checkedPath(path, path.poses.back(), .2, map, footprint),
    nav2_core::NoValidPathCouldBeFound);
}

TEST(PathInterpolation, InscribedInflationAppliesAtCenterNotAgainAtFootprintEdge)
{
  nav2_costmap_2d::Costmap2D map(30,30,.2,0,0,0);
  nav2_costmap_2d::Footprint footprint;
  for (auto xy : {std::array<double,2>{-.3,-.3}, {.3,-.3}, {.3,.3}, {-.3,.3}}) {
    geometry_msgs::msg::Point p; p.x=xy[0]; p.y=xy[1]; footprint.push_back(p);
  }
  nav_msgs::msg::Path path; path.poses={pose(2,2),pose(2,2)};
  map.setCost(11,10,nav2_costmap_2d::INSCRIBED_INFLATED_OBSTACLE);
  EXPECT_NO_THROW(redline_navigation::checkedPath(path,path.poses.back(),.2,map,footprint));
  map.setCost(10,10,nav2_costmap_2d::INSCRIBED_INFLATED_OBSTACLE);
  EXPECT_THROW(redline_navigation::checkedPath(path,path.poses.back(),.2,map,footprint),nav2_core::NoValidPathCouldBeFound);
  map.setCost(10,10,nav2_costmap_2d::FREE_SPACE);
  for (auto forbidden : {nav2_costmap_2d::LETHAL_OBSTACLE,nav2_costmap_2d::NO_INFORMATION}) {
    map.setCost(11,10,forbidden);
    EXPECT_THROW(redline_navigation::checkedPath(path,path.poses.back(),.2,map,footprint),nav2_core::NoValidPathCouldBeFound);
  }
}
