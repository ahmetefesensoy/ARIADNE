# RedLine.msg — proje.md section 5
std_msgs/Header header
string site_id
geometry_msgs/Polygon[] abort_regions      # margin >= 0 sınırı (kırmızı)
geometry_msgs/Polygon[] terminate_regions  # margin >= T_term sınırı (sarı)
string limiting_crew_id
uint8 limiting_consumable                  # MarginField.LIM_*
float32 margin_now_min
