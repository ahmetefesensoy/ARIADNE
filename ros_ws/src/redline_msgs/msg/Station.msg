# Station.msg — proje.md section 5
string station_id
string target_id
geometry_msgs/Point position
float32 service_min
string[] tasks                     # "LIBS", "APXS", "PHOTO", "SAMPLE", "DAN", ...
float32 science_value
float32 window_open_pet_min
float32 window_close_pet_min
