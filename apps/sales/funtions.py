# from django.db import connection
from django.db import models
from django.db.models import Min, Sum, Max, Q, F, Prefetch, Subquery, OuterRef, Value
from django.db.models.functions import Coalesce
from apps.sales.models import Client, Order, OrderDetail, LoanPayment


def total_remaining_repay_loan(order_detail_set=None):
    response = 0

    for d in order_detail_set:

        multiply = d.quantity_sold * d.price_unit

        if d.unit.name == 'G' or d.unit.name == 'GBC':
            loan_payment_set = d.loanpayment_set.all()
            response += (multiply - repay_loan(loan_payment_set))

    return response


def total_remaining_return_loan(order_detail_set=None):
    response = 0
    product__array = [1, 12, 2, 3]
    for d in order_detail_set:
        if d.unit.name == 'B' and d.product.id in product__array:
            loan_payment_set = d.loanpayment_set.all()
            response += (d.quantity_sold - return_loan(loan_payment_set))
            # val = d.return_loan_sum
            # if val is None:
            # val = 0
            # response += (d.quantity_sold - val)
    return response


def repay_loan(loan_payment_set=None):
    response = 0

    for lp in loan_payment_set:

        if lp.quantity == 0:
            response += lp.price

    return response


def return_loan(loan_payment_set=None):
    response = 0

    for lp in loan_payment_set:
        response += lp.quantity

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
        if lp.price > 0:
            transaction_payment_set = lp.transactionpayment_set.all()
            for t in transaction_payment_set:
                if t.type == 'F':
                    response = response + t.number_of_vouchers
    return response


def total_return_loan(order_detail_set=None):
    response = 0
    for d in order_detail_set:
        loan_payment_set = d.loanpayment_set.all()
        response = response + return_loan(loan_payment_set)
    return response


def total_remaining_repay_loan_ball(order_detail_set=None):
    response = 0
    for d in order_detail_set:
        if d.unit.name == 'B':
            multiply = d.quantity_sold * d.price_unit
            loan_payment_set = d.loanpayment_set.all()
            response = response + (multiply - repay_loan_ball(loan_payment_set))
    return response


def repay_loan_ball(loan_payment_set=None):
    response = 0
    for lp in loan_payment_set:
        response = response + (lp.quantity * (lp.price + lp.discount))
    return response


def total_ball_changes(order_detail_set=None):
    response = 0
    for d in order_detail_set:
        ballchange_set = d.ballchange_set.all()
        response = response + ball_changes(ballchange_set)
    return response


def ball_changes(ballchange_set=None):
    response = 0
    for ball in ballchange_set:
        response = response + ball.quantity
    return response


def total_cash_flow_spending(cashflow_set=None):
    response = 0
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


# queries
def get_orders_for_status_account(subsidiary_obj=None):
    client_set = Client.objects.filter(
        order__isnull=False, order__subsidiary=subsidiary_obj, order__type__in=['V', 'R']
    ).values('id', 'names').annotate(max=Max('id'))

    order_set = Order.objects.filter(
        subsidiary=subsidiary_obj, type__in=['V', 'R'],
        client__id__in=[c['id'] for c in client_set]
    ).select_related('client').annotate(
        total_remaining_return_loan=Coalesce(
            Subquery(
                OrderDetail.objects.filter(
                    order_id=OuterRef('id'), product_id__in=[1, 12, 2, 3], unit__name='B'
                ).annotate(
                    return_loan_sum=Coalesce(
                        Subquery(
                            LoanPayment.objects.filter(order_detail=OuterRef('id')).values(
                                'order_detail_id').annotate(
                                return_loan=Coalesce(Sum('quantity'), Value(0))).values('return_loan')[:1],
                            output_field=models.DecimalField()
                        ), Value(0)
                    )
                ).values('order_id').annotate(
                    amount=Sum(F('quantity_sold') - F('return_loan_sum'))
                ).values('amount')[:1]
            )
            , Value(0)
        )
    ).annotate(
        total_remaining_repay_loan=Coalesce(
            Subquery(
                OrderDetail.objects.filter(
                    order_id=OuterRef('id'), unit__name__in=['G', 'GBC']
                ).annotate(
                    repay_loan_sum=Coalesce(
                        Subquery(
                            LoanPayment.objects.filter(order_detail=OuterRef('id'), quantity=0).values(
                                'order_detail_id').annotate(
                                repay_loan=Coalesce(Sum('price'), Value(0))).values('repay_loan')[:1],
                            output_field=models.DecimalField()
                        ), Value(0)
                    )
                ).values('order_id').annotate(
                    amount2=Sum(F('quantity_sold') * F('price_unit') - F('repay_loan_sum'))
                ).values('amount2')[:1]
            )
            , Value(0)
        )
    ).values('id', 'client__id', 'client__names', 'total_remaining_return_loan', 'total_remaining_repay_loan')

    summary_sum_total_remaining_repay_loan = 0
    summary_sum_total_remaining_return_loan = 0
    client_dict = {}
    for o in order_set:

        key = o['client__id']

        rpl = o['total_remaining_repay_loan']
        rtl = o['total_remaining_return_loan']

        if key in client_dict:
            client = client_dict[key]

            old_rpl = client.get('sum_total_remaining_repay_loan')
            old_rtl = client.get('sum_total_remaining_return_loan')

            client_dict[key]['sum_total_remaining_repay_loan'] = old_rpl + rpl
            client_dict[key]['sum_total_remaining_return_loan'] = old_rtl + rtl

        else:
            client_dict[key] = {
                'client_id': o['client__id'],
                'client_names': o['client__names'],
                'sum_total_remaining_repay_loan': rpl,
                'sum_total_remaining_return_loan': rtl,
            }

        summary_sum_total_remaining_repay_loan += rpl
        summary_sum_total_remaining_return_loan += rtl
        d = dict()
        d['client_dict'] = client_dict
        d['summary_sum_total_remaining_repay_loan'] = summary_sum_total_remaining_repay_loan
        d['summary_sum_total_remaining_return_loan'] = summary_sum_total_remaining_return_loan
    return d
