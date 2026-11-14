# ScalarField.msg — proje.md section 5
std_msgs/Header header
string site_id
string name                        # "margin_min_EV1", "weh_percent", ...
string unit
float32 resolution_m
geometry_msgs/Point origin
uint32 width
uint32 height
float32[] data                     # satır-öncelikli, NaN = veri yok
float32[] sigma                    # boş olabilir
Provenance provenance
