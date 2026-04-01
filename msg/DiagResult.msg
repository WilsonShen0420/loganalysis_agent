# Diagnostic result from LogDiag service
string  session_id          # Conversation session ID
string  summary             # One-line problem summary
string  timeline            # Anomaly timeline (JSON array string)
string  root_cause          # Root cause analysis
string  suggestions         # Recommended troubleshooting steps
string  raw_log_references  # Key log lines supporting the analysis
uint8   status              # 0=success, 1=no_anomaly, 2=error
string  error_message       # Error message (when status=2)

uint8 STATUS_SUCCESS=0
uint8 STATUS_NO_ANOMALY=1
uint8 STATUS_ERROR=2
