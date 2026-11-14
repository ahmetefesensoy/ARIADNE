# CellDelta.msg — proje.md section 5
std_msgs/Header header             # frame_id = map
string site_id
float32 resolution_m
geometry_msgs/Point origin         # ızgara (0,0) köşesi, map frame
CellState[] cells
