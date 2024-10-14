# import all necessary libraries for the project

import os
import google.generativeai as genai
import pymupdf
import tkinter as tk
import plotly.express as px
import plotly.graph_objects as go
import re
import csv
from dotenv import load_dotenv
from pathlib import Path


# get api key from .env
dotenv_path = Path('./.env')
load_dotenv(dotenv_path=dotenv_path)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


# get all judging filters as input from recruiter
def extract_judging_criteria():
    judging_criteria = input("Enter judgement criteria (CSV): ")
    judging_criteria = judging_criteria.split(",")
    for i in range(len(judging_criteria)):
        judging_criteria[i] = judging_criteria[i].strip().capitalize()
    return judging_criteria


# reads & extracts text from all resumes in ./ENGINEERING/*.pdf
def extract_resume_data():
    resumes_string = ""
    for filename in os.listdir('ENGINEERING'):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join('ENGINEERING', filename)
            pdf_document = pymupdf.open(pdf_path)
            pdf_text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                pdf_text += page.get_text("text")
            pdf_document.close()
            resumes_string += "<"+filename+">\n"+pdf_text+"\n</resume>"
    return resumes_string


# plot the spider chart from all resume data
def plot_spider_chart(responseText, judging_criteria):
    fig = go.Figure()

    responseText = responseText.split("</resume>")
    for response in responseText:
        print(response)

        file_name = response.strip("\n").partition(".pdf>")[0][1::] + ".pdf"
        pattern = r'\* (.+?): (\d+)'
        matches = re.findall(pattern, response)
        r_value = []
        for match in matches:
            r_value.append(int(match[1]))

        fig.add_trace(go.Scatterpolar(
            r=r_value,
            theta=judging_criteria + [],
            fill='toself',
            name=file_name
        ))
    fig.show()


# Create a CSV of output scores
def write_to_csv(responseText):
    # Define the filename for the CSV
    output_filename = "resume_scores.csv"

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
                criteria_scores.get(criteria, 0) for criteria in judging_criteria
            ]
            rows.append(row)

    # Write data to CSV
    with open(output_filename, mode='w', newline='') as file:
        writer = csv.writer(file)

        # Create the header row
        header = ["Resume File", "Fit Score"] + judging_criteria
        writer.writerow(header)

        # Write the data rows
        writer.writerows(rows)

    print(f"CSV file '{output_filename}' has been created successfully.")


# job description of the role over which resumes are being tested
job_description = """
Overview
Student Training in Engineering Program (STEP) is a developmental internship program for students in their first or second year of a Bachelor's degree program in Computer Science or a related field, aimed specifically at cultivating high potential students and focuses on providing development opportunities through technical training, software engineering project work, and professional development.

Google welcomes applications from candidates from all backgrounds regardless of race, ethnicity, religion, gender identity, sexual orientation, age, disability status or any other dimension of diversity, who are currently enrolled in a full-time Bachelors degree program.

Students from all schools, and students who (1) have demonstrated a commitment to diversity and inclusion; (2) have faced and overcome adversity; or (3) identify with a group that is historically underrepresented in the technology industry including, but not limited to Black, Hispanic, Native American, students with disabilities, Women and veterans, are encouraged to apply.

Program Goals
To provide interns with the opportunity to complete a challenging technical project where you will build solutions and gain exposure to immense scale and complexity.
To help interns develop their technical skills, build confidence in their abilities, and better prepare them for their future in computer science. All STEP interns will receive coaching and mentorship from Google engineers to guide you through your summer experience.
To give interns an inside look at Google's unique environment, community, and culture. Interns will have the opportunity to attend technical talks by Googlers, gain insight into technical interview preparation, learn about Google’s coding practices and technologies, and develop other skills that will set them up for success.
To help participants begin building important personal networks and friendships with a diverse group of students who share their passion for technology and computer science.
Eligibility Requirements
Minimum Qualifications

Completed first or second year of undergraduate studies in computer science or a related field by Summer 2025.
Programming experience in C++, Java, JavaScript or Python.
Have taken 1-2 college computer science courses (AP or IB included).
Currently attending a university in North America.
Preferred Qualifications

Returning to a Bachelor's degree program with at least two years remaining in their academic program after completion of the Summer 2025 internship.
Ability to complete a full-time, 12-week internship between May and August or June and September 2025 (exact program dates will be provided at a later point in the process).
"""

# calls the extract_resume_data function
resumes_string = extract_resume_data()

# calls the extract_judging_criteria function()
judging_criteria = extract_judging_criteria()

# creating models to represent hiring managers
genai.configure(api_key=GEMINI_API_KEY)

generation_config0 = {
    "temperature": 0.8,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

generation_config1 = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model0 = genai.GenerativeModel(
    model_name="gemini-1.5-pro-002",
    generation_config=generation_config0,
    system_instruction="You are an artificial intelligence hiring manager assistant and you need to review the given job description and resumes and provide your summary on each resume to another artificial intelligence hiring manager assistant who is similiar to you. Your response should be in the following format(don't forget any bracket such as <> or end resumes</resume> or be it any space for formating purposes and indexing might throw an error),(also keep the fit score in two digits for indexing purposes), also , grade them numerically in 2 digits on the criteria provided as input (these 2 digit scores will be used to compare 2 any 2 random candidates and plot on a spider chart):\n<resume_file_name.file_extension>\nFit_Score: your_score/100 #The fit score you assigned to the candidate relative to others\nJuding Criteria Scores\n(list the criterias one below the other along with the score) * criteria: score (dont put a space next to criteria and : and put a space after : and score and dont forget the bullet point * for formatting purpose) format\nPositives: # Provide what made you give that score. What matched\nNegatives: # Provide what you feel he is lacking relative to others\n</resume>",
)

model1 = genai.GenerativeModel(
    model_name="gemini-1.5-pro-002",
    generation_config=generation_config0,
    system_instruction="You are an artificial intelligence hiring manager assistant and you need to review the given job description and resumes and provide your response on each resume review by the hiring manager to the hiring manager. Your response should be in the following format(Don't forget any brackets such as <> or end resumes</resume> or be it any space for formating purposes and indexing might throw an error),(also keep the Fit_Score_Agreement: as either T or F(case sensitive)):\n<resume_file_name.file_extension>\nFit_Score_Agreement: #Enter only True or False(Case sensitive)\nMy_Comment: #Enter your comment on the summary by the hiring manager do you agree or disagree.\n</resume>\n",
)


# maintain chat history with models
chat_session0 = model0.start_chat(
    history=[
    ]
)

chat_session1 = model1.start_chat(
    history=[
    ]
)

response = chat_session0.send_message(
    "<Job Description>\n"+job_description+"\n</Job Description>\n"+resumes_string + str(judging_criteria))
response1 = chat_session1.send_message("<Job Description>\n"+job_description +
                                       "\n</Job Description>\n"+resumes_string+"\nHiring Manager's Response: \n"+response.text)

# get text from responses
responseText = response.text
response1Text = response1.text

# plot spider chart after analysing data and receiving response
plot_spider_chart(responseText, judging_criteria)

# create & write csv
write_to_csv(responseText)
