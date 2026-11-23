# from django.db import connection
import decimal

from django.db import models
from django.db.models import Min, Sum, Max, Q, F, Prefetch, Subquery, OuterRef, Value
from django.db.models.functions import Coalesce
from apps.sales.models import Client, Order, OrderDetail, LoanPayment


def total_remaining_repay_loan(order_detail_set=None):
    # Legacy GLP loan-balance logic removed; keep neutral behavior.
    return decimal.Decimal(0)


def total_remaining_return_loan(order_detail_set=None):
    # Legacy GLP return-loan logic removed; keep neutral behavior.
    return 0


def repay_loan(loan_payment_set=None):
    response = 0

    for lp in loan_payment_set:

        # Los campos `quantity`/`price` fueron reemplazados por `pay`.
        response += lp.pay

    return response


def return_loan(loan_payment_set=None):
    response = 0

    for lp in loan_payment_set:
        response += getattr(lp, 'quantity', 0)

    return response


def total_repay_loan(order_detail_set=None):
    response = 0
    for d in order_detail_set:
        loan_payment_set = d.loanpayment_set.all()
        response = response + repay_loan(loan_payment_set=loan_payment_set)

    return response


def total_repay_loan_with_vouchers(order_detail_set=None):
    response = 0
    for d in order_detail_set:
        loan_payment_set = d.loanpayment_set.all()
        response = response + repay_loan_with_vouchers(loan_payment_set)
    return response


def repay_loan_with_vouchers(loan_payment_set=None):
    response = 0
    for lp in loan_payment_set:
        if lp.pay > 0:
            transaction_payment_set = lp.transactionpayment_set.all()
            for t in transaction_payment_set:
                if t.type == 'F':
                    response = response + getattr(t, 'number_of_vouchers', t.payment)
    return response


def total_return_loan(order_detail_set=None):
    response = 0
    for d in order_detail_set:
        loan_payment_set = d.loanpayment_set.all()
        response = response + return_loan(loan_payment_set)
    return response


def total_cash_flow_spending(cashflow_set=None):
    response = decimal.Decimal(0)
    for cf in cashflow_set:
        if cf.type == 'S':
            response = response + cf.total
    return response


def get_cash_flow(order=None, transactionpayment=None):
    response = None
    if transactionpayment.type == 'D' or transactionpayment.type == 'E':
        for cf in order.cashflow_set.all():
            if cf.type == 'D' or cf.type == 'E':
                response = cf
                break
    return response

