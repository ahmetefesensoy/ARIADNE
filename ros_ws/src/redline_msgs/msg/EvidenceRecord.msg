# EvidenceRecord.msg — proje.md section 5
std_msgs/Header header
string evidence_id
builtin_interfaces/Time measured
builtin_interfaces/Time received
string source                        # sensör veya ürün adı
Provenance provenance
geometry_msgs/PoseWithCovariance pose
float32 resolution_m
float32 quality                       # 0..1
string[] input_ids
string payload_uri
string summary_json
