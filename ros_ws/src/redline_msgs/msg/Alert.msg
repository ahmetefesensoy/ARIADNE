# Alert.msg — proje.md section 5
std_msgs/Header header
string alert_id
uint8 INFO=0
uint8 CAUTION=1
uint8 WARNING=2
uint8 EMERGENCY=3
uint8 severity
string code                         # SEP_ALERT, SUIT_LEAK, LINK_LOSS, MARGIN_LOW, RULE_VIOLATION, ROBOT_HELP
string text
string[] related_ids
