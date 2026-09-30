-- Metadata only. Never export notebook names, cells, chat text or raw accounts.
-- Later identities may describe completed history, not the target's starting state.
WITH scoped AS MATERIALIZED (
 SELECT id,event_type,created_at,payload->>'conversation_id' AS conv_id,
   NULLIF(lower(btrim(user_email)),'') AS account,
   NULLIF(payload->>'notebook','') AS notebook,
   CASE WHEN event_type='tutor_query' THEN COALESCE(payload->>'question','')<>''
        WHEN event_type='tutor_response' THEN COALESCE(payload->>'response','')<>''
        ELSE false END AS has_chat
 FROM events
 WHERE created_at < CAST(:until AS timestamptz)
   AND payload->>'conversation_id' IN
       (SELECT jsonb_array_elements_text(CAST(:conversation_ids AS jsonb)))
   AND event_type IN ('tutor_query','tutor_response','tutor_notebook_info')
), identities AS (
 SELECT conv_id,count(*) AS events,
   array_agg(DISTINCT encode(sha256(convert_to(:salt || ':' || account,'UTF8')),'hex'))
     FILTER (WHERE account IS NOT NULL) AS account_ids,
   count(*) FILTER (WHERE account IS NULL) AS missing_identity_events
 FROM scoped GROUP BY conv_id
), chats AS (
 SELECT *,row_number() OVER (PARTITION BY conv_id ORDER BY created_at,id) AS chronological_rank,
   CASE WHEN notebook IS NOT NULL
     THEN encode(sha256(convert_to(:salt || ':notebook:' || notebook,'UTF8')),'hex')
     END AS notebook_id
 FROM scoped WHERE event_type IN ('tutor_query','tutor_response')
), grouped AS (
 SELECT conv_id,count(*) AS chat_events,
   min(created_at) AS chat_start,max(created_at) AS chat_end,
   count(*) FILTER (WHERE event_type='tutor_query' AND has_chat) AS queries,
   count(*) FILTER (WHERE event_type='tutor_response' AND has_chat) AS responses,
   array_agg(DISTINCT notebook_id ORDER BY notebook_id)
     FILTER (WHERE notebook_id IS NOT NULL) AS notebook_ids,
   count(*) FILTER (WHERE notebook_id IS NULL) AS missing_notebook_events,
   max(notebook_id) FILTER (WHERE chronological_rank=1) AS first_chat_notebook_id,
   min(id) FILTER (WHERE chronological_rank=1) AS first_chat_event_id
 FROM chats GROUP BY conv_id
)
SELECT g.*,i.events,i.account_ids,i.missing_identity_events
FROM grouped g JOIN identities i USING(conv_id)
ORDER BY g.conv_id
