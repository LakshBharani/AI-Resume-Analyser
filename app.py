from flask import Flask,request,redirect,url_for,render_template,session
import os
import pyodbc
import subprocess
import threading
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = "329rjfnfrg94rjvnffvie498r"


UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

completed_and_downloadable_jobids = []

@app.route('/login',methods=['GET','POST'])
def login():
    if 'username' not in session:
        conn1 = pyodbc.connect(r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\\Users\\Anjan\\OneDrive\\Documents\\Projects\\Neural Hire\\IAM.accdb;')
        cursor1 = conn1.cursor()
        cursor1.execute("""
        SELECT * FROM iam
        """)
        rows1 = cursor1.fetchall()
        iam = {}
        for row1 in rows1:
            iam[row1[0]] = row1[1]
        conn1.close()
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
    conn = pyodbc.connect(r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\\Users\\Anjan\\OneDrive\\Documents\\Projects\\Neural Hire\\temporarydb.accdb;')
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM jobs
    """)
    rows = cursor.fetchall()
    if 'username' not in session:
        return redirect('/login')
    tablerows = []
    for row in rows:
        if row[4]==session['username']:
            tablerows.append([row[1],row[3],row[0]])
            if row[3]==True:
                completed_and_downloadable_jobids.append(row[0])
    conn.close()
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
        conn1 = pyodbc.connect(r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\\Users\\Anjan\\OneDrive\\Documents\\Projects\\Neural Hire\\temporarydb.accdb;')
        cursor1 = conn1.cursor()
        cursor1.execute("""
        INSERT INTO jobs(jobname, datecreated, status, username) VALUES(?,?,?,?)
        """,(jobname,datetime.now().date(),False,session['username']))
        conn1.commit()
        cursor1.execute("SELECT @@IDENTITY AS last_id")
        jobid = cursor1.fetchone().last_id
        print(jobid)
        conn1.close()
        threading.Thread(target=subprocess.Popen, args=(['python', 'ai_runner.py', filepath, jobdescription, metrics_input,str(jobid)],)).start()
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
        
        if int(request.form['View']) in completed_and_downloadable_jobids:
            return redirect(url_for('viewjob',inputviewjobid=str(request.form['View'])))
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
    input_view_job_id = request.args.get('inputviewjobid')
    if request.method=='GET':
        csv_file_name = str(input_view_job_id)+".csv"
        df = pd.read_csv(csv_file_name)
        labels = df.columns[1:].tolist()  # Assuming the first column is a category, and others are metrics
        datasets = [
            {
                "label": row[0],
                "data": row[1:].tolist()
            }
            for row in df.values
        ]
        return render_template('viewjob.html',labels=labels,datasets=datasets)
    return redirect('/')
    
if __name__ == '__main__':
    app.run(debug=True)