# CrewState.msg — proje.md section 5
std_msgs/Header header
string crew_id
geometry_msgs/PoseWithCovariance pose
Consumables consumables
float32 heart_rate_bpm
float32 suit_pressure_kpa
float32 ppco2_kpa
uint8 OK=0
uint8 SLOW=1
uint8 INCAPACITATED=2
uint8 status
