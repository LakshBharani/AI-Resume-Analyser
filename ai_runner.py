import os
import pyodbc
import google.generativeai as genai
import pymupdf
import zipfile
import subprocess
import csv
import sys

filepath = sys.argv[1]
job_description = sys.argv[2]
job_metrics = sys.argv[3]
jobid = sys.argv[4]



def ai_runner(filepath_input,job_description_input,job_metrics_input,job_id_input):
    try:
        genai.configure(api_key="#Your API key here#")
        generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "top_k": 20,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        output_file = str(job_id_input)+".csv"
        metrics_input = job_metrics_input
        success_status = True
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-002",
            generation_config=generation_config,
            system_instruction="You are an artificial intelligence hiring manager assistant and you need to review the given job description and resumes and provide your summary on each resume to another artificial intelligence hiring manager assistant who is similar to you. Your response should be in the following format (don't forget any bracket such as <> or end resumes</resume> or be it any space for formatting purposes and indexing might throw an error), also, keep the fit score in two digits for indexing purposes, and grade them numerically in 2 digits on the criteria provided as input (these 2 digit scores will be used to compare any 2 random candidates and plot on a spider chart):\n<resume_file_name.file_extension>\nFit_Score: your_score/100 # The fit score you assigned to the candidate relative to others\nJudging Criteria Scores\n(list the criteria one below the other along with the score, and also keep the score of each criteria 2 digits if you want to give a single digit score put a zero before it) * criteria : score/100\n</resume>\nPlease provide all outputs in the desired format so that the program doesn't do a mistake in parsing the number. Also don't miss the analysis of any resume for tallying reasons.\n (This information is for you)Job Description:"+job_description_input+"Judging criteria:"+metrics_input,
        )
        resumes_string = ""
        with zipfile.ZipFile(filepath_input, 'r') as archive:
            for fileinfo in archive.infolist():
                if fileinfo.filename.endswith('.pdf'):
                    with archive.open(fileinfo) as pdf_file:
                        pdf_data = pdf_file.read()
                        pdf_document = pymupdf.open(stream=pdf_data, filetype="pdf")
                        pdf_text = ""
                        for page_num in range(pdf_document.page_count):
                            page = pdf_document[page_num]
                            pdf_text += page.get_text("text")
                        pdf_document.close()
                    resumes_string += f"<{fileinfo.filename}>\n{pdf_text}\n</resume>"
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(resumes_string)
        print(response.text)
        result = response.text.split("</resume>\n")
        my_dict = {}
        for single_resume in result:
            temp_string = ""
            temp_list = []
            for i in range(len(single_resume)):
                if single_resume[i:i+5:]==".pdf>":
                    my_dict[single_resume[1:i+4:]] = []
                    temp_string = single_resume[1:i+4:]
                if single_resume[i:i+2:]==": ":
                    temp_list.append(int(single_resume[i+2:i+4:]))
            my_dict[temp_string]=temp_list
        with open(output_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            temp_row = job_metrics_input.split("\r\n")
            writer.writerow(temp_row)
            for key,values in my_dict.items():
                writer.writerow([key]+values)
    except Exception as e:
        print(e)
    conn1 = pyodbc.connect(r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\\Users\\Anjan\\OneDrive\\Documents\\Projects\\Neural Hire\\temporarydb.accdb;')
    cursor1 = conn1.cursor()
    cursor1.execute("""
    UPDATE jobs SET status=? WHERE jobid=?
    """,(True,job_id_input))
    conn1.commit()
    conn1.close()

ai_runner(filepath,job_description,job_metrics,jobid)