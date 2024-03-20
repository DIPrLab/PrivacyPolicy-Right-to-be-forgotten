"""
This script runs the PrivacyRA application using a development server.
"""

from os import environ
from PrivacyRA import app
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for
import uuid 
from math import ceil
import time
# MySQL database configuration
db = mysql.connector.connect(
    host="HostName",
    user="UserName",
    password="Password",
    database="Database Name"
)



@app.route('/process_payment', methods=['POST'])
def process_payment():
    # Extract form data
    amount = request.form['amount']
    currency = request.form['currency']
    payment_method = request.form['payment_method']
    account_name = request.form['account_name']
    account_number = request.form['account_number']
    expiry_date = request.form['expiry_date']
    securitycode = request.form['securitycode']
    consent = request.form.get('consent')
    transaction_id = uuid.uuid4().hex
    
    
    # Validate form data
    if not amount or not currency or not payment_method:
        return "Please fill out all required fields.", 400

    # Insert payment information into the database
    cursor = db.cursor()
    try:
        card_info_query = """
            INSERT INTO card_info (account_name, account_number, expiry_date, securitycode, consent)
            VALUES (%s, %s, %s, %s, %s)
        """
        card_info_data = (account_name, account_number, expiry_date, securitycode, consent)        
        cursor.execute(card_info_query, card_info_data)
        db.commit()
        # Retrieve the card_id of the newly inserted record
        card_id = cursor.lastrowid      
        payments_query = """
            INSERT INTO payments (card_id, amount, currency, payment_method, transaction_id)
            VALUES (%s, %s, %s, %s, %s)
        """
        payments_data = (card_id, amount, currency, payment_method, ip_address, transaction_id)        
        cursor.execute(payments_query, payments_data)
        db.commit()
        cursor.close()
        return redirect(url_for('payment_success'))
    except mysql.connector.Error as err:
        return f"Error processing payment: {err}", 500


@app.route('/details')
def details():
    # Fetch card data
    cursor = db.cursor(dictionary=True)
    search_input = request.args.get('search')
    
    if search_input:
        # Perform search query
        cursor.execute("SELECT * FROM card_info WHERE account_number = %s ", (search_input,))
        card_data = cursor.fetchall()
        total_records = len(card_data)
        total_pages = 1
        current_page = 1
        payments_data = {}
        for card in card_data:
            cursor.execute("SELECT * FROM payments WHERE card_id = %s ", (card['card_id'],))
            payments_data[card['card_id']] = cursor.fetchall()
    else:
        # Fetch card data with pagination
        cursor.execute("SELECT COUNT(*) FROM card_info WHERE flag = 0")
        result = cursor.fetchone()
        total_records = result['COUNT(*)'] if result else 0
        records_per_page = 100  # Adjust this value as needed
        total_pages = ceil(total_records / records_per_page)
        # Fetch payments data for the current page
        page = request.args.get('page', 1, type=int)
        offset = (page - 1) * records_per_page
        cursor.execute("SELECT * FROM card_info WHERE flag = 0 LIMIT %s, %s", (offset, records_per_page))
        card_data = cursor.fetchall()
        
        # Fetch payments data for all cards
        payments_data = {}
        for card in card_data:
            cursor.execute("SELECT * FROM payments WHERE card_id = %s AND flag = 0", (card['card_id'],))
            payments_data[card['card_id']] = cursor.fetchall()

        # Calculate current page
        current_page = min(page, total_pages) if total_pages > 0 else 1

    cursor.close()
    return render_template('details.html', card_data=card_data, payments_data=payments_data, total_pages=total_pages,  current_page=current_page)



# Route to handle the form submission
@app.route('/submit_forgotten_request', methods=['POST'])
def submit_forgotten_request():
    # Extract form data
    full_name = request.form['full_name']
    email = request.form['email']
    delete_type = request.form['delete_type']
    card_number = request.form.get('card_number', '')  # Default to empty string if not provided
    transaction_id = request.form.get('transaction_id', '')  # Default to empty string if not provided
    delete_method = request.form['delete_method']
    request_description = request.form['request_description']
    confirmation = request.form.get('confirmation')  # Check if checkbox is checked
    verification = request.form.get('verification')  # Check if checkbox is checked
    card_last_4_digits = card_number[-4:] 
    # Perform form validation
    if not (full_name and email and request_description):
        return "Please fill out all required fields.", 400
    cursor = db.cursor()
    if (card_number):
        cursor.execute("UPDATE card_info SET flag = 1 , account_number = %s WHERE account_number = %s", (card_last_4_digits , card_number))    
        db.commit() 
    elif (transaction_id):            
        cursor.execute("UPDATE payments SET flag = 1 WHERE transaction_id = %s", (transaction_id,))  
        db.commit() 
    # Process the request
    try:
        # Prepare and execute SQL query to insert data into delete_request table
        insert_query = """
            INSERT INTO delete_request (Name, Email, Number, Request_Description, deletetype)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (full_name, email, card_last_4_digits or transaction_id, request_description, delete_method)
        cursor.execute(insert_query, values)
        db.commit()  # Commit the transaction
        
        #deleterequestmethod(card_number,  transaction_id, card_last_4_digits)
        
        return redirect(url_for('delete_formrequest_success'))
    except mysql.connector.Error as err:
        db.rollback()  # Rollback the transaction if an error occurs
        return f"Error processing request: {err}", 500  



@app.route('/admin')
def admin():
    # Query the delete_request table to get the count of delete requests
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM delete_request where flag = 0")
    delete_request_count = cursor.fetchone()[0]
    cursor.close()
    return render_template('admin.html', delete_request_count=delete_request_count)

@app.route('/delete_all_requests', methods=['POST'])
def delete_all_requests():
    # Handle delete operation for all requests
    cursor = db.cursor()    
    user_id = uuid.uuid4().hex
    cursor.execute("SELECT * FROM delete_request where flag = 0")
    delete_requests = cursor.fetchall()    
    start_time = time.time()
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
    end_time = time.time()  
    delete_times = end_time - start_time
    print(f"Time taken to delete records: {delete_times} seconds")
    cursor.close()
    return redirect(url_for('admin'))    



@app.route('/activities')
def get_activities():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM activities")
    activities = cursor.fetchall()
    cursor.close()
    return render_template('activities.html', activities=activities)

if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT)