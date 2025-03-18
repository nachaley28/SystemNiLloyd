from flask import Flask, render_template, redirect, url_for, session,send_file,flash,request
from flask_mysqldb import MySQL
import base64
import io


app = Flask(__name__)

def encode_b64(data):
    return base64.b64encode(data).decode() if data else None
app.jinja_env.filters['b64encode'] = encode_b64

app.secret_key = 'your_secret_key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'mitscoop'

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
    if 'user_id' not in session:
        return redirect(url_for('landing'))
    return render_template('home.html') 

@app.route('/report',methods=["GET", "POST"])
def report():
    if 'user_id' not in session:
        return redirect(url_for('landing'))
    message = request.form.get('message')  
    image = request.files.get('image')   
        
    if image:  
        image_data = image.read()  

            #
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO report (message, image) VALUES (%s, %s)", (message, image_data))
        mysql.connection.commit()
        cursor.close()

           
        return redirect(url_for("home"))

    else:
          
       
        return render_template('report.html') 

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
    return render_template('admin.html')

@app.route('/check')
def check():
    if 'user_id' not in session:
        return redirect(url_for('landing'))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT report_id, message, image FROM report")
    reports = cursor.fetchall()
    cursor.close()

    return render_template('check.html', reports=reports)

@app.route('/view/<report_id>')
def view_image(report_id):
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT image FROM report WHERE report_id = %s", (report_id,))
    report = cursor.fetchone()


    if report and report[0]:
        image_data = report[0] 
        
        
        return send_file(io.BytesIO(image_data), mimetype='image/jpeg')

    else:
        return "Image not found", 404
    

@app.route('/delete/<report_id>', methods=['POST'])
def delete_report(report_id):
    
        cursor = mysql.connection.cursor()

        cursor.execute("DELETE FROM report WHERE report_id = %s", (report_id,))
       
        mysql.connection.commit()

        return redirect(url_for('check')) 



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
    return render_template('attendance.html')

@app.route('/list_report')
def list_report():
    return render_template('list_report.html')

@app.route('/check_attendance', methods=['GET', 'POST'])
def check_attendance():
    cursor = mysql.connection.cursor()
    
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        date = request.form.get('date')
        status = request.form.get('status')

        # Check if employee exists
        cursor.execute("SELECT * FROM user WHERE user_id = %s", (user_id,))
        employee = cursor.fetchone()

        if not employee:
            return render_template('check_attendance.html', message="Employee not found.")

        # Insert or update attendance
        cursor.execute("""
            SELECT * FROM attendance WHERE user_id = %s AND date = %s
        """, (user_id, date))
        existing_attendance = cursor.fetchone()

        if existing_attendance:
            cursor.execute("""
                UPDATE attendance
                SET status = %s
                WHERE user_id = %s AND date = %s
            """, (status, user_id, date))  # Fix the update query to reference user_id and date properly
            mysql.connection.commit()
            message = "Attendance updated successfully."
        else:
            cursor.execute("""
                INSERT INTO attendance (user_id, date, status)
                VALUES (%s, %s, %s)
            """, (user_id, date, status))  
            mysql.connection.commit()
            message = "Attendance recorded successfully."
        
        cursor.close()
        return render_template('check_attendance.html', message=message)

    else:
        # Fetch all employees for the dropdown
        cursor.execute("SELECT * FROM user")  # Make sure table and column names are correct
        users = cursor.fetchall()

        if not users:
            return render_template('check_attendance.html', message="No employees found in the database.")
        
        cursor.close()
        return render_template('check_attendance.html', users=users)







if __name__ == "__main__":
    app.run(debug=True)
