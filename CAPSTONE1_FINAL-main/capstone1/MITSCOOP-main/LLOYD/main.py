from flask import Flask, render_template, redirect, url_for, session,send_file,flash,request
from flask_mysqldb import MySQL
import base64
import io
from datetime import datetime,timedelta




app = Flask(__name__)

def encode_b64(data):
    return base64.b64encode(data).decode() if data else None
app.jinja_env.filters['b64encode'] = encode_b64

app.secret_key = 'your_secret_key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'mitscoop'
app.config['MYSQL_UNIX_SOCKET'] = '/opt/lampp/var/mysql/mysql.sock'


mysql = MySQL(app)





@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        address = request.form['address']
        contact = request.form['contact']
        position = request.form['position']
        status = request.form['status']
        email = request.form['email']
        pwd = request.form['password']
        con_password = request.form['con_password']

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM user WHERE email = %s', (email,))
        email_count = cursor.fetchone()[0]
        cursor.close()

        if email_count > 0:
            flash('⚠️ Email is already in use.')
            return redirect(url_for('register'))
        elif pwd != con_password:
            flash('⚠️ Passwords do not match.')
            return redirect(url_for('register'))

    
        cursor = mysql.connection.cursor()
        cursor.execute(
            'INSERT INTO user (name, age, address, gender, contact, status, position, email, password) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (name, age, address, gender, contact, status, position, email, pwd)
        )
        mysql.connection.commit()

        user_id = cursor.lastrowid
        session['user_id'] = user_id

        cursor.close()

        return redirect(url_for('landing')) 
    else:
        return render_template('register.html')

@app.route('/', methods=["GET", "POST"])
def landing():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM user WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()

        if email == "admin" and password == "admin":
            session['user_id'] = "admin"
            return redirect(url_for('admin'))


        if user:
            session['user_id'] = user[0] 
            return redirect(url_for('home'))
        else:
            flash('Wrong username or password')
            return redirect(url_for('landing'))

    return render_template('landing.html')

@app.route('/home')
def home():
   
    user_id = session.get('user_id')  
    if user_id:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s AND status = 'pending'", (user_id,))
        task_count = cursor.fetchone()[0]
        cursor.close()
    else:
        task_count = 0
    
    return render_template('home.html', task_count=task_count)
    

@app.route('/report', methods=["GET", "POST"])
def report():
    if 'user_id' not in session:
        return redirect(url_for('landing'))
    
    user_id = session['user_id']  

    if request.method == "POST":
        message = request.form.get('message')  
        image = request.files.get('image')   

        if image:  
            image_data = image.read()

            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO report (message, image,user_id,status) VALUES (%s, %s,%s, %s)", (message, image_data,user_id,'Completed'))
            mysql.connection.commit()
            cursor.close()

            if user_id:
                cursor = mysql.connection.cursor()
                cursor.execute(f"DELETE FROM tasks WHERE user_id = {user_id}")
                mysql.connection.commit()

                if cursor.rowcount == 0:
                    print(f"No task updated for task_id {id} and user_id {user_id}")
                else:
                    print(f"Task {id} status updated successfully.")
        return redirect(url_for("home"))

        

    else:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT task_description, due_datetime, status FROM tasks WHERE user_id = %s", (user_id,))
        tasks = cursor.fetchall()
        cursor.close()

        return render_template('report.html', tasks=tasks)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
         return redirect(url_for('landing'))


    user_id = session['user_id']  
    cursor = mysql.connection.cursor()
    cursor.execute("""
    SELECT name, age, address, gender, status, contact, position,email
    FROM user
    WHERE user_id = %s
    """, (user_id,))


    user_data = cursor.fetchone()
    cursor.close()
   

    if user_data:
        return render_template('profile.html', 
                               name=user_data[0], 
                               age=user_data[1], 
                               address=user_data[2], 
                               gender=user_data[3],
                               status=user_data[4],
                               contac=user_data[5],
                               position=user_data[6],
                                email=user_data[7])
    
    else:
        return redirect(url_for('landing')) 
    
@app.route('/admin')
def admin():
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM report")
    total_reports = cursor.fetchone()[0]

    
    cursor.execute("SELECT COUNT(*) FROM report WHERE status = 'to be evaluated'")
    to_be_evaluated_reports = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM report WHERE status = 'approved'")
    approved_reports = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM report WHERE status = 'rejected'")
    rejected_reports = cursor.fetchone()[0]

    
    to_be_evaluated_percentage = (to_be_evaluated_reports / total_reports) * 100 if total_reports > 0 else 0
    approved_percentage = (approved_reports / total_reports) * 100 if total_reports > 0 else 0
    pending_percentage = (rejected_reports / total_reports) * 100 if total_reports > 0 else 0

   
    cursor.execute("""
        SELECT u.user_id, u.name, COUNT(r.report_id) AS reports_submitted
        FROM user u
        LEFT JOIN report r ON u.user_id = r.user_id
        GROUP BY u.user_id
    """)
    users_reports = cursor.fetchall()  

    
    cursor.close()

    return render_template(
        'admin.html',
        to_be_evaluated_percentage=to_be_evaluated_percentage,
        approved_percentage=approved_percentage,
        pending_percentage=pending_percentage,
        users_reports=users_reports
    )

@app.route('/check/<int:report_id>', methods=['GET', 'POST'])
def check(report_id):
    if 'user_id' not in session:
        return redirect(url_for('landing'))

    if request.method == 'POST':
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE report SET status = 'approved' WHERE report_id = %s", (report_id,))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('list_report')) 
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT report_id, message, image, status FROM report")
    reports = cursor.fetchall()
    cursor.close()

    return render_template('list_report.html', reports=reports)


@app.route('/view/<int:report_id>')
def view(report_id):
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT image FROM report WHERE report_id = %s", (report_id,))
    report = cursor.fetchone()


    if report and report[0]:
        image_data = report[0] 
        
        
        return send_file(io.BytesIO(image_data), mimetype='image/jpeg')

    else:
        return "Image not found", 404
    

@app.route('/delete/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    
        cursor = mysql.connection.cursor()

        cursor.execute("DELETE FROM report WHERE report_id = %s", (report_id,))
       
        mysql.connection.commit()

        return redirect(url_for('check')) 



@app.route('/record')
def record():
    cursor = mysql.connection.cursor()

    current_date = datetime.now()
    start_of_week = current_date - timedelta(days=current_date.weekday())  
    end_of_week = start_of_week + timedelta(days=6)  

    start_of_week_str = start_of_week.strftime('%Y-%m-%d')
    end_of_week_str = end_of_week.strftime('%Y-%m-%d')

    cursor.execute("""
        SELECT u.user_id, u.name, a.time, a.status
        FROM user u
        LEFT JOIN attendance a ON u.user_id = a.user_id
        AND a.time BETWEEN %s AND %s
    """, (start_of_week_str, end_of_week_str))

    attendance_records = cursor.fetchall()

    cursor.close()

    return render_template('record.html', attendance=attendance_records)




@app.route('/performance')
def performance():
    
    return render_template("performance.html")

@app.route('/help')
def help():
    
    return render_template("help.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))


@app.route('/attendance')
def attendance():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM attendance WHERE user_id = %s", (session['user_id'],))
    attendance = cursor.fetchall()
    return render_template('attendance.html',attendance=attendance)

@app.route('/list_report')
def list_report():
    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT report.report_id, report.message, user.name 
        FROM report
        JOIN user ON report.user_id = user.user_id
    """)
    
    report = cursor.fetchall()
    cursor.close()
    return render_template('list_report.html',report=report)

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    cursor = mysql.connection.cursor()
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        task_description = request.form.get('task_description')
        due_date = request.form.get('due_date')
        due_time = request.form.get('due_time')

        if user_id and task_description and due_date and due_time:
            try:
                due_datetime = f"{due_date} {due_time}"

                cursor.execute("""
                    INSERT INTO tasks (user_id, task_description, due_datetime)
                    VALUES (%s, %s, %s)
                """, (user_id, task_description, due_datetime))
                mysql.connection.commit()
                flash("Task assigned successfully.", "success")
            except Exception as e:
                mysql.connection.rollback()
                flash(f"Error: {str(e)}", "danger")
        else:
            flash("Please fill in all fields.", "warning")

        cursor.close()
        return redirect(url_for('add_task'))
    
    cursor.execute("SELECT user_id, name FROM user")
    users = cursor.fetchall()
    cursor.close()

    return render_template('add_task.html', users=users)
    

@app.route('/monitor')
def monitor():
    return render_template('monitor.html')

@app.route('/check_attendance', methods=['GET', 'POST'])
def check_attendance():
    cursor = mysql.connection.cursor()
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        time = datetime.now()  
        status = request.form.get('status')

        cursor.execute("SELECT * FROM user WHERE user_id = %s", (user_id,))
        employee = cursor.fetchone()

        if not employee:
            return render_template('check_attendance.html', message="Employee not found.")

        cursor.execute("""
            SELECT * FROM attendance WHERE user_id = %s AND time = %s
        """, (user_id, time))
        existing_attendance = cursor.fetchone()

        if existing_attendance:
            cursor.execute("""
                UPDATE attendance
                SET hour = %s, status = %s
                WHERE user_id = %s AND time = %s
            """, (status, user_id, time))
            mysql.connection.commit()
            message = "Attendance updated successfully."
        else:
            cursor.execute("""
                INSERT INTO attendance (user_id,time,status)
                VALUES (%s, %s, %s)
            """, (user_id, time, status))
            mysql.connection.commit()
            message = "Attendance recorded successfully."
        
        cursor.close()
        return render_template('check_attendance.html', message=message)

    else:
        cursor.execute("SELECT * FROM user")
        users = cursor.fetchall()

        if not users:
            return render_template('check_attendance.html', message="No employees found in the database.")
        
        cursor.close()
        return render_template('check_attendance.html', users=users)




if __name__ == "__main__":
    app.run(debug=True)
