-- Input IDs are frozen before content retrieval; references use a separate later request.
SELECT id, event_type, created_at, payload->>'conversation_id' AS conv_id,
  encode(sha256(convert_to(:salt || ':' || lower(btrim(user_email)), 'UTF8')), 'hex') AS account_id,
  encode(sha256(convert_to(:salt || ':notebook:' || (payload->>'notebook'), 'UTF8')), 'hex') AS notebook_id,
  CASE WHEN event_type='tutor_query' THEN payload->>'question'
       WHEN event_type='tutor_response' THEN payload->>'response' END AS text
FROM events
WHERE id IN (SELECT value::bigint FROM jsonb_array_elements_text(CAST(:event_ids AS jsonb)))
  AND created_at < CAST(:until AS timestamptz)
  AND event_type IN ('tutor_query','tutor_response')
ORDER BY id
