# DoseRate.msg — proje.md section 5
std_msgs/Header header
float32 dose_rate_b_ugy_h
float32 dose_rate_e_ugy_h
float32 background_b_ugy_h
float32 background_e_ugy_h
bool alert
string alert_detector               # "B" veya "E"
int32 source_sol
string source_file
builtin_interfaces/Time historical_utc
float32 sky_view_factor             # topografik ölçek (1 = açık gökyüzü)
