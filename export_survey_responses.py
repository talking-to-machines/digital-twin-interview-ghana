import psycopg2
import psycopg2.extras
import pandas as pd
import os

# This URL changes. Confirm it here if it's not working
# https://data.heroku.com/datastores
DATABASE_URL = os.getenv("DATABASE_URL")


def export_suvery_responses():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    df = pd.read_sql_query(
        "SELECT * FROM survey_responses ORDER BY timestamp ASC;", con=conn
    )
    conn.close()
    return df


survey_responses = export_suvery_responses()
survey_responses.to_csv("data/survey_responses.csv", index=False)
