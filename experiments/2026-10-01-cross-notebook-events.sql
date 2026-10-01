-- Nonempty chat metadata only; no message text, notebook source or raw accounts.
SELECT id,event_type,created_at,payload->>'conversation_id' AS conv_id,
  CASE WHEN NULLIF(lower(btrim(user_email)),'') IS NOT NULL
    THEN encode(sha256(convert_to(:salt || ':' || lower(btrim(user_email)),'UTF8')),'hex')
    END AS account_id,
  CASE WHEN NULLIF(payload->>'notebook','') IS NOT NULL
    THEN encode(sha256(convert_to(:salt || ':notebook:' || (payload->>'notebook'),'UTF8')),'hex')
    END AS notebook_id
FROM events
WHERE created_at < CAST(:until AS timestamptz)
  AND payload->>'conversation_id' IN
    (SELECT jsonb_array_elements_text(CAST(:conversation_ids AS jsonb)))
  AND ((event_type='tutor_query' AND COALESCE(payload->>'question','')<>'')
    OR (event_type='tutor_response' AND COALESCE(payload->>'response','')<>''))
ORDER BY payload->>'conversation_id',id
