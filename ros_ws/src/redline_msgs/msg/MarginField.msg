# MarginField.msg — proje.md section 5
std_msgs/Header header
string site_id
string crew_id
float32 resolution_m
geometry_msgs/Point origin
uint32 width
uint32 height
float32[] margin_min               # dakika; NaN = erişilemez
uint8 LIM_O2=0
uint8 LIM_CO2=1
uint8 LIM_WATER=2
uint8 LIM_BATTERY=3
uint8 LIM_DAYLIGHT=4
uint8 LIM_SHELTER=5
uint8[] limiting
float32 terminate_threshold_min
