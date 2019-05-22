import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class Mail():
    def __init__(self, login, password, host, port):
        self.login = login
        self.password = password
        self.host = host
        self.port = port

    def init_error_mailer(self, from_addr, send_errors_to, error_subj):
        """
        Настраивает обработчик отправки ошибок автоматом на почту админу
        :param from_addr: - от кого
        :param send_errors_to:  - кому лист, обычно админ
        :param error_subj: - тема
        :return:
        """
        self.from_addr = from_addr
        self.send_errors_to = send_errors_to
        self.error_subj =error_subj


    def send(self, email_from, email_to, subject, html, file=None, filename=None):
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = ", ".join(email_to) if isinstance(email_to,(list,)) else email_to
        msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html'))
        if file:
            p = MIMEBase('application', 'octet-stream')
            p.set_payload((file).read())
            encoders.encode_base64(p)
            p.add_header('Content-Disposition', 'attachment; filename= %s' % filename if filename else 'attachment' )
            msg.attach(p)

        s = smtplib.SMTP(self.host, self.port)
        s.starttls()
        s.login(self.login, self.password)
        text = msg.as_string()
        res = s.sendmail(email_from, email_to, text)
        s.quit()
        return res

    def send_error(self, e: str):
        """
        Отправка сообщения об ошибке администратору
        :param e: - объект ошибки
        :return:
        """
        if self.send_errors_to and self.from_addr and self.error_subj:
            res = self.send(
                self.from_addr,
                self.send_errors_to.split(","),
                self.error_subj,
                e,


            )
            return res
        else:
            print('FATAL: Cant send error msg due to config section [error_mailing] problem')

