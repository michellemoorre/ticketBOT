import smtplib
from email.message import EmailMessage

email = 'mikhail.khrshkh@gmail.com'
email2 = 'michaelmar444@gmail.com'
password = 'YiK-mQP-76k-Lc7'

msg = EmailMessage()
msg.set_content('Вы купили билет')

msg['Subject'] = 'Билеты'
msg['From'] = email
msg['To'] = 'michaelmar444@gmail.com'

s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
s.login(email, password)
s.send_message(msg)
s.quit()