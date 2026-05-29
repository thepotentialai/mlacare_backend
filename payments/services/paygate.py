import requests
from django.conf import settings


PAY_URL = 'https://paygateglobal.com/api/v1/pay'
STATUS_URL = 'https://paygateglobal.com/api/v1/status'


def initiate_paygate_payment(phone_number: str, amount: str, identifier: str, network: str):
    payload = {
        'auth_token': settings.PAYGATE_KEY,
        'phone_number': phone_number,
        'amount': amount,
        'description': 'Don MLA Doctors',
        'identifier': identifier,
        'network': network,
    }
    response = requests.post(PAY_URL, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def verify_paygate_status(tx_reference: str):
    payload = {
        'auth_token': settings.PAYGATE_KEY,
        'tx_reference': tx_reference,
    }
    response = requests.post(STATUS_URL, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()
