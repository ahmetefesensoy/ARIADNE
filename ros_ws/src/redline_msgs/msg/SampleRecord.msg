# SampleRecord.msg — proje.md section 5
std_msgs/Header header
string sample_id
string target_id
geometry_msgs/Point origin_point       # numunenin alındığı yer
geometry_msgs/Point analysis_point     # analiz sırasında araç/kişi
string tool
string container_id
uint8 SELECTED=0
uint8 REACH_OK=1
uint8 PRE_POSITIONED=2
uint8 READY=3
uint8 ACQUIRING=4
uint8 ACQUIRED=5
uint8 STOWED=6
uint8 RECORDED=7
uint8 FAILED=8
uint8 state
string[] evidence_ids
