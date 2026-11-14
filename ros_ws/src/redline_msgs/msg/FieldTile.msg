# FieldTile.msg — proje.md section 5
std_msgs/Header header
string site_id
string name                        # "margin_min_EV1", "cell_state", "weh_percent"
string unit
float32 resolution_m
geometry_msgs/Point origin
uint32 width
uint32 height
float32 scale                      # değer = byte·scale + offset
float32 offset
uint8 nodata_byte
uint8[] png                        # 8 veya 16 bit gri PNG
