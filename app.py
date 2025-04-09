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
DATABASE_URL = os.getenv("DATABASE_URL")  # Make sure to set this environment variable
app.secret_key = os.getenv("APP_KEY")  # Set this to your desired secret key
openai.api_key = os.getenv(
    "OPENAI_API_KEY"
)  # Make sure to set this environment variable

# Local Settings
GPT_MODEL = "gpt-4o-mini"
TEMPERATURE = 1.0

# Prompt placeholders and their corresponding request arguments
prompt_placeholders = {
    # Admin - Respondent Identification
    "@last_name": "last_name",
    "@id_card": "id_card",
    "@phone_number": "phone_number",
    "@phone_owner": "phone_owner",
    "@phone_number_backup": "phone_number_backup",
    # Admin - Social Media Account
    "@consent_social_media": "consent_social_media",
    "@twitter": "twitter",
    "@tiktok": "tiktok",
    # Demographics Quota
    "@ethnicity": "ethnicity",  # Which ethnicity best describes you?
    "@ethnicity_other": "ethnicity_other",  # Please specify
    # Demographics
    "@Q1_1": "Q1_1",  # What is your current age?
    "@Q1_2": "Q1_2",  # What is your gender?
    "@Q1_3": "Q1_3",  # What is your current working situation?
    "@Q1_4": "Q1_4",  # How much on average does your household spend in a typical week on food?
    "@Q1_5": "Q1_5",  # How much on average does your household spend in a typical week on non-food items (electricity, water, rent, school fees)?
    "@Q1_6": "Q1_6",  # How would you rate the overall economic or financial condition of your household today?
    "@Q1_7": "Q1_7",  # What is the highest educational qualification you have completed?
    "@Q1_8": "Q1_8",  # Do you live with a spouse or partner?
    # Network Density Question
    "@Q2": "Q2",  # How many individuals can you identify in your social network? Think of friends and relatives that live close to you
    # Media Use
    "@Q3_1": "Q3_1",  # Do you have WhatsApp?
    "@Q3_2": "Q3_2",  # How often do you use WhatsApp?
    "@Q3_3": "Q3_3",  # You have WhatsApp groups with...
    "@Q3_4": "Q3_4",  # What social media have you used in the last year? Please select all that apply.
    "@Q3_5": "Q3_5",  # How often do you use social media?
    # Health
    "@Q4_1": "Q4_1",  # Thinking now about health matters, please indicate your familiarity with each of these health problems.
    "@Q4_2": "Q4_2",  # Do you have any of the following underlying health conditions? Please select all that apply.
    "@Q4_3": "Q4_3",  # How is your health in general? Is it...
    "@Q4_4": "Q4_4",  # Please indicate for each of the five statements which is closest to how you have been feeling over the last two weeks. Notice that higher numbers mean better well-being. Example: If you have felt cheerful and in good spirits more than half of the time during the last two weeks, select the circle with the number 3.
    # Afrobarometer
    "@Q5_1": "Q5_1",  # How much do you trust the following people?
    "@Q5_2": "Q5_2",  # How much do you trust the following institutions?
    "@Q5_3": "Q5_3",  # How much do you trust the following non-governmental organizations?
    # TB EQ-5D
    "@Q6_2": "Q6_2",  # Your mobility TODAY
    "@Q6_3": "Q6_3",  # Your self-care TODAY
    "@Q6_4": "Q6_4",  # Your usual activities TODAY (e.g. work, study, housework, family or leisure activities)
    "@Q6_5": "Q6_5",  # Your pain / discomfort TODAY
    "@Q6_6": "Q6_6",  # Your anxiety / depression TODAY
    "@Q6_8": "Q6_8",  # Please tap on the scale how your health is TODAY
    # Video Questions
    "@open_video": "open_video",  # We would like to get you thoughts about giving vaccinations at an early age to children. In your own words could you tell us whether you think this is a good idea. Are there real benefits to doing this? Are there any risks?
    "@Q8_6": "Q8_6",  # What was the topic of the video?
    "@Q8_2": "Q8_2",  # Please indicate how much you agree or disagree with the following statement: The content of the video is convincing.
    "@Q8_4": "Q8_4",  # Please indicate how much you agree or disagree with the following statement: The content of the video is clear.
    "@Q8_5": "Q8_5",  # Please indicate how much you agree or disagree with the following statement: The content of the video is accurate.
    "@Q240": "Q240",  # Thinking broadly about vaccines, please indicate how much you agree or disagree with the following statement: Vaccines are created too quickly.
    "@Q241": "Q241",  # Thinking broadly about vaccines, please indicate how much you agree or disagree with the following statement: Vaccines have potential side effects.
    "@Q239": "Q239",  # Thinking broadly about vaccines, please indicate how much you agree or disagree with the following statement: Vaccines are effective.
    "@Q8_8": "Q8_8",  # On a scale of 1 to 7, where 1 means "not informative about the measles vaccination for young children" and 7 means "very informative about the measles vaccination for young children", how would you rate the video you just watched?
    "@Q242": "Q242",  # Please indicate how much you agree or disagree with the following statement: Measles is a serious threat.
    "@Q243": "Q243",  # Please indicate how much you agree or disagree with the following statement: The dangers of measles are exaggerated by media.
    "@Q244": "Q244",  # Please indicate how much you agree or disagree with the following statement: A vaccine for measles should not be trusted.
    "@Q8_9": "Q8_9",  # On a scale of 1 to 7, where 1 means "early vaccinations are not important for the health of children" and 7 means "early vaccinations are very important for the health of children", how would you rate the importance of early vaccinations for children’s health?
    "@Q8_7": "Q8_7",  # According to the video at what age should children receive their first measles (MMR) vaccination?
}


def load_conversation(user_id) -> list:
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


def load_survey_responses(user_id: str) -> dict:
    if not user_id:  # Verify that user_id is valid
        raise ValueError("user_id cannot be empty")

    try:
        # Use a context manager for the database connection and cursor
        with psycopg2.connect(DATABASE_URL, sslmode="require") as conn:
            with conn.cursor() as cur:

                # Prepare the query for getting past survey responses
                query_message = """
                SELECT 
                    *
                FROM survey_responses 
                WHERE 
                    user_id = %s
                """

                # Execute the query for past survey responses
                cur.execute(query_message, (user_id,))

                # Fetch the first row from the result
                row = cur.fetchone()

                if not row:
                    return {}

                # Get column names from the cursor description
                column_names = [desc[0] for desc in cur.description]

                # Format the row into a dictionary
                survey_response_dict = dict(zip(column_names, row))

                return survey_response_dict

    except Exception as e:
        print(f"Error loading survey responses: {e}")
        return {}


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


def log_survey_responses(user_id: str, survey_responses) -> None:
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        insert = sql.SQL(
            "INSERT INTO survey_responses (user_id, last_name, id_card, phone_number, phone_owner, phone_number_backup, consent_social_media, twitter, tiktok, ethnicity, ethnicity_other, Q1_1, Q1_2, Q1_3, Q1_4, Q1_5, Q1_6, Q1_7, Q1_8, Q2, Q3_1, Q3_2, Q3_3, Q3_4, Q3_5, Q4_1, Q4_2, Q4_3, Q4_4, Q5_1, Q5_2, Q5_3, Q6_2, Q6_3, Q6_4, Q6_5, Q6_6, Q6_8, open_video, Q8_6, Q8_2, Q8_4, Q8_5, Q240, Q241, Q239, Q8_8, Q242, Q243, Q244, Q8_9, Q8_7, timestamp) "
            "VALUES (%s, %s, %s, %s)"
        )
        data = (
            user_id,
            survey_responses.args.get("last_name", ""),
            survey_responses.args.get("id_card", ""),
            survey_responses.args.get("phone_number", ""),
            survey_responses.args.get("phone_owner", ""),
            survey_responses.args.get("phone_number_backup", ""),
            survey_responses.args.get("consent_social_media", ""),
            survey_responses.args.get("twitter", ""),
            survey_responses.args.get("tiktok", ""),
            survey_responses.args.get("ethnicity", ""),
            survey_responses.args.get("ethnicity_other", ""),
            survey_responses.args.get("Q1_1", ""),
            survey_responses.args.get("Q1_2", ""),
            survey_responses.args.get("Q1_3", ""),
            survey_responses.args.get("Q1_4", ""),
            survey_responses.args.get("Q1_5", ""),
            survey_responses.args.get("Q1_6", ""),
            survey_responses.args.get("Q1_7", ""),
            survey_responses.args.get("Q1_8", ""),
            survey_responses.args.get("Q2", ""),
            survey_responses.args.get("Q3_1", ""),
            survey_responses.args.get("Q3_2", ""),
            survey_responses.args.get("Q3_3", ""),
            survey_responses.args.get("Q3_4", ""),
            survey_responses.args.get("Q3_5", ""),
            survey_responses.args.get("Q4_1", ""),
            survey_responses.args.get("Q4_2", ""),
            survey_responses.args.get("Q4_3", ""),
            survey_responses.args.get("Q4_4", ""),
            survey_responses.args.get("Q5_1", ""),
            survey_responses.args.get("Q5_2", ""),
            survey_responses.args.get("Q5_3", ""),
            survey_responses.args.get("Q6_2", ""),
            survey_responses.args.get("Q6_3", ""),
            survey_responses.args.get("Q6_4", ""),
            survey_responses.args.get("Q6_5", ""),
            survey_responses.args.get("Q6_6", ""),
            survey_responses.args.get("Q6_8", ""),
            survey_responses.args.get("open_video", ""),
            survey_responses.args.get("Q8_6", ""),
            survey_responses.args.get("Q8_2", ""),
            survey_responses.args.get("Q8_4", ""),
            survey_responses.args.get("Q8_5", ""),
            survey_responses.args.get("Q240", ""),
            survey_responses.args.get("Q241", ""),
            survey_responses.args.get("Q239", ""),
            survey_responses.args.get("Q8_8", ""),
            survey_responses.args.get("Q242", ""),
            survey_responses.args.get("Q243", ""),
            survey_responses.args.get("Q244", ""),
            survey_responses.args.get("Q8_9", ""),
            survey_responses.args.get("Q8_7", ""),
            datetime.now(),
        )

        cur.execute(insert, data)
        conn.commit()

    except Exception as e:
        print(f"Error logging survey responses: {e}")

    finally:
        cur.close()
        conn.close()


def query_llm(messages: list) -> str:
    response = openai.ChatCompletion.create(
        model=GPT_MODEL,
        temperature=TEMPERATURE,
        messages=messages,
        frequency_penalty=0,
        presence_penalty=0.6,
    )

    llm_response = response["choices"][0]["message"]["content"]
    return llm_response


def summarise_interview_responses(
    past_interview_responses: list,
) -> str:
    # Combine past_interview_responses into a single string
    past_interview_responses_str = "\n".join(
        [f"{item['role']}: {item['content']}" for item in past_interview_responses]
    )

    # Read the summarisation prompt from the file
    with open("prompts/summarisation_prompt.txt", "r") as file:
        summarisation_prompt = file.read()

    messages = [
        {"role": "system", "content": summarisation_prompt},
        {"role": "user", "content": past_interview_responses_str},
    ]

    summarised_interview_response = query_llm(messages=messages)

    return summarised_interview_response


@app.route("/", methods=["GET", "POST"])
def home():
    # Define the user id
    session_user_id = request.args.get("user_id", "")  # whatever the querystring is
    if session_user_id == "":
        session_user_id = str(uuid4())

    # Check if user has already undergone the survey
    past_survey_responses = load_survey_responses(session_user_id)

    # Extract system prompt template and replace placeholders with request arguments
    if past_survey_responses:  # Subsequent round of interview
        with open("prompts/system_prompt_followup_interview.txt", "r") as file:
            system_prompt = file.read()

            # Extract user's past interview responses
            past_interview_responses = load_conversation(session_user_id)

            # Summarise past responses
            summarised_interview_responses = summarise_interview_responses(
                past_interview_responses=past_interview_responses
            )

            # Replace placeholders in system_prompt with past responses
            system_prompt = system_prompt.replace(
                "@summarised_interview_responses", summarised_interview_responses
            )

            # Replace placeholders in system_prompt with survey responses collected from previous rounds
            for question, response in past_survey_responses.items():
                system_prompt = system_prompt.replace(f"Q{question}", response)

    else:  # Initial round of interview
        with open("prompts/system_prompt_initial_interview.txt", "r") as file:
            system_prompt = file.read()

        log_survey_responses(user_id=session_user_id, survey_responses=request)

    # Retrieve request arguments and replace placeholders in system_prompt
    for placeholder, arg_name in prompt_placeholders.items():
        value = request.args.get(arg_name, "NA")

        if value:
            system_prompt = system_prompt.replace(placeholder, value)

    print(f"System Prompt: {system_prompt}")
    session_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello"},
    ]

    # Get the assistant's response
    assistant_response = query_llm(messages=session_messages)
    session_messages += [{"role": "assistant", "content": assistant_response}]

    # Write to database
    log_conversation(session_user_id, system_prompt, assistant_response)

    return render_template(
        "index_survey.html",
        assistant_message=assistant_response,
        user_id=session_user_id,
    )


@app.route("/get")
def get_bot_response():
    # Get the user's message and id
    user_text = request.args.get("msg")
    session_user_id = request.args.get("user_id", "")  # whatever the querystring is

    # Read conversation from database and append user message
    session_messages = load_conversation(session_user_id)
    session_messages += [{"role": "user", "content": user_text}]

    # Append the model's response
    model_message = query_llm(messages=session_messages)
    session_messages = session_messages + [
        {"role": "assistant", "content": model_message}
    ]

    # Log the conversation to the database
    log_conversation(session_user_id, user_text, model_message)

    # Return the model's response
    return str(model_message)


if __name__ == "__main__":
    app.run(debug=False)
