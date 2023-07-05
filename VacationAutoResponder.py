from getpass import getpass
from cryptography.fernet import Fernet
import imaplib
import smtplib
from datetime import date
import email
import time
import random

class VacationAutoResponder:
    def __init__(self, email_id, reply):
        self.email_id = email_id
        self.reply = reply
        self.fernet = Fernet(Fernet.generate_key())
        #password encrypted  and stored within object
        self.password = self.fernet.encrypt(getpass("Password: ").encode())

    def login(self):
        imap = imaplib.IMAP4_SSL('imap.gmail.com')
        imap.login(self.email_id, self.fernet.decrypt(self.password).decode())
        return imap
        
    def logout(self, imap):
        imap.logout()

    def is_no_reply(self, sender, subject):
        no_reply_terms = ["no-reply", "noreply", "do not reply", "do-not-reply", "donotreply", "automated message", "auto-generated message", "alternative contact methods", "contact information", "alert", 'newsletter', "notif", "unsubscribe"]
        for term in no_reply_terms:
            if term in sender.lower() or term in subject.lower():
                return True
        return False
    
    def convert_to_string(self, mime_obj_list):
        decoded = email.header.decode_header(mime_obj_list)
        result = ""
        for d, c in decoded:
            if isinstance(d, bytes):
                result += d.decode(c or 'ascii')
            else:
                result += d
        return result
        

    def send_single_reply(self, to, subject, smtp):
        reply = email.message.EmailMessage()
        subject = " ".join([s.strip('\r\n') for s in subject.split('\n')])
        print(subject)
        reply['Subject'] = f'Re: {subject}'
        reply['From'] = self.email_id
        reply['To'] = to.split("<")[-1].strip(">")
        reply.set_content(self.reply)
        smtp.send_message(reply)

    def check_and_reply(self, imap):
        imap.select('INBOX')
        today = date.today()
        today_str = today.strftime('%d-%b-%Y')
        status, data = imap.search(None, f'(UNSEEN) (SINCE {today_str})')
        emails = data[0].split()
        smtp = smtplib.SMTP_SSL('smtp.gmail.com')
        smtp.login(self.email_id, self.fernet.decrypt(self.password).decode())
        for num in emails:
            typ, data = imap.fetch(num, '(BODY.PEEK[])')
            if data == None or data[0] == None:
                continue
            message = email.message_from_bytes(data[0][1])
            sender, subject = self.convert_to_string(message["From"]), self.convert_to_string(message["Subject"])
            # check sender and subject for no reply terms
            if self.is_no_reply(sender, subject):
                #no reply mails are lef as it is
                imap.store(num, '+X-GM-LABELS', 'Vacation-NoReply')
                imap.copy(num, 'Vacation-NoReply')
                print(f"Skipped {sender} as it is no reply")
            else:
                #replied mails are moved to Vacation and removed from inbox
                self.send_single_reply(sender, subject, smtp)
                print(f"Sent auto reply to {sender}")
                imap.store(num, '+X-GM-LABELS', 'Vacation-Replied')
                imap.copy(num, 'Vacation-Replied')
            # remove from inbox
            imap.store(num, '+FLAGS', '\\Deleted')
            imap.expunge()
            
        smtp.quit()
        imap.close()

            

    def run(self):
        imap = self.login()
        while True:
            try:
                self.check_and_reply(imap)
                interval = random.randint(45, 120)
                print(f'Waiting for {interval}s')
                time.sleep(interval)
            except KeyboardInterrupt:
                print("Stopping Auto responder. Hope you had a relaxing vacation!")
                break
        self.logout(imap)


email_id = input("Enter Email ID: ")
reply = input("Enter reply message(Leave Blank for default):\n")

if reply == "":
    reply = "Hi, I am out for vacation and will reply as soon as I return. Thank you."

auto_responder = VacationAutoResponder(email_id, reply)

auto_responder.run()