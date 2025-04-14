import psycopg2
import psycopg2.extras
import pandas as pd
import os

# This URL changes. Confirm it here if it's not working
# https://data.heroku.com/datastores
DATABASE_URL = os.getenv("DATABASE_URL")


def export_conversation_logs():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    df = pd.read_sql_query(
        "SELECT * FROM conversation_logs ORDER BY timestamp ASC", con=conn
    )
    conn.close()
    return df


conversation_logs = export_conversation_logs()
conversation_logs.to_csv("data/conversation_logs.csv", index=False)
