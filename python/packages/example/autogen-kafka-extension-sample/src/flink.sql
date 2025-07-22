
-- Create Model

CREATE MODEL sentimentmodel
       INPUT(text STRING)
       OUTPUT(sentiment STRING) COMMENT 'sentiment analysis model'
       WITH (
          'provider' = 'openai',
          'task' = 'classification',
          'openai.connection' = 'openai-cli-connection',
          'openai.system_prompt' = 'You are specialized in sentiment analysis. Your job is to analyze the sentiment of the text and provide the sentiment score. The sentiment score is positive, negative, or neutral.'
        );

-- Insert the response from the model

INSERT INTO `agent_response_topic`
    SELECT s.key, s.id, ROW(p.sentiment) AS message, s.message_type
    FROM `agent_request_topic` AS s, LATERAL TABLE (ML_PREDICT('sentimentmodel', `message`.`text`)) AS p(sentiment)