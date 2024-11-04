# import all necessary libraries for the project

import os
import google.generativeai as genai
import pymupdf
import plotly.graph_objects as go
import re
import csv
from dotenv import load_dotenv
from pathlib import Path
import zipfile
import pyodbc
import sys


# get api key from .env
dotenv_path = Path('./.env')
load_dotenv(dotenv_path=dotenv_path)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
SQL_CLOUD_PWD = os.getenv('SQL_CLOUD_PWD')

filepath = sys.argv[1]
job_description = sys.argv[2]
job_metrics = sys.argv[3]
job_Id = sys.argv[4]

print(filepath, job_description, job_metrics, job_Id)

# establish db connection
myconn = pyodbc.connect(
    r'Driver={ODBC Driver 18 for SQL Server};Server=tcp:neural-hire-dev-1.database.windows.net,1433;Database=neural-hire-db;Uid=vmadmin;Pwd=Virginia@Tech;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
mycurr = myconn.cursor()

# get all judging filters as input from recruiter


def extract_job_metrics():
    global job_metrics
    job_metrics = job_metrics.split(",")
    for i in range(len(job_metrics)):
        job_metrics[i] = job_metrics[i].strip().capitalize()
    return job_metrics


# reads & extracts text from all resumes in ./ENGINEERING/*.pdf
def extract_resume_data():
    resumes_string = ""
    with zipfile.ZipFile(filepath, 'r') as archive:
        for fileinfo in archive.infolist():
            if fileinfo.filename.endswith('.pdf'):
                with archive.open(fileinfo) as pdf_file:
                    pdf_data = pdf_file.read()
                    pdf_document = pymupdf.open(
                        stream=pdf_data, filetype="pdf")
                    pdf_text = ""
                    for page_num in range(pdf_document.page_count):
                        page = pdf_document[page_num]
                        pdf_text += page.get_text("text")
                    pdf_document.close()
                    resumes_string += f"<{fileinfo.filename}>\n{pdf_text}\n</resume>"
    return resumes_string


# Create a CSV of output scores
def write_to_csv(responseText):
    print(responseText)

    # Define the filename for the CSV
    output_filename = f"{job_Id}.csv"

    # Extract the judging criteria and resume data
    responseText = responseText.split("</resume>")
    rows = []

    # Extract each resume's data from the AI response
    for response in responseText:
        if response.strip():  # Skip empty responses
            file_name = response.strip("\n").partition(".pdf>")[0][1:] + ".pdf"
            pattern = r'\* (.+?): (\d+)'  # Find judging criteria scores
            matches = re.findall(pattern, response)

            # Extract Fit Score and Criteria Scores
            fit_score_match = re.search(r"Fit_Score: (\d+)/100", response)
            fit_score = fit_score_match.group(1) if fit_score_match else "N/A"

            # Create a dictionary of criteria scores for alignment with headers
            criteria_scores = {match[0]: int(match[1]) for match in matches}

            # Store data in rows for CSV
            row = [file_name, fit_score] + [
                criteria_scores.get(criteria, 0) for criteria in job_metrics
            ]
            rows.append(row)

    # Write data to CSV
    with open(output_filename, mode='w', newline='') as file:
        writer = csv.writer(file)

        # Create the header row
        header = ["Resume File", "Fit Score"] + job_metrics
        writer.writerow(header)

        # Write the data rows
        writer.writerows(rows)

    print(f"CSV file '{output_filename}' has been created successfully.")

# calls the extract_resume_data function
resumes_string = extract_resume_data()

# calls the extract_judging_criteria function()
job_metrics = extract_job_metrics()

# creating models to represent hiring managers
genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 0.1,
    "top_p": 0.95,
    "top_k": 20,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-002",
    generation_config=generation_config,
    system_instruction="You are an artificial intelligence hiring manager assistant and you need to review the given job description and resumes and provide your summary on each resume to another artificial intelligence hiring manager assistant who is similar to you. Your response should be in the following format (don't forget any bracket such as <> or end resumes</resume> or be it any space for formatting purposes and indexing might throw an error), also, keep the fit score in two digits for indexing purposes, and grade them numerically in 2 digits on the criteria provided as input (these 2 digit scores will be used to compare any 2 random candidates and plot on a spider chart):\n<resume_file_name.file_extension>\nFit_Score: your_score/100 # The fit score you assigned to the candidate relative to others\nJudging Criteria Scores\n(list the criteria one below the other along with the score, and also keep the score of each criteria 2 digits if you want to give a single digit score put a zero before it) * criteria: score/100\n</resume>\nPlease provide all outputs in the desired format (including the '* ' character before every judging criteria) so that the program doesn't do a mistake in parsing the number. Also don't miss the analysis of any resume for tallying reasons.\n (This information is for you)Job Description:"+job_description+"Judging criteria:"+str(job_metrics),
)

# maintain chat history with models
chat_session = model.start_chat(
    history=[
    ]
)

response = chat_session.send_message(resumes_string)

# get text from responses
responseText = response.text

# plot spider chart after analysing data and receiving response
# plot_spider_chart(responseText, job_metrics)

mycurr.execute("""
    UPDATE jobs SET status=? WHERE jobid=?
    """, (True, job_Id))
mycurr.commit()
mycurr.close()

# create & write csv
write_to_csv(responseText)
