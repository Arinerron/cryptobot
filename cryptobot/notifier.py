#!/usr/bin/env python3

from cryptobot import config, logger
import requests

_NOTIFIER_LOCK = False # to prevent exceptions from causing recursion on "error" cause
SUBJECTS = {
    'error': 'Cryptobot Error Detected',
    'order': 'Cryptobot Order Placed',
    'flash': 'Cryptobot Flash Change Detected'
}


class TwilioNotifier:
    @staticmethod
    def send(subject: str, msg: str):
        try:
            from twilio.rest import Client
        except ImportError as e:
            logger.error('Unable to import Twilio')
            raise e


        account_sid = config.get('bot.notifications.twilio.account-sid')
        auth_token = config.get('bot.notifications.twilio.auth-token')
        messaging_service_sid = config.get('bot.notifications.twilio.service-sid')
        to_no = config.get('bot.notifications.twilio.to')

        assert account_sid, 'Missing twilio.account-sid'
        assert auth_token, 'Missing twilio.auth-token'
        assert messaging_service_sid, 'Missing twilio.service-sid'
        assert to_no, 'Missing destination phone number, twilio.to'

        logger.debug(f'Sending Twilio notification to phone number "{to_no}"...')
        client = Client(account_sid, auth_token)
        message = client.messages.create(body=msg, messaging_service_sid=messaging_service_sid, to=to_no)


class EmailNotifier:
    @staticmethod
    def send(subject: str, msg: str):
        to_email = config.get('bot.notifications.email.to')

        assert to_email, 'Missing destination email address, email.to'

        # XXX: should be url-encoded subject
        # XXX: check response to make sure it worked?
        response = requests.post('https://curlmail.co/arinerron@protonmail.com?subject=' + subject, data=msg)


def _get_handles(key: str) -> list:
    val = [
        str(x)
        for x in
        config.get(key, [])
    ]

    assert all([isinstance(x, str) for x in val]), 'All "handle" values must be either a string or dictionary'

    return ([str(x).lower() for x in val] if isinstance(val, list) else [str(val)])


def send(cause: str, *msg) -> bool:
    global _NOTIFIER_LOCK
    if _NOTIFIER_LOCK:
        return False

    _NOTIFIER_LOCK = True

    cause = str(cause).lower()
    msg = ' '.join([str(x) for x in msg])

    if cause not in SUBJECTS.keys():
        logger.warning(f'Unknown notification cause "{cause}"')

    subject = str(SUBJECTS.get(cause, f'Cryptobot {cause}'))

    if cause in _get_handles('bot.notifications.twilio.handle'):
        TwilioNotifier.send(subject, msg)
    if cause in [str(x).lower() for x in config.get('bot.notifications.email.handle', [])]:
        EmailNotifier.send(subject, msg)

    _NOTIFIER_LOCK = False
