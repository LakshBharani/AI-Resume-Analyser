from dotenv import load_dotenv
from flask import Flask,request,redirect,url_for,render_template,session
import os
import pyodbc
import subprocess
import threading
from datetime import datetime
import pandas as pd
from pathlib import Path

dotenv_path = Path('./.env')
load_dotenv(dotenv_path=dotenv_path)
SQL_CLOUD_PWD = os.getenv('SQL_CLOUD_PWD')

connection_string = f'Driver={"ODBC Driver 18 for SQL Server"};Server=tcp:neural-hire-dev-1.database.windows.net,1433;Database=neural-hire-db;Uid=vmadmin;Pwd={SQL_CLOUD_PWD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

myconn = pyodbc.connect(connection_string)
mycurr = myconn.cursor()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route('/login',methods=['GET','POST'])
def login():
    if 'username' not in session:
        mycurr.execute("""
        SELECT * FROM [dbo].[iam]
        """)
        rows1 = mycurr.fetchall()
        iam = {}
        for row1 in rows1:
            iam[row1[0]] = row1[1]
        myconn.commit()
        
        if request.method=='POST':
            try:
                inputusername = request.form['inputusername']
                inputpassword = request.form['inputpassword']
                if iam[inputusername] == inputpassword:
                    session['username'] = inputusername
                    return redirect('/')
            except Exception as e:
                return render_template('login.html', loggintrial = False)
            else:
                return render_template('login.html', loggintrial = False)
        return render_template('login.html', logintrial = True)
    return redirect('/')

@app.route('/',methods=['GET','POST'])
def home():
    mycurr.execute("""
    SELECT * FROM [dbo].[jobs]
    """)
    rows = mycurr.fetchall()
    session['completed_and_downloadable_jobids'] = []
    if 'username' not in session:
        return redirect('/login')
    tablerows = []
    for row in rows:
        if row[4]==session['username']:
            tablerows.append([row[1],row[3],row[0]])
            if row[3]==True:
                session['completed_and_downloadable_jobids'].append(row[0])
    myconn.commit()
    return render_template('home.html',data = tablerows)

@app.route('/createnewjob',methods=['GET','POST'])
def createnewjob():
    if 'username' not in session:
        return redirect('/login')
    if request.method=="POST":
        jobname = request.form['jobname']
        jobdescription = request.form['jobdescription']
        file = request.files['file']
        filepath = os.path.join(app.config['UPLOAD_FOLDER'],file.filename)
        file.save(filepath)
        metrics = request.form['metrics']
        metrics = metrics.split('\r\n')
        metrics_input = ""
        for a in range(len(metrics)-1):
            metrics_input += metrics[a] + ","
        metrics_input += metrics[-1] + "."
        
        mycurr.execute("""
        INSERT INTO [dbo].[jobs](jobname, datecreated, status, username) VALUES(?,?,?,?)
        """,(jobname,datetime.now().date(),False,session['username']))
        mycurr.commit()
        mycurr.execute("SELECT @@IDENTITY AS last_id")
        jobid = mycurr.fetchone().last_id
        print(jobid)
        myconn.commit()
        threading.Thread(target=subprocess.Popen, args=(['python', 'resume_analyser.py', filepath, jobdescription, metrics_input,str(jobid)],)).start()
        return redirect('/')
    return render_template('createnewjob.html')

@app.route('/redirecthandle',methods=['GET','POST'])
def redirecthandle():
    try:
        logoutconfirmation = request.form["logout"]=="confirm"
        if logoutconfirmation:
            session.pop('username',None)
            return redirect('/login')
    except Exception as e0:
        logoutconfirmation = False
    try:
        createnewjob = request.form['createnewjob']=="confirm"
        if createnewjob:
            return redirect('/createnewjob')
    except Exception as e1:
        emptyvar = 0
    try:
        
        if int(request.form['View']) in session['completed_and_downloadable_jobids']:
            return redirect(url_for('viewjob',inputviewjobid=str(request.form['View'])))
        return redirect('/')
    except Exception as e2:
        emptyvar = 0
    try:
        createnewjob = request.form['home']=="confirm"
        if createnewjob:
            return redirect('/')
    except Exception as e1:
        emptyvar = 0
    return redirect('/')

@app.route('/viewjob',methods=['GET','POST'])
def viewjob():
    if 'username' not in session:
        return redirect('/login')
    input_view_job_id = request.args.get('inputviewjobid')
    if (request.method=='GET') and (int(input_view_job_id) in session['completed_and_downloadable_jobids']):
        csv_file_name = str(input_view_job_id)+".csv"
        df = pd.read_csv(csv_file_name, encoding='utf-8', encoding_errors='ignore')
        labels = df.columns[1:].tolist() # Assuming the first column is a category, and others are metrics
        mycurr.execute(f'select jobname from [dbo].[jobs] where jobid = {str(input_view_job_id)};')
        job_name = mycurr.fetchone()[0]
        datasets = [
            {
                "label": row[0],
                "data": row[1:].tolist(),
            }
            for row in df.values
        ]
        return render_template('viewjob.html', labels=labels, datasets=datasets, job_name=job_name)
    return redirect('/')
    
if __name__ == '__main__':
    app.run(debug=False)