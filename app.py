from flask import Flask, render_template, request, session
import openai
import os
import psycopg2
from psycopg2 import sql
from datetime import datetime
from uuid import uuid4

app = Flask(__name__)

# Local or Heroku
local = False
if local:
    from dotenv import load_dotenv

    load_dotenv()

# Configuration variables (Needs to be set as environmental variables on Heroku)
DATABASE_URL = os.getenv["DATABASE_URL"]  # Make sure to set this environment variable
app.secret_key = os.getenv("APP_KEY")  # Set this to your desired secret key
openai.api_key = os.getenv(
    "OPENAI_API_KEY"
)  # Make sure to set this environment variable

# Local Settings
GPT_MODEL = "gpt-4o-mini"
TEMPERATURE = 1.0

# Prompt placeholders and their corresponding request arguments
prompt_placeholders = {
    "@sex": "sex",
    "@agev": "agev",
    "@education": "education",
    "@video_text_final": "video_text_final",
    "@convince": "convince",
    "@clear": "clear",
    "@zenzile": "zenzile",
    "@vzenzilev": "vzenzilev",
    "@sonja": "sonja",
    "@vsonjav": "vsonjav",
    "@henrico": "henrico",
    "@vhenricov": "vhenricov",
    "@narrator": "narrator",
    "@vnarratorv": "vnarratorv",
    "@emotion": "emotion",
    "@venjoyv": "venjoyv",
    "@vrealproblemv": "vrealproblemv",
    "@vhappenv": "vhappenv",
    "@q271": "q271",
    "@q272": "q272",
    "@q273": "q273",
    "@q274": "q274",
    "@source": "source",
    "@tone": "tone",
    "@socnorma": "socnorma",
    "@socnormc": "socnormc",
    "@cqindsoc": "cqindsoc",
}


with open("prompts/system_prompt.txt", "r") as file:
    system_prompt = file.read()


def load_conversation(user_id):
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    # Prepare the query for 'message'
    query_message = """
    SELECT 
        'user' as role, 
        message as content, 
        timestamp 
    FROM conversation_logs 
    WHERE 
        user_id = %s and 
        message is not null
    """

    # Execute the query for 'message'
    cur.execute(query_message, (user_id,))

    # Fetch all the rows for 'message'
    rows_message = cur.fetchall()

    # Prepare the query for 'response'
    query_response = """
    SELECT 
        'assistant' as role, 
        response as content, 
        timestamp 
    FROM conversation_logs 
    WHERE 
        user_id = %s and 
        response is not null
    """

    # Execute the query for 'response'
    cur.execute(query_response, (user_id,))

    # Fetch all the rows for 'response'
    rows_response = cur.fetchall()

    # Concatenate and sort the rows
    all_rows = sorted(rows_message + rows_response, key=lambda x: x[2])

    # Format the rows into the desired dictionary format
    session_messages = [{"role": row[0], "content": row[1]} for row in all_rows]

    cur.close()
    conn.close()
    return session_messages


def log_conversation(user_id, message, response):
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    insert = sql.SQL(
        "INSERT INTO conversation_logs (user_id, message, response, timestamp) "
        "VALUES (%s, %s, %s, %s)"
    )
    data = (user_id, message, response, datetime.now())

    cur.execute(insert, data)
    conn.commit()
    cur.close()
    conn.close()


def query_llm(session_messages: list) -> str:
    response = openai.ChatCompletion.create(
        model=GPT_MODEL,
        temperature=TEMPERATURE,
        messages=session_messages,
        frequency_penalty=0,
        presence_penalty=0.6,
        # max_tokens=256,
    )

    llm_response = response["choices"][0]["message"]["content"]
    return llm_response


@app.route("/", methods=["GET", "POST"])
def home():
    # Define the user id
    session_user_id = request.args.get("id", "")  # whatever the querystring is
    if session_user_id == "":
        session_user_id = str(uuid4())

    # Define the prompt to use
    condition = request.args.get("condition", "")  # whatever the querystring is
    print(f"Condition: {condition}")

    # case match treatment T1-T7 to read the relevant text file and assign to video_text_final
    treatment_files = {
        "T1": "prompts/T1.txt",
        "T2": "prompts/T2.txt",
        "T3": "prompts/T3.txt",
        "T4": "prompts/T4.txt",
        "T5": "prompts/T5.txt",
        "T6": "prompts/T6.txt",
        "T7": "prompts/T7.txt",
        "T8": "prompts/T8.txt",
        "T9": "prompts/T9.txt",
    }

    # Extract treatment script
    treatment = request.args.get("treatment", "")
    if treatment in treatment_files:
        with open(treatment_files[treatment], "r") as file:
            video_text_final = file.read()
    else:
        video_text_final = ""
    system_prompt = system_prompt.replace("@video_text_final", video_text_final)

    # Retrieve request arguments and replace placeholders in system_prompt
    for placeholder, arg_name in prompt_placeholders.items():
        value = request.args.get(arg_name, "")
        system_prompt = system_prompt.replace(placeholder, value)

    print(f"System Prompt: {system_prompt}")
    session_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello"},
        # {"role": "user", "content": session['prompt']},
    ]

    # Get the assistant's response
    assistant_response = query_llm(session_messages=session_messages)
    session_messages += [{"role": "assistant", "content": assistant_response}]

    # Write to database
    log_conversation(session_user_id, system_prompt, assistant_response)

    return render_template(
        "index_survey.html",
        assistant_message=assistant_response,
        user_id=session_user_id,
        condition=condition,
    )


@app.route("/get")
def get_bot_response():
    # Get the user's message and id
    user_text = request.args.get("msg")
    session_user_id = request.args.get("id", "")  # whatever the querystring is

    # Read conversation from database and append user message
    session_messages = load_conversation(session_user_id)
    session_messages += [{"role": "user", "content": user_text}]

    # Append the model's response
    model_message = query_llm(session_messages=session_messages)
    session_messages = session_messages + [
        {"role": "assistant", "content": model_message}
    ]

    # Log the conversation to the database
    log_conversation(session_user_id, user_text, model_message)

    # Return the model's response
    return str(model_message)


if __name__ == "__main__":
    app.run(debug=False)
