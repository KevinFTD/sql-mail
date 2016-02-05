#!/usr/bin/python
# coding:utf-8
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from traceback import format_exc
import logging
import os

class ServerNullException(Exception):
    """Exception that mail server is null """

class Email(object):
    """connect to some mail server and send content to recipients

        wrap smtplib.SMTP, and achieve following features more convenient.
        1. cc and bcc.
        2. display image in content.
           By adding html tag <img src="cid:user-defined-tag"> into content
           'user-defined-tag' is the tag when you call add_one_image(self, cid_tag, file_name)
    """

    def __init__(self, me="username<username@gmail.com>", recipients=None,
                 subject=None, content=None, cc_list=None, bcc_list=None):
        """
        :param me: mail sender
        :param recipients: mail recipients, a list
        :param subject: mail subject
        :param content: mail content which can be html string
        :param cc_list: cc recipients, a list
        :param bcc_list: bcc recipients, a list
        :return:
        """
        self.me = me
        self.recipients = recipients if recipients else list()
        self.subject = subject
        self.content = content
        self.cc_list = cc_list if cc_list else list()
        self.bcc_list = bcc_list if bcc_list else list()

        self.msg = None
        self.image_list = list()
        # for child class
        self.additional_content = None

    def set_content(self, value):
        self.content = value

    def set_cc_list(self, value):
        if isinstance(value, list):
            self.cc_list = value

    def set_bcc_list(self, value):
        if isinstance(value, list):
            self.bcc_list = value

    def _prepare(self):

        # 尝试用utf8和GBK解码邮件内容和主题成unicode
        content = self.additional_content + self.content if self.additional_content else self.content
        subject = self.subject

        try:
            content = unicode(content, 'utf8')
            sub = unicode(subject, 'utf8')
        except UnicodeDecodeError:
            try:
                content = unicode(content, 'gbk')
                sub = unicode(subject, 'gbk')
            except UnicodeDecodeError:
                logging.error("cannot convert content or sub into unicode")
                raise
        # 已经是unicode
        except TypeError:
            pass

        self.msg = MIMEMultipart('related')
        self.msg['Subject'] = subject
        self.msg['From'] = self.me
        self.msg['To'] = ";".join(self.recipients)
        self.msg['Cc'] = ";".join(self.cc_list)
        self.msg['Bcc'] = ";".join(self.bcc_list)
        
        txt = MIMEText(content.encode('utf-8'), 'html', 'UTF-8')
        self.msg.attach(txt)

        for image in self.image_list:
            self.msg.attach(image)

    def add_one_image(self, cid_tag, file_path):
        """
        In order to show picture in mail content,
        you should add an cid tag in the mail html content,
        such as <img src="cid:user-defined-tag">

        :param cid_tag: img src tag
        :param file_path: the path of the picture
        :return:
        """
        image = MIMEImage(open(file_path, 'rb').read())
        image.add_header('Content-ID', '<'+cid_tag+'>')
        self.image_list.append(image)

    def send_mail(self, mail_server=None, username=None, password=None):
        if mail_server is None:
            raise ServerNullException("Mail server CANNOT be NULL")

        self._prepare()

        retry_times = 0
        # 每隔三秒重试一次 100次后退出
        while retry_times <= 100:
            result = self._send_mail(mail_server, username, password)
            if result:
                break
            time.sleep(3)  # 等待3s
            retry_times += 1

    def _send_mail(self, mail_server, username, password):
        try:        
            s = smtplib.SMTP(mail_server)

            if username:
                try:
                    s.login(username, password)
                except smtplib.SMTPAuthenticationError as auth_error:
                    if auth_error.smtp_code == 530:
                        s = smtplib.SMTP_SSL(mail_server)
                        s.login(username, password)
                    else:
                        raise auth_error

            s.sendmail(self.me, self.recipients+self.cc_list+self.bcc_list, self.msg.as_string())
            s.close()
            return True
        except Exception:
            logging.error(format_exc())
            return False


class NiceReportMail(Email):
    def __init__(self, me="username<username@gmail.com>", recipients=None,
                 subject=None, content=None, cc_list=None, bcc_list=None):
        super(NiceReportMail, self).__init__(me, recipients, subject, content, cc_list, bcc_list)

        self.tmp_pic_list = list()
        self.style = None
        self.clear_tmp_pic = False

    def set_clear_pic(self, clear_or_not):
        self.clear_tmp_pic = clear_or_not

    def set_style_template(self, style_template):
        """
        style template is a file that contains css like:

        <style type="text/css">
        ...
        ...
        ...
        </style>

        :param style_template:
        :return:
        """
        try:
            with open(style_template) as fd:
                file_str = fd.read()
                self.style = file_str.decode("utf-8")
        except IOError:
            self.style = str()

    def set_template_content(self, mail_template, template_data):
        """
        use jinja2 template as the mail content template like:

        <table>
            <thead>
                <tr>
                    {% for item in header %}
                    <th>{{item}}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for item in body %}
                    <tr>
                        {% for value in item %}
                        <td>{{ value|default("N/A") }}</td>
                        {% endfor %}
                    </tr>
                {% endfor %}
            </tbody>
        </table>

        :param mail_template: jinja2 template file
        :param template_data: dict for jinja2 template
        :return:
        """

        path, template_file = os.path.split(mail_template)

        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader(path))
        template = env.get_template(template_file)
        self.content = template.render(template_data)

    def add_images(self, pic_dict):
        """
        add many images at one time

        pic_dict is a dict like:
        {
            "cid_tag1": file1,
            "cid_tag2": file2
        }

        :param pic_dict:
        :return:
        """
        if isinstance(pic_dict, dict):
            for tag in pic_dict.keys():
                self.add_one_image(tag, pic_dict[tag])
                self.tmp_pic_list.append(pic_dict[tag])

    def send_mail(self, mail_server=None, username=None, password=None):
        if not self.style:
            # set default style
            try:
                with open("%s/templates/default-style.html" % (os.path.dirname(os.path.abspath(__file__)))) as fd:
                    file_str = fd.read()
                    self.style = file_str.decode("utf-8")
            except IOError:
                self.style = str()

        # pass style to parent class by additional_content
        self.additional_content = self.style
        super(NiceReportMail, self).send_mail(mail_server, username, password)

        if self.clear_tmp_pic:
            for tmp_file in self.tmp_pic_list:
                os.remove(tmp_file)

def test1():
    email = Email(me="kevin<kevin@qq.com>", recipients=["kevin@foxmail.com"],
                  subject="Email module Test", content="""Hello, I'm mail module.<br/><img src="cid:mypic" />""")
    email.add_one_image("mypic", "demo_files/fighting.jpg")
    email.send_mail(mail_server="smtp.qq.com", username="kevin@qq.com", password="qq_application_code")

def test2():
    email = NiceReportMail(me="kevin<kevin@qq.com>", recipients=["kevin@foxmail.com"],
                  subject="Email module Test Nice looking mail",
                  content="""
                    <h2>Hello, I'm mail module.</h2>
                    <table>
                        <thead>
                            <tr>
                                <td>Date</td><td>value</td>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>20160102</td><td>276</td>
                            </tr>
                            <tr>
                                <td>20160103</td><td>235</td>
                            </tr>
                            <tr>
                                <td>20160104</td><td>280</td>
                            </tr>
                        </tbody>
                    </table>
                """)
    email.send_mail(mail_server="smtp.qq.com", username="kevin@qq.com", password="qq_application_code")

if __name__ == "__main__":
    #test1()
    test2()
