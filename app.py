from flask import Flask, render_template, request, session
import openai
import os
import psycopg2
from psycopg2 import sql
from datetime import datetime
from uuid import uuid4

app = Flask(__name__)

# Database configuration
DATABASE_URL = os.environ['DATABASE_URL']  # Make sure to set this environment variable
app.secret_key = os.getenv("APP_KEY")  # Set this to your desired secret key
openai.api_key = os.getenv("OPENAI_API_KEY")  # Make sure to set this environment variable

# Local or Heroku
local = False
if local:
    from dotenv import load_dotenv
    load_dotenv("test3/.env")

# GPT Settings
# model_to_use = "gpt-3.5-turbo"
model_to_use = "gpt-4"
temperature = float(1)


with open('prompts/duch.txt', 'r') as file:
    duch = file.read()


    
def load_conversation(user_id):
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()

    # Prepare the query for 'message'
    query_message = """
    SELECT 'user' as role, message as content, timestamp 
    FROM conversation_logs 
    WHERE user_id = %s and message is not null
    """

    # Execute the query for 'message'
    cur.execute(query_message, (user_id,))

    # Fetch all the rows for 'message'
    rows_message = cur.fetchall()

    # Prepare the query for 'response'
    query_response = """
    SELECT 'assistant' as role, response as content, timestamp 
    FROM conversation_logs 
    WHERE user_id = %s and response is not null
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
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()

    insert = sql.SQL(
        "INSERT INTO conversation_logs (user_id, message, response, timestamp) VALUES (%s, %s, %s, %s)"
    )
    data = (user_id, message, response, datetime.now())

    cur.execute(insert, data)
    conn.commit()
    cur.close()
    conn.close()


@app.route('/', methods=['GET', 'POST'])
def home():
    # Define the user id
    session_user_id = request.args.get('id',"") # whatever the querystring is
    if session_user_id == "":
        session_user_id = str(uuid4())
    
    # Define the prompt to use    
    condition = request.args.get('condition',"") # whatever the querystring is
    
    print("the condition is: ", condition)
    #name = request.args.get('name',"") # whatever the querystring is
    #year = request.args.get('year',"") # whatever the querystring is
    #month = request.args.get('month',"") # whatever the querystring is
    agev = request.args.get("agev","")
    sex = request.args.get("sex","")
    education = request.args.get("education","")
    treatment = request.args.get("treatment","")
    
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
        "T9": "prompts/T9.txt"
    }

    # Read the file corresponding to the treatment
    video_text_final = ""
    if treatment in treatment_files:
        with open(treatment_files[treatment], 'r') as file:
            video_text_final = file.read()
    
    sex = request.args.get("sex","")
    education = request.args.get("education","")
    treatment = request.args.get("treatment","")
    convince = request.args.get("convince","")
    clear = request.args.get("clear","")
    zenzile = request.args.get("zenzile","")
    vzenzilev = request.args.get("vzenzilev","")
    sonja = request.args.get("sonja","")
    vsonjav = request.args.get("vsonjav","")
    henrico = request.args.get("henrico","")
    vhenricov = request.args.get("vhenricov","")
    narrator = request.args.get("narrator","")
    vnarratorv = request.args.get("vnarratorv","")
    emotion = request.args.get("emotion","")
    venjoyv = request.args.get("venjoyv","")
    vrealproblemv = request.args.get("vrealproblemv","")
    vhappenv = request.args.get("vhappenv","")
    q271 = request.args.get("q271","")
    q272 = request.args.get("q272","")
    q273 = request.args.get("q273","")
    q274 = request.args.get("q274","")
    source = request.args.get("source","")
    tone = request.args.get("tone","")
    socnorma = request.args.get("socnorma","")
    socnormc = request.args.get("socnormc","")
    cqindsoc = request.args.get("cqindsoc","")

    prompt_duch = duch.replace("@sex", sex)
    prompt_duch = prompt_duch.replace("@agev", agev)
    prompt_duch = prompt_duch.replace("@education", education)
    prompt_duch = prompt_duch.replace("@video_text_final",video_text_final)
    prompt_duch = prompt_duch.replace("@convince",convince)
    prompt_duch = prompt_duch.replace("@clear",clear)
    prompt_duch = prompt_duch.replace("@zenzile",zenzile)
    prompt_duch = prompt_duch.replace("@vzenzilev",vzenzilev)
    prompt_duch = prompt_duch.replace("@sonja",sonja)
    prompt_duch = prompt_duch.replace("@vsonjav",vsonjav)
    prompt_duch = prompt_duch.replace("@henrico",henrico)
    prompt_duch = prompt_duch.replace("@vhenricov",vhenricov)
    prompt_duch = prompt_duch.replace("@narrator",narrator)
    prompt_duch = prompt_duch.replace("@vnarratorv",vnarratorv)
    prompt_duch = prompt_duch.replace("@emotion",emotion)
    prompt_duch = prompt_duch.replace("@venjoyv",venjoyv)
    prompt_duch = prompt_duch.replace("@vrealproblemv",vrealproblemv)
    prompt_duch = prompt_duch.replace("@vhappenv",vhappenv)
    prompt_duch = prompt_duch.replace("@q271",q271)
    prompt_duch = prompt_duch.replace("@q272",q272)
    prompt_duch = prompt_duch.replace("@q273",q273)
    prompt_duch = prompt_duch.replace("@q274",q274)
    prompt_duch = prompt_duch.replace("@source",source)
    prompt_duch = prompt_duch.replace("@tone",tone)
    prompt_duch = prompt_duch.replace("@socnorma",socnorma)
    prompt_duch = prompt_duch.replace("@socnormc",socnormc)
    prompt_duch = prompt_duch.replace("@cqindsoc",cqindsoc)


    
    prompt = prompt_duch
    print("the prompt is: ", prompt)
    messages = [
        # {"role": "system", "content": prompt},
        # {"role": "user", "content": ""},
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Hello"},
        # {"role": "user", "content": session['prompt']},
    ]

    # Initialize conversation
    response = openai.ChatCompletion.create(
        model=model_to_use,
        temperature=temperature,
        messages=messages,
        frequency_penalty=0,
        presence_penalty=0.6,
        # max_tokens=256,
    )

    # Get the assistant's response
    assistant_message = response['choices'][0]['message']['content']
    session_messages = messages
    session_messages = session_messages + [{"role": "assistant", "content": assistant_message}]
    
    # Write to database
    log_conversation(session_user_id, prompt, assistant_message)

    return render_template('index2.html',  assistant_message=assistant_message, user_id = session_user_id, condition = condition)

@app.route('/get')
def get_bot_response():
    # Get the user's message and id
    user_text = request.args.get('msg')
    session_user_id = request.args.get('id',"") # whatever the querystring is
    
    # Read conversation from database and append user message
    session_messages = load_conversation(session_user_id)
    session_messages = session_messages + [{"role": "user", "content": user_text}]

    # Get a response from the model
    response = openai.ChatCompletion.create(
        model=model_to_use,
        temperature=temperature,
        messages=session_messages,
        max_tokens=256,
        frequency_penalty=0,
        presence_penalty=0.6,
        # max_tokens=256,
    )

    # Append the model's response
    model_message = response['choices'][0]['message']['content']
    session_messages = session_messages + [{"role": "assistant", "content": model_message}]
    
    # Log the conversation to the database
    log_conversation(session_user_id, user_text, model_message)
    
    # Return the model's response
    return str(model_message)

if __name__ == "__main__":
    app.run(debug=False)