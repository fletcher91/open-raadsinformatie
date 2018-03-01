#! /usr/bin/env python

import sendgrid
from sendgrid.helpers.mail import Email, Mail, Content

from ocd_frontend import settings


sg = sendgrid.SendGridAPIClient(apikey=settings.SENDGRID_API_KEY)
from_address = Email(settings.SENDGRID_FROM_ADDRESS)


def send(to, subject, content):
    to_addr = Email(to)
    content = Content('text/plain', content)
    message = Mail(from_address, subject, to_addr, content)
    return sg.client.mail.send.post(request_body=message.get())
