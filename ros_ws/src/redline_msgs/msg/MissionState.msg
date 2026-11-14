# MissionState.msg — proje.md section 5
std_msgs/Header header
string run_id
string scenario_id
uint8 BRIEFING=0
uint8 PRECURSOR=1
uint8 TRAVERSE=2
uint8 STATION_SCIENCE=3
uint8 RETURN=4
uint8 CONTINGENCY=5
uint8 DEBRIEF=6
uint8 phase
string active_plan_id
string[] active_task_ids
float32 pet_min
