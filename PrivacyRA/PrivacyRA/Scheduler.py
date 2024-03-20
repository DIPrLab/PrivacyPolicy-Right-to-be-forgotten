from os import environ
from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import uuid 
from math import ceil
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

app = Flask(__name__)
# MySQL database configuration
db = mysql.connector.connect(
    host="HostName",
    user="UserName",
    password="Password",
    database="Database Name"
)


# Define the job to be scheduled
def my_job():
    cursor = db.cursor()    
    user_id = uuid.uuid4().hex
    cursor.execute("SELECT * FROM delete_request where flag = 0")
    delete_requests = cursor.fetchall()
    for request in delete_requests:
        length = len(request[3])
        if request and request[6] == 1:
            if len(request[3]) <= 20:
                type = "card"
                card_number = request[3]            
                # Update card_info table
                cursor.execute("""
                    UPDATE card_info
                    SET 
                        account_number = %s,
                        account_name = 'Data Deleted',
                        expiry_date = NULL,
                        securitycode = NULL,
                        consent = NULL,
                        flag = 0
                    WHERE account_number = %s
                """, (card_number[-4:] , card_number,))
                # Insert into activities table
                cursor.execute("""
                    INSERT INTO activities (message, userid, type)
                    VALUES (%s, %s, %s)
                """, ('Card number ending with ' + card_number[-4:]  + ' has been deleted from our database according to the user request', user_id, type))
                cursor.execute("UPDATE delete_request SET flag = 1 WHERE deleteid = %s", (request[0],))
                db.commit()         
            if len(request[3]) >= 21:
                # Insert into activities table
                cursor.execute("""
                    INSERT INTO activities (message, userid, type)
                    SELECT 
                        CONCAT('Payment of ', p.currency, ' ', p.amount, ' is paid by using card ending with ', c.account_number),
                        %s,
                        'payment'
                    FROM
                        payments AS p
                    INNER JOIN card_info AS c ON p.card_id = c.card_id
                    WHERE
                        p.transaction_id = %s
                """, (user_id, request[3]))
                # Delete payment record and insert activity in a single query
                cursor.execute("""
                    DELETE FROM payments
                    WHERE transaction_id = %s
                """, (request[3],))
                cursor.execute("UPDATE delete_request SET flag = 1 WHERE deleteid = %s", (request[0],))
                db.commit()  # Commit the transaction
        if request and request[6] == 2:
            # Retrieve card_id associated with the provided account_number
            cursor.execute("SELECT card_id FROM card_info WHERE account_number = %s", (request[3],))
            card_id = cursor.fetchone()

            if card_id:
                card_id = card_id[0]  # Extract the card_id value from the tuple

                # Retrieve payment details associated with the card_id
                cursor.execute("SELECT currency, amount FROM payments WHERE card_id = %s", (card_id,))
                payments_data = cursor.fetchall()

                # Insert a record into the activities table for each payment
                for payment in payments_data:
                    currency, amount = payment
                    message = f"Payment of {currency} {amount} is paid by using card ending with {request[3]}"
                    cursor.execute("INSERT INTO activities (message, userid, type) VALUES (%s, %s, %s)", (message, user_id, 'card'))

                # Delete the payments associated with the card_id
                cursor.execute("DELETE FROM payments WHERE card_id = %s", (card_id,))
                db.commit()
            else:
                print("No card found with the provided account number.")

            cursor.execute("UPDATE delete_request SET flag = 1 WHERE deleteid = %s", (request[0],))
            db.commit()  # Commit the transaction
        if request and request[6] == 3:
            cursor.execute("SELECT card_id FROM card_info WHERE account_number = %s", (request[3],))
            card_id = cursor.fetchone()

            # Retrieve payment details associated with the card_id
            cursor.execute("SELECT currency, amount FROM payments WHERE card_id = %s", (card_id))
            payments_data = cursor.fetchall()

            # Insert a record into the activities table for each payment
            for payment in payments_data:
                currency, amount = payment
                message = f"Payment of {currency} {amount} is paid by using card ending with {request[3][-4:]}"
                cursor.execute("INSERT INTO activities (message, userid, type) VALUES (%s, %s, %s)", (message, user_id, 'card'))

            # Delete the payments associated with the card_id
            cursor.execute("DELETE FROM payments WHERE card_id = %s", (card_id))
            # Update card_info table
            cursor.execute("""
                UPDATE card_info
                SET 
                    account_number = %s,
                    account_name = 'Data Deleted',
                    expiry_date = NULL,
                    securitycode = NULL,
                    consent = NULL,
                    flag = 0
                WHERE account_number = %s
            """, (request[3][-4:] , request[3],))
            cursor.execute("""
                    INSERT INTO activities (message, userid, type)
                    VALUES (%s, %s, %s)
                """, ('Card number ending with ' + request[3][-4:]  + ' has been deleted from our database according to the user request', user_id, 'card'))
            cursor.execute("UPDATE delete_request SET flag = 1 WHERE deleteid = %s", (request[0],))
            db.commit()  # Commit the transaction
    cursor.close()

# Schedule the job to run at 1 AM PST every day
scheduler.add_job(my_job, 'cron', hour=1, timezone=pytz.timezone("America/Los_Angeles"))

# Start the scheduler
scheduler.start()

if __name__ == '__main__':
    # Create scheduler instance
    scheduler = BackgroundScheduler()

    # Schedule the delete_requests function to run every day at 1AM PST
    scheduler.add_job(delete_requests, 'cron', hour=21, timezone='America/Los_Angeles')

    # Start the scheduler
    scheduler.start()

    # Keep the Flask app running
    HOST = environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT)