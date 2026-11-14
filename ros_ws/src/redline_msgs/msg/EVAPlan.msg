# EVAPlan.msg — proje.md section 5
std_msgs/Header header
string plan_id
uint32 version
string site_id
string[] crew_ids
Station[] stations
PlanLeg[] legs
nav_msgs/Path route
float32 total_duration_min
string decision_id
