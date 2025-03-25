import psycopg2
import psycopg2.extras
import pandas as pd

# This URL changes. Confirm it here if it's not working
# https://data.heroku.com/datastores/482aaeb7-693d-4326-a3b9-624b169778fa#administration
DATABASE_URL = 'postgres://ijiqkniuryroff:fd8aac9db85e1780df907811ca31024fca05ea917f320b9a52dae9b5f06a77c3@ec2-44-211-104-233.compute-1.amazonaws.com:5432/d7l3ka6kqlbvth'

def get_all_conversations():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    df = pd.read_sql_query('SELECT * FROM conversation_logs ORDER BY timestamp ASC', con=conn)
    conn.close()
    return df

conversations = get_all_conversations()
conversations.to_csv('C:/Users/Piotr/Desktop/conversations.csv', index=False)