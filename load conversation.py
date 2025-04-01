import psycopg2
import psycopg2.extras
import pandas as pd
import os

# This URL changes. Confirm it here if it's not working
# https://data.heroku.com/datastores
DATABASE_URL = os.getenv("DATABASE_URL")


def get_all_conversations():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    df = pd.read_sql_query(
        "SELECT * FROM conversation_logs ORDER BY timestamp ASC", con=conn
    )
    conn.close()
    return df


conversations = get_all_conversations()
conversations.to_csv("data/conversations.csv", index=False)
