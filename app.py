import openai
import os
import psycopg2
import logging
from flask import Flask, render_template, request, session
from psycopg2 import sql
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler("app.log", mode="a"),  # Log to a file (append mode)
    ],
)

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
GPT_MODEL = "gpt-4o"
TEMPERATURE = 0.0

# Prompt placeholders and their corresponding request arguments
prompt_placeholders = {
    # Admin - Respondent Identification
    "@user_id": "user_id",
    "@country": "country",
    "@email_recontact": "email_recontact",
    "@first_name": "first_name",
    "@last_name": "last_name",
    "@phone_number": "phone_number",
    "@phone_owner": "phone_owner",
    "@phone_number_backup": "phone_number_backup",
    # Admin - Social Media Account
    "@consent_social_media": "consent_social_media",
    "@has_paypal": "has_paypal",
    "@paypal_email": "paypal_email",
    "@paypal_email_confirm": "paypal_email_confirm",
    "@twitter": "twitter",
    "@tiktok": "tiktok",
    # Demographics Quota
    "@ethnicity": "ethnicity",
    "@ethnicity_other": "ethnicity_other",
    "@UK_region": "UK_region",
    "@UK_district": "UK_district",
    "@US_state": "US_state",
    "@US_county": "US_county",
    "@zip": "zip",
    # Demographics
    "@Q1_1": "Q1_1",
    "@Q1_2": "Q1_2",
    "@gender_other": "gender_other",
    "@Q1_3": "Q1_3",
    "@Q1_4": "Q1_4",
    "@Q1_5": "Q1_5",
    "@Q1_6": "Q1_6",
    "@Q1_7": "Q1_7",
    "@Q1_8": "Q1_8",
    # Network Density Question
    "@Q2": "Q2",
    # Media Use
    "@Q3_1": "Q3_1",
    "@Q3_2": "Q3_2",
    "@Q3_3": "Q3_3",
    "@Q3_4": "Q3_4",
    "@Q3_5": "Q3_5",
    # Health
    "@familiarity_tuberculosis": "familiarity_tuberculosis",
    "@familiarity_mumps": "familiarity_mumps",
    "@familiarity_polio": "familiarity_polio",
    "@familiarity_pneumococcal": "familiarity_pneumococcal",
    "@familiarity_rotavirus": "familiarity_rotavirus",
    "@familiarity_rsv": "familiarity_rsv",
    "@familiarity_rubella": "familiarity_rubella",
    "@familiarity_tetanus": "familiarity_tetanus",
    "@familiarity_whooping_cough": "familiarity_whooping_cough",
    "@familiarity_influenza": "familiarity_influenza",
    "@familiarity_diphtheria": "familiarity_diphtheria",
    "@familiarity_meningitis": "familiarity_meningitis",
    "@familiarity_hepatitis_a": "familiarity_hepatitis_a",
    "@familiarity_hepatitis_b": "familiarity_hepatitis_b",
    "@familiarity_hpv": "familiarity_hpv",
    "@familiarity_shingles": "familiarity_shingles",
    "@Q4_2": "Q4_2",
    "@Q4_3": "Q4_3",
    "@wellbeing_cheerful": "wellbeing_cheerful",
    "@wellbeing_calm": "wellbeing_calm",
    "@wellbeing_active": "wellbeing_active",
    "@wellbeing_fresh": "wellbeing_fresh",
    "@wellbeing_interested": "wellbeing_interested",
    # Afrobarometer
    "@trust_relatives": "trust_relatives",
    "@trust_neighbors": "trust_neighbors",
    "@trust_own_tribe": "trust_own_tribe",
    "@trust_other_tribes": "trust_other_tribes",
    "@trust_chiefs": "trust_chiefs",
    "@trust_district_assemblies": "trust_district_assemblies",
    "@trust_police": "trust_police",
    "@trust_courts": "trust_courts",
    "@trust_parties": "trust_parties",
    "@trust_army": "trust_army",
    "@trust_parliament": "trust_parliament",
    "@trust_president": "trust_president",
    "@trust_gbc": "trust_gbc",
    "@trust_electoral_commission": "trust_electoral_commission",
    "@trust_churches": "trust_churches",
    "@trust_mosques": "trust_mosques",
    "@trust_unions": "trust_unions",
    "@trust_banks": "trust_banks",
    "@trust_businesses": "trust_businesses",
    # TB EQ-5D
    "@Q6_2": "Q6_2",
    "@Q6_3": "Q6_3",
    "@Q6_4": "Q6_4",
    "@Q6_5": "Q6_5",
    "@Q6_6": "Q6_6",
    "@Q6_8": "Q6_8",
    # Video Questions
    "@open_video": "open_video",
    "@Q8_2": "Q8_2",
    "@Q8_3": "Q8_3",
    "@Q8_4": "Q8_4",
    "@Q8_5": "Q8_5",
    "@Q8_6": "Q8_6",
    "@Q8_7": "Q8_7",
    "@Q8_8": "Q8_8",
    "@Q8_9": "Q8_9",
    "@Q8_10": "Q8_10",
    "@Q8_11": "Q8_11",
    "@Q8_12": "Q8_12",
    "@Q8_13": "Q8_13",
    "@Q8_14": "Q8_14",
}


def load_conversation(user_id: str, country: str) -> list:
    """Load and retrieve a user's conversation history from the database.

    This function fetches messages and responses for a specific user and country
    from the `conversation_logs` table in the database. The messages and responses
    are combined, sorted by their timestamp, and returned in a structured format.

    Args:
        user_id (str): The unique identifier of the user.
        country (str): The country associated with the user's conversation.

    Returns:
        list: A list of dictionaries representing the conversation history. Each
              dictionary contains the following keys:
              - "role" (str): The role of the entity ("user" or "assistant").
              - "content" (str): The content of the message or response.
    """
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    # Prepare the query for 'message'
    query_message = """
    SELECT 
        'user' AS role, 
        message AS content, 
        country,
        timestamp 
    FROM conversation_logs 
    WHERE 
        user_id = %s AND 
        message IS NOT NULL AND
        country = %s
    """

    # Execute the query for 'message'
    cur.execute(
        query_message,
        (
            user_id,
            country,
        ),
    )

    # Fetch all the rows for 'message'
    rows_message = cur.fetchall()

    # Prepare the query for 'response'
    query_response = """
    SELECT 
        'assistant' AS role, 
        response AS content, 
        country,
        timestamp 
    FROM conversation_logs 
    WHERE 
        user_id = %s AND
        response IS NOT NULL AND
        country = %s
    """

    # Execute the query for 'response'
    cur.execute(
        query_response,
        (
            user_id,
            country,
        ),
    )

    # Fetch all the rows for 'response'
    rows_response = cur.fetchall()

    # Concatenate and sort the rows
    all_rows = sorted(rows_message + rows_response, key=lambda x: x[2])

    # Format the rows into the desired dictionary format
    session_messages = [{"role": row[0], "content": row[1]} for row in all_rows]

    cur.close()
    conn.close()
    return session_messages


def load_survey_responses(user_id: str, country: str) -> dict:
    """Load survey responses for a specific user and country from the database.

    Args:
        user_id (str): The unique identifier of the user.
        country (str): The country associated with the survey responses.

    Returns:
        dict: A dictionary containing the survey responses if found,
              or an empty dictionary if no responses are available.

    Raises:
        ValueError: If `user_id` or `country` is empty or invalid.
    """
    if not user_id or not country:  # Verify that user_id is valid
        raise ValueError("user_id or country cannot be empty")

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
                    user_id = %s AND
                    country = %s
                """

                # Execute the query for past survey responses
                cur.execute(
                    query_message,
                    (
                        user_id,
                        country,
                    ),
                )

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


def log_conversation(user_id: str, country: str, message: str, response: str) -> None:
    """Logs a conversation entry into the database.

    Args:
        user_id (str): The unique identifier for the user.
        country (str): The country associated with the user.
        message (str): The message sent by the user.
        response (str): The response generated for the user.

    Returns:
        None

    Raises:
        psycopg2.DatabaseError: If there is an issue connecting to or interacting with the database.
    """
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cur = conn.cursor()

    insert = sql.SQL(
        "INSERT INTO conversation_logs (user_id, country, message, response, timestamp) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    data = (user_id, country, message, response, datetime.now())

    cur.execute(insert, data)
    conn.commit()
    cur.close()
    conn.close()
    logging.info(f"Conversation logged successfully: {response}")


def log_survey_responses(user_id: str, survey_responses) -> None:
    """
    Logs survey responses to the database.

    This function takes a user ID and a collection of survey responses,
    and inserts the data into the `survey_responses` table in the database.

    Args:
        user_id (str): The unique identifier for the user submitting the survey.
        survey_responses: An object containing the survey responses, typically
                          accessed via `args.get()` to retrieve individual fields.

    Raises:
        Exception: If there is an error during the database operation, it will
                   print the error message to the console.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = conn.cursor()

        insert = sql.SQL(
            "INSERT INTO survey_responses (user_id, country, email_recontact, first_name, last_name, phone_number, phone_owner, phone_number_backup, consent_social_media, has_paypal, paypal_email, paypal_email_confirm, twitter, tiktok, ethnicity, ethnicity_other, UK_region, UK_district, US_state, US_county, zip, Q1_1, Q1_2, gender_other, Q1_3, Q1_4, Q1_5, Q1_6, Q1_7, Q1_8, Q2, Q3_1, Q3_2, Q3_3, Q3_4, Q3_5, familiarity_tuberculosis, familiarity_mumps, familiarity_polio, familiarity_pneumococcal, familiarity_rotavirus, familiarity_rsv, familiarity_rubella, familiarity_tetanus, familiarity_whooping_cough, familiarity_influenza, familiarity_diphtheria, familiarity_meningitis, familiarity_hepatitis_a, familiarity_hepatitis_b, familiarity_hpv, familiarity_shingles, Q4_2, Q4_3, wellbeing_cheerful, wellbeing_calm, wellbeing_active, wellbeing_fresh, wellbeing_interested, trust_relatives, trust_neighbors, trust_own_tribe, trust_other_tribes, trust_chiefs, trust_district_assemblies, trust_police, trust_courts, trust_parties, trust_army, trust_parliament, trust_president, trust_gbc, trust_electoral_commission, trust_churches, trust_mosques, trust_unions, trust_banks, trust_businesses, Q6_2, Q6_3, Q6_4, Q6_5, Q6_6, Q6_8, open_video, Q8_2, Q8_3, Q8_4, Q8_5, Q8_6, Q8_7, Q8_8, Q8_9, Q8_10, Q8_11, Q8_12, Q8_13, Q8_14, timestamp) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        data = (
            user_id,
            survey_responses.args.get("country", "NA"),
            survey_responses.args.get("email_recontact", "NA"),
            survey_responses.args.get("first_name", "NA"),
            survey_responses.args.get("last_name", "NA"),
            survey_responses.args.get("phone_number", "NA"),
            survey_responses.args.get("phone_owner", "NA"),
            survey_responses.args.get("phone_number_backup", "NA"),
            survey_responses.args.get("consent_social_media", "NA"),
            survey_responses.args.get("has_paypal", "NA"),
            survey_responses.args.get("paypal_email", "NA"),
            survey_responses.args.get("paypal_email_confirm", "NA"),
            survey_responses.args.get("twitter", "NA"),
            survey_responses.args.get("tiktok", "NA"),
            survey_responses.args.get("ethnicity", "NA"),
            survey_responses.args.get("ethnicity_other", "NA"),
            survey_responses.args.get("UK_region", "NA"),
            survey_responses.args.get("UK_district", "NA"),
            survey_responses.args.get("US_state", "NA"),
            survey_responses.args.get("US_county", "NA"),
            survey_responses.args.get("zip", "NA"),
            survey_responses.args.get("Q1_1", "NA"),
            survey_responses.args.get("Q1_2", "NA"),
            survey_responses.args.get("gender_other", "NA"),
            survey_responses.args.get("Q1_3", "NA"),
            survey_responses.args.get("Q1_4", "NA"),
            survey_responses.args.get("Q1_5", "NA"),
            survey_responses.args.get("Q1_6", "NA"),
            survey_responses.args.get("Q1_7", "NA"),
            survey_responses.args.get("Q1_8", "NA"),
            survey_responses.args.get("Q2", "NA"),
            survey_responses.args.get("Q3_1", "NA"),
            survey_responses.args.get("Q3_2", "NA"),
            survey_responses.args.get("Q3_3", "NA"),
            survey_responses.args.get("Q3_4", "NA"),
            survey_responses.args.get("Q3_5", "NA"),
            survey_responses.args.get("familiarity_tuberculosis", "NA"),
            survey_responses.args.get("familiarity_mumps", "NA"),
            survey_responses.args.get("familiarity_polio", "NA"),
            survey_responses.args.get("familiarity_pneumococcal", "NA"),
            survey_responses.args.get("familiarity_rotavirus", "NA"),
            survey_responses.args.get("familiarity_rsv", "NA"),
            survey_responses.args.get("familiarity_rubella", "NA"),
            survey_responses.args.get("familiarity_tetanus", "NA"),
            survey_responses.args.get("familiarity_whooping_cough", "NA"),
            survey_responses.args.get("familiarity_influenza", "NA"),
            survey_responses.args.get("familiarity_diphtheria", "NA"),
            survey_responses.args.get("familiarity_meningitis", "NA"),
            survey_responses.args.get("familiarity_hepatitis_a", "NA"),
            survey_responses.args.get("familiarity_hepatitis_b", "NA"),
            survey_responses.args.get("familiarity_hpv", "NA"),
            survey_responses.args.get("familiarity_shingles", "NA"),
            survey_responses.args.get("Q4_2", "NA"),
            survey_responses.args.get("Q4_3", "NA"),
            survey_responses.args.get("wellbeing_cheerful", "NA"),
            survey_responses.args.get("wellbeing_calm", "NA"),
            survey_responses.args.get("wellbeing_active", "NA"),
            survey_responses.args.get("wellbeing_fresh", "NA"),
            survey_responses.args.get("wellbeing_interested", "NA"),
            survey_responses.args.get("trust_relatives", "NA"),
            survey_responses.args.get("trust_neighbors", "NA"),
            survey_responses.args.get("trust_own_tribe", "NA"),
            survey_responses.args.get("trust_other_tribes", "NA"),
            survey_responses.args.get("trust_chiefs", "NA"),
            survey_responses.args.get("trust_district_assemblies", "NA"),
            survey_responses.args.get("trust_police", "NA"),
            survey_responses.args.get("trust_courts", "NA"),
            survey_responses.args.get("trust_parties", "NA"),
            survey_responses.args.get("trust_army", "NA"),
            survey_responses.args.get("trust_parliament", "NA"),
            survey_responses.args.get("trust_president", "NA"),
            survey_responses.args.get("trust_gbc", "NA"),
            survey_responses.args.get("trust_electoral_commission", "NA"),
            survey_responses.args.get("trust_churches", "NA"),
            survey_responses.args.get("trust_mosques", "NA"),
            survey_responses.args.get("trust_unions", "NA"),
            survey_responses.args.get("trust_banks", "NA"),
            survey_responses.args.get("trust_businesses", "NA"),
            survey_responses.args.get("Q6_2", "NA"),
            survey_responses.args.get("Q6_3", "NA"),
            survey_responses.args.get("Q6_4", "NA"),
            survey_responses.args.get("Q6_5", "NA"),
            survey_responses.args.get("Q6_6", "NA"),
            survey_responses.args.get("Q6_8", "NA"),
            survey_responses.args.get("open_video", "NA"),
            survey_responses.args.get("Q8_2", "NA"),
            survey_responses.args.get("Q8_3", "NA"),
            survey_responses.args.get("Q8_4", "NA"),
            survey_responses.args.get("Q8_5", "NA"),
            survey_responses.args.get("Q8_6", "NA"),
            survey_responses.args.get("Q8_7", "NA"),
            survey_responses.args.get("Q8_8", "NA"),
            survey_responses.args.get("Q8_9", "NA"),
            survey_responses.args.get("Q8_10", "NA"),
            survey_responses.args.get("Q8_11", "NA"),
            survey_responses.args.get("Q8_12", "NA"),
            survey_responses.args.get("Q8_13", "NA"),
            survey_responses.args.get("Q8_14", "NA"),
            datetime.now(),
        )

        cur.execute(insert, data)
        conn.commit()

    except Exception as e:
        print(f"Error logging survey responses: {e}")

    finally:
        cur.close()
        conn.close()
        logging.info(f"Survey responses logged successfully for: {user_id}")


def query_llm(messages: list) -> str:
    """
    Sends a list of messages to the OpenAI ChatCompletion API and retrieves the response.

    Args:
        messages (list): A list of message dictionaries to be sent to the language model.
                         Each dictionary typically contains a "role" (e.g., "user" or "system" or "assistant")
                         and "content" (the message text).

    Returns:
        str: The content of the response message generated by the language model.
    """
    response = openai.ChatCompletion.create(
        model=GPT_MODEL,
        temperature=TEMPERATURE,
        messages=messages,
        frequency_penalty=0,
        presence_penalty=0.6,
    )

    interviewer_response = response["choices"][0]["message"]["content"]
    return interviewer_response


def summarise_interview_responses(
    past_interview_responses: list,
) -> str:
    """
    Summarises a list of past interview responses using a language model.

    This function takes a list of interview responses, combines them into a single
    string, and uses a predefined summarisation prompt to query a language model
    for a summarised response.

    Args:
        past_interview_responses (list): A list of dictionaries where each dictionary
            represents an interview response. Each dictionary should have the keys:
            - 'role' (str): The role of the speaker.
            - 'content' (str): The content of the response.

    Returns:
        str: A summarised version of the interview responses.
    """
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


def inject_survey_response_prompt(system_prompt: str, country: str) -> str:
    """
    Replaces a placeholder in the system prompt with a country-specific survey response prompt.

    This function reads a survey response prompt from a file based on the specified country
    and injects it into the provided system prompt by replacing the placeholder
    "@survey_response_prompt".

    Args:
        system_prompt (str): The system prompt containing the placeholder to be replaced.
        country (str): The country for which the survey response prompt is required.
                       Supported values are "Ghana", "United Kingdom", and "United States".

    Returns:
        str: The updated system prompt with the country-specific survey response prompt injected.

    Raises:
        RuntimeError: If the specified country is not supported.
    """
    if country == "Ghana":
        with open("prompts/ghana_survey_response_prompt.txt", "r") as file:
            survey_response_prompt = file.read()

    elif country == "United Kingdom":
        with open("prompts/uk_survey_response_prompt.txt", "r") as file:
            survey_response_prompt = file.read()

    elif country == "United States":
        with open("prompts/us_survey_response_prompt.txt", "r") as file:
            survey_response_prompt = file.read()

    else:
        logging.info(
            f"Country information is not provided. Defaulting to country=Ghana system prompt..."
        )
        with open("prompts/ghana_survey_response_prompt.txt", "r") as file:
            survey_response_prompt = file.read()

    system_prompt = system_prompt.replace(
        "@survey_response_prompt", survey_response_prompt
    )

    return system_prompt


@app.route("/", methods=["GET", "POST"])
def home():
    # Extract user id and country
    session_user_id = request.args.get("user_id", "")  # whatever the querystring is
    country = request.args.get("country", "")
    if not session_user_id or not country:
        logging.error(
            "User ID or country is not provided. Defaulting to 'test_id' and 'Ghana', respectively."
        )
        session_user_id = "453226" # TODO remove
        country = "United Kingdom"  # TODO remove
        # session_user_id = "test_id"
        # country = "Ghana"
    logging.info(f"session_user_id, country: {session_user_id, country}")

    # Check if user has already undergone the survey
    past_survey_responses = load_survey_responses(
        user_id=session_user_id, country=country
    )

    # Extract system prompt template and replace placeholders with request arguments
    if past_survey_responses:  # Subsequent round of interview
        logging.info(
            f"past_survey_responses from {past_survey_responses['user_id']} extracted successfully"
        )
        with open("prompts/system_prompt_followup_interview.txt", "r") as file:
            system_prompt = file.read()

            # Inject survey response prompt depending on country
            system_prompt = inject_survey_response_prompt(
                system_prompt=system_prompt, country=country
            )

            # Extract user's past interview responses
            past_interview_responses = load_conversation(
                user_id=session_user_id, country=country
            )

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
                system_prompt = system_prompt.replace(
                    f" @{question}\n", f" {response}\n"
                )

    else:  # Initial round of interview
        logging.info("No past survey responses found.")
        with open("prompts/system_prompt_initial_interview.txt", "r") as file:
            system_prompt = file.read()

        # Inject survey response prompt depending on country
        system_prompt = inject_survey_response_prompt(
            system_prompt=system_prompt, country=country
        )

        log_survey_responses(user_id=session_user_id, survey_responses=request)

    # Retrieve request arguments and replace placeholders in system_prompt
    for placeholder, arg_name in prompt_placeholders.items():
        value = request.args.get(arg_name, "NA")
        system_prompt = system_prompt.replace(f" {placeholder}\n", f" {value}\n")

    logging.info(f"system_prompt: {system_prompt}")
    session_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello"},
    ]

    # Get the assistant's response
    assistant_response = query_llm(messages=session_messages)
    session_messages += [{"role": "assistant", "content": assistant_response}]

    # Write to database
    log_conversation(
        user_id=session_user_id,
        country=country,
        message=system_prompt,
        response=assistant_response,
    )

    return render_template(
        "index_survey.html",
        assistant_message=assistant_response,
        user_id=session_user_id,
        country=country,
    )


@app.route("/get")
def get_bot_response():
    # Get the user's message, id, and country
    user_text = request.args.get("msg")
    session_user_id = request.args.get("user_id", "")  # whatever the querystring is
    country = request.args.get("country", "")
    if not session_user_id or not country:
        logging.error(
            "User ID or country is not provided. Defaulting to 'test_id' and 'Ghana', respectively."
        )
        session_user_id = "453226" # TODO remove
        country = "United Kingdom"  # TODO remove
        # session_user_id = "test_id"
        # country = "Ghana"
    logging.info(
        f"session_user_id, country, user_text: {session_user_id, country, user_text}"
    )

    # Read conversation from database and append user message
    session_messages = load_conversation(user_id=session_user_id, country=country)
    session_messages += [{"role": "user", "content": user_text}]

    # Append the model's response
    model_message = query_llm(messages=session_messages)
    session_messages = session_messages + [
        {"role": "assistant", "content": model_message}
    ]

    # Log the conversation to the database
    log_conversation(
        user_id=session_user_id,
        country=country,
        message=user_text,
        response=model_message,
    )

    # Return the model's response
    return str(model_message)


if __name__ == "__main__":
    app.run(debug=False)
