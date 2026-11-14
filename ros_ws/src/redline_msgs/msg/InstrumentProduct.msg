# InstrumentProduct.msg — proje.md section 5
std_msgs/Header header
string product_id
string instrument                     # "APXS", "LIBS", "MSPEC", "DAN", "DOSIMETER", "WEATHER", "CAMERA"
string target_id
geometry_msgs/PoseWithCovariance instrument_pose
geometry_msgs/Point target_point
float32 integration_s
Provenance provenance
string payload_uri                    # data/products/... (JSON + PDS4 benzeri etiket)
string summary_json
