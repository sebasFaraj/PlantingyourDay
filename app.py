
import os
import shutil

from datetime import datetime, date,timezone
from flask import Flask, flash, redirect, render_template,jsonify, request, session
from flask_session import Session
import sqlite3
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Getting source directory and configuring upload folder for the profile pictures
src_dir = os.getcwd()
dest_dir = src_dir + '/static/user_pro_pics'
app.config["UPLOAD_FOLDER"] = dest_dir

# Configure session to use filesystem (instead of signed cookies)


Session(app)



# Name dictionary to later reference and print according plant name
name_dict = {"red_plant":"Red Plant","blue_plant":"Blue Plant","sprout":"Sprout"}




@app.route("/")
def landing():
    return render_template("index.html")

# The home page seen after loging in
@app.route("/home")
@login_required
def index():
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    db.execute("SELECT plant,time,stage FROM owned WHERE owner = ?", [session["user_id"]])
    inventory = db.fetchall()

    db.execute("SELECT todo_id,time_set,time_end,goal,category FROM todo WHERE owner = ?", [session["user_id"]])
    TODOS = db.fetchall()

    return render_template("home.html", inventory=inventory, name_dict=name_dict, TODOS = TODOS)

@app.route("/delete/<todo_id>", methods = ["POST"])
@login_required
def delete_goal(todo_id):
    # Connect to database
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    # Get the goal's owner
    db.execute("SELECT owner FROM todo WHERE todo_id = ?", [todo_id])
    owner = db.fetchall()
    
    # If the owner is the one signed in, delete the goal and update the user's information
    if owner[0]["owner"] == session["user_id"]:
        db.execute("DELETE FROM todo WHERE todo_id = ?", [todo_id])
        db.execute("SELECT coins,completed FROM users WHERE id = ?", [session["user_id"]])
        user = db.fetchall()

        new_coins = user[0]["coins"] + 25
        new_completed = user[0]["completed"] + 1

        db.execute("UPDATE users set coins = ? WHERE id = ?", [new_coins, session["user_id"]])
        db.execute("UPDATE users set completed = ? WHERE id = ?", [new_completed, session["user_id"]])
        conn.commit()
        
    
    # Get the new list of TODOS
    db.execute("SELECT todo_id,time_set,time_end,goal,category FROM todo WHERE owner = ?", [session["user_id"]])
    TODOS = db.fetchall()

    # Render the template containing the new goals and jsonify it for use later
    text = "Congrats on completing your goal :), you get 25 coins"
    return jsonify('',render_template("goals.html", TODOS = TODOS, text=text))


@app.route("/update/<todo_id>", methods = ["POST"])
@login_required
def update_goal(todo_id):
    # Conneting to the database
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    new_text = request.form.get("new_text")
    value = request.form.get("value")

    print(new_text)
    print(value)

    if new_text == "" or new_text == None:
        print(new_text)
        flash("Needs to be filled out")
        return redirect("/")

    db.execute("UPDATE todo SET goal = ? WHERE todo_id = ?", [new_text,todo_id])
    
    db.execute("SELECT todo_id,time_set,time_end,goal,category FROM todo WHERE owner = ?", [session["user_id"]])
    TODOS = db.fetchall()
    

    conn.commit()
    conn.close()
    return jsonify('',render_template("goals.html", TODOS = TODOS))

@app.route("/reload", methods = ["POST"])
@login_required
def reload():
    # Connect to database
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()
 
    # Get the new list of TODOS
    db.execute("SELECT todo_id,time_set,time_end,goal,category FROM todo WHERE owner = ?", [session["user_id"]])
    TODOS = db.fetchall()
    return jsonify('',render_template("goals.html", TODOS = TODOS))


@app.route("/add", methods = ["POST"])
@login_required
def add():
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    goal = request.form.get("goal")
    
    category = request.form.get("category")

    time_end = request.form.get("end_time")
    if time_end:
        time_end = time_end.replace("T"," ")

    current = datetime.now()
    date_string = current.strftime("%d-%m-%Y %H:%M") 

    if goal == "":
        flash("To add a goal, please fill out all fields")
        conn.close()
        return redirect("/")


    db.execute("INSERT INTO todo (owner,time_set,time_end,goal,category) Values(?,?,?,?,?)", [session["user_id"],date_string,time_end,goal,category])

    db.execute("SELECT todo_id,time_set,time_end,goal,category FROM todo WHERE owner = ?", [session["user_id"]])
    TODOS = db.fetchall()
    text = "Goal Added"

    conn.commit()
    conn.close()
    return jsonify('',render_template("goals.html", TODOS = TODOS, text=text))

@app.route("/change_profile_picture", methods=["GET", "POST"])
@login_required
def change_picture():

    # When posted
    if request.method == "POST":
        
        # Check if picture was posted
        if "profile_picture" not in request.files:
            flash("No picture was uploaded, try again")
            return redirect("/change_profile_picture")
        
        
        # Request the picture from the form
        pro_pic = request.files["profile_picture"]
        # Rename it and save according to the user_id
        pro_pic.filename = str(session["user_id"]) + ".jpg"
        path = os.path.join(app.config["UPLOAD_FOLDER"], pro_pic.filename)
        
        pro_pic.save(path)
        
        flash("profile picture has been chagned succesfully")
        return redirect ("/home")

    else:
        return render_template("change_pro_pic.html")    

@app.route("/login", methods=["GET", "POST"])
def login():

    # DESIGN ADAPTED FROM DISTRIBUTION CODE FROM CS50 FINANCE

    # Connect to database
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("must provide username")
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return redirect("/login")


        # Query database for username
        db.execute("SELECT * FROM users WHERE username = ?", [request.form.get("username")]) 
        rows = db.fetchall()


        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username and/or password")
            return redirect("/login")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["pro_pic"] = str(rows[0]["id"]) + ".jpg"
        session["username"] = rows[0]["username"]


        # Redirect user to home page
        return redirect("/home")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    # DESIGN ADAPTED FROM MY SOLUTION IN CS50 FINANCE
    # Had to be mostly changed due to the new elements introduces
        
    if request.method == "POST":
        conn = sqlite3.connect('data.db')
        conn.row_factory = sqlite3.Row
        db = conn.cursor()
    
        # Error Checking
        if request.form.get("username") == "":
            flash("All fields must be filled out, try again")
            return redirect("/register")

        if request.form.get("password") == "":
            flash("All fields must be filled out, try again")
            return redirect("/register")

        if request.form.get("password") != request.form.get("confirmation"):
            flash("The passwords do not match, please try again")
            return redirect("/register")

        # Checks is username is taken
        user = db.execute("SELECT * FROM users WHERE username = ?", [request.form.get("username")])
        if len(user.fetchall()) != 0:
            flash("Username is taken")
            return redirect("/register")

        # Hashes the given password
        psw_hash = generate_password_hash(request.form.get("password"), method="pbkdf2:sha256")

        # Gets current date and time
        current = date.today()
        date_string = current.strftime("%B %d, %Y")

        # Inserts new user into database alongside account creation date
        db.execute("INSERT INTO users (username,hash,creation_time,coins) VALUES(?, ?,?,?)",
                   [request.form.get("username"), psw_hash, date_string,0])
        conn.commit()

        # Get User ID
        db.execute("SELECT id FROM users WHERE username = ?", [request.form.get("username")])
        id = db.fetchall()

        # Get source and destination dir
        src_dir = os.getcwd()
        dest_dir = src_dir + '/static/user_pro_pics'

        # get source file (The default picture)
        src_file = os.path.join(src_dir, "static/default.jpg")
        # copy into user_pro_pics
        shutil.copy(src_file,dest_dir)
        
        dst_file = os.path.join(dest_dir, "default.jpg")
        new_name = os.path.join(dest_dir, str(id[0]["id"]) + ".jpg")
        # Rename to user id.jpg
        os.rename(dst_file, new_name)

        conn.commit()
        return redirect("/home")

    else:
        return render_template("registration.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # DESIGN ADAPTED FROM DISTRIBUTION CODE FROM CS50 FINANCE

    # Forget any user_id
    session.clear()

    # Redirect user to landing page
    return redirect("/")

@app.route("/account_information")
@login_required
def account_info():
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    db.execute("SELECT username,coins,creation_time,completed FROM users WHERE id = ?", [session["user_id"]])
    user = db.fetchall()

    conn.close()
    return render_template("accinfo.html", user = user[0])

@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_pswd():
    # Setting up SQLITE connection and cursor
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    if request.method == "POST":

        # Error checking
        db.execute("SELECT hash FROM users WHERE id = ?", [session["user_id"]])
        user = db.fetchall()

        # Variables to avoid calling function again
        new_pswd = request.form.get("new_pswd")
        confirm_pswd = request.form.get("confirm_pswd")
        current_pswd = request.form.get("current_pswd")

        if new_pswd == "" or current_pswd == "" or confirm_pswd == "":
            flash("Please fill out all fields")
            return redirect("/change_password")

        if new_pswd != confirm_pswd:
            flash("Passwords don't match, please try again")
            return redirect("/change_password")

        # If the current password is correct, change to the new password
        if check_password_hash(user[0]["hash"], current_pswd):
            db.execute("UPDATE users SET hash = ? WHERE id = ?",[generate_password_hash(new_pswd), session["user_id"]])

        else:
            flash("Your current password is wrong, try again")
            return redirect("/change_password")

        flash("Password has been succesfully changed")
        conn.commit()
        conn.close()
        return redirect("/home")

    else:
        return render_template("change.html")

@app.route("/account_deletion", methods=["GET", "POST"])
@login_required
def acc_delete():
    # Setting up SQLITE connection and cursor
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    if request.method == "POST":
        db.execute("SELECT hash FROM users WHERE id = ?", [session["user_id"]])
        user = db.fetchall()

        if request.form.get("current_pswd") == "":
            flash("All Fields must be filled out, please try again")
            return redirect("/account_deletion")
        

        if check_password_hash(user[0]["hash"], request.form.get("current_pswd")):
            db.execute("DELETE FROM users WHERE id = ?", [session["user_id"]])

        else:
            flash("Password is wrong, try again")
            return redirect("/account_deletion")

        conn.commit()
        conn.close()
        session.clear()
        return redirect("/")

    else:
        return render_template("delete.html")

@app.route("/shop", methods=["GET", "POST"])
@login_required
def shop():
    # Setting up SQLITE connection and cursor
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    db = conn.cursor()

    if request.method == "POST":
        # Returns "value" of button pressed
        plant_name = request.form.get("submit")

        # Get user
        db.execute("SELECT username,coins FROM users WHERE id = ?", [session["user_id"]])
        user = db.fetchall()

        # Get requested plant
        db.execute("SELECT id,name,price FROM plants WHERE name = ?", [plant_name])
        plant = db.fetchall()

        # Get and format date/time
        current = datetime.now()
        date_string = current.strftime("%d/%m/%Y %H:%M:%S")

        # If user can afford it
        if user[0]["coins"] > plant[0]["price"]:
            # Insert into owned table
            db.execute("INSERT INTO owned(owner,plant,time,stage) VALUES (?,?,?,?)",[session["user_id"],plant_name,date_string ,1])
            # Update the user's number of coins
            db.execute("UPDATE users SET coins = ? WHERE id = ?", [user[0]["coins"] - plant[0]["price"], session["user_id"]])
            
            flash("Bought " + name_dict[plant_name])
            
            conn.commit()
            conn.close()
            return redirect("/shop")
        else:
            flash("Not enough currency")
            return redirect("/shop")

    else:

        # Get the plant inventory from the database
        db.execute("SELECT name,price,description FROM plants")
        plants = db.fetchall()
        print(len(plants))

        # Find the length of each row for the display
        length = round((len(plants) / 3) + 0.26) 
        length = int(length)
        
        # Render using the plants
        return render_template("shop.html", plants = plants, length = length, name_dict = name_dict)