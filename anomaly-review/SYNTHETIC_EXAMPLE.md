# Synthetic Metrics Example

The fixture `fixtures/synthetic_sessions.json` contains invented data only. It demonstrates three question episodes:

| Question | Scenario | Elapsed span | Observed active | Before help | After help | Outcome |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| q1 | Two help responses, a 37-minute inactivity gap, later resumed work, and an intermediate subcheck pass | 2460 s | 70 s | 10 s | 60 s | Explicitly unfinished |
| q2 | Tutor response failed, a question check passed, and no final status was recorded | 60 s | Unknown | Unknown | Unknown | Unknown |
| q3 | One completed help response followed by one failed check and a later question pass | 132 s | 61 s | 10 s | 51 s | Explicitly completed |

Selected q1 activity metrics:

```json
{
  "tutor_request_count": 2,
  "completed_tutor_response_count": 2,
  "failed_checks_before_first_help": 1,
  "failed_checks_after_first_help": 1,
  "repeated_failure_count": 1,
  "code_edits_after_first_help": 2,
  "executions_after_first_help": 1,
  "continued_work_after_help": true,
  "resumed_work_after_help": true
}
```

Selected q3 recovery metrics:

```json
{
  "eventually_passed_question_check": true,
  "failed_checks_between_help_and_recovery": 1,
  "continued_work_after_help": true,
  "resumed_work_after_help": false,
  "question_outcome": "completed"
}
```

The exact expected values and evidence-reference checks are executable in `tests/test_metrics.py`.
