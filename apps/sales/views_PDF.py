import decimal

import reportlab
from django.http import HttpResponse
from reportlab.graphics.barcode import qr
from reportlab.lib.colors import black, white, gray, red, green, blue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Spacer, tables, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4, A5, C7
from reportlab.lib.units import mm, cm, inch
from reportlab.platypus import Table, Flowable
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import Canvas
# from reportlab.rl_config import defaultPageSize
from functools import partial
from reportlab.lib.colors import PCMYKColor, PCMYKColorSep, Color, black, blue, red, pink, green
from .models import Product, Client, Order, OrderDetail, SubsidiaryStore, ProductStore, Kardex, LoanPayment, OrderBill, \
    TransactionPayment
from django.contrib.auth.models import User
from apps.hrm.views import get_subsidiary_by_user
from .number_to_letters import numero_a_moneda
from .views import get_dict_orders, total_remaining_repay_loan, total_remaining_return_loan, \
    repay_loan, return_loan
from datetime import datetime
from .format_dates import utc_to_local
from django.db.models import Sum, Max, Min, Sum, Q, Value as V, F, Prefetch
import io
import pdfkit
from apps.sales.funtions import get_orders_for_status_account

# Register Fonts
# PAGE_HEIGHT = defaultPageSize[1]
# PAGE_WIDTH = defaultPageSize[0]
from ..hrm.models import Subsidiary

styles = getSampleStyleSheet()
styleN = styles['Normal']
styleH = styles['Heading1']

styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='CenterTitle2', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=12))
styles.add(ParagraphStyle(name='Center_Regular', alignment=TA_CENTER, leading=8, fontName='Ticketing', fontSize=10))
styles.add(
    ParagraphStyle(name='Justify_Newgot_title', alignment=TA_JUSTIFY, leading=14, fontName='Newgot', fontSize=14))
styles.add(
    ParagraphStyle(name='Center_Newgot_title', alignment=TA_CENTER, leading=15, fontName='Newgot', fontSize=15))
styles.add(ParagraphStyle(name='Left_Square', alignment=TA_LEFT, leading=10, fontName='Square', fontSize=10))
styles.add(ParagraphStyle(name='Justify_Square', alignment=TA_JUSTIFY, leading=10, fontName='Square', fontSize=10))
styles.add(ParagraphStyle(name='Center_Newgot_1', alignment=TA_CENTER, leading=11, fontName='Newgot', fontSize=9))
styles.add(ParagraphStyle(name='Center-text', alignment=TA_CENTER, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Justify_Newgot', alignment=TA_JUSTIFY, leading=10, fontName='Newgot', fontSize=10))
styles.add(ParagraphStyle(name='Right_Newgot', alignment=TA_RIGHT, leading=12, fontName='Newgot', fontSize=12))
styles.add(ParagraphStyle(name='Center_Newgot', alignment=TA_CENTER, leading=11, fontName='Newgot', fontSize=11))
styles.add(ParagraphStyle(name='Left-text', alignment=TA_LEFT, leading=8, fontName='Square', fontSize=8))

pdfmetrics.registerFont(TTFont('Ticketing', 'ticketing.regular.ttf'))
pdfmetrics.registerFont(TTFont('Square', 'square-721-condensed-bt.ttf'))
pdfmetrics.registerFont(TTFont('Square-Bold', 'sqr721bc.ttf'))


def product_print(self, pk=None):
    response = HttpResponse(content_type='application/pdf')
    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=letter,
                            rightMargin=40,
                            leftMargin=40,
                            topMargin=60,
                            bottomMargin=18,
                            )
    products = []
    styles = getSampleStyleSheet()
    header = Paragraph("Listado de Productos", styles['Heading1'])
    products.append(header)
    headings = ('Id', 'Descrición', 'Activo', 'Creación')
    if not pk:
        all_products = [(p.id, p.name, p.is_enabled, p.code)
                        for p in Product.objects.all().order_by('pk')]
    else:
        all_products = [(p.id, p.name, p.is_enabled, p.code)
                        for p in Product.objects.filter(id=pk)]
    t = Table([headings] + all_products)
    t.setStyle(TableStyle(
        [
            ('GRID', (0, 0), (3, -1), 1, colors.dodgerblue),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.darkblue),
            ('BACKGROUND', (0, 0), (-1, 0), colors.dodgerblue)
        ]
    ))

    products.append(t)
    doc.build(products)
    response.write(buff.getvalue())
    buff.close()
    return response


def account_order_list_pdf(request, pk):
    if request.method == 'GET':
        client_obj = Client.objects.get(pk=int(pk))

        order_set = Order.objects.filter(client=client_obj, type='R')

        if pk != '':
            html = get_dict_orders(order_set, client_obj=client_obj, is_pdf=True, )
            options = {
                'page-size': 'A3',
                'orientation': 'Landscape',
                'encoding': "UTF-8",
            }
            path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
            config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

            pdf = pdfkit.from_string(html, False, options, configuration=config)
            response = HttpResponse(pdf, content_type='application/pdf')
            # response['Content-Disposition'] = 'attachment;filename="kardex_pdf.pdf"'
            return response


Title = "ESTADO DE CUENTA DE "
pageinfo = "VICTORIA JUAN GAS S.A.C."
register_date_now = utc_to_local(datetime.now())
date_now = register_date_now.strftime("%d/%m/%y %H:%M")


# A4 CM 21.0 x 29.7


def create_pdf(header=None, body=None, footer=None, title=None, cols=None):
    _a4 = (8.3 * inch, 11.7 * inch)
    ml = 0.75 * inch
    mr = 0.75 * inch
    ms = 0.75 * inch
    mi = 1.0 * inch
    _bts = 8.3 * inch - ml - mr
    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=_a4,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title=title
                            )
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="{}.pdf"'.format(title)
    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Ticketing'),  # all columns
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), 2),  # all columns
        ('LEFTPADDING', (0, 0), (-1, -1), 2),  # all columns
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

    ]

    col_widths = cols * [_bts / cols]

    _date = 'FECHA DE INPRESIÓN: ' + datetime.now().strftime("%d/%m/%Y")

    ana_detail = Table(header + body, colWidths=col_widths)
    ana_detail.setStyle(TableStyle(style_table))

    _dictionary = [
        Paragraph(_date, styles["Right"]),
        Paragraph('001', styles["Right"]),
        Paragraph(title, styles["CenterTitle2"]),
        Spacer(1, 20),
        ana_detail,
        Spacer(1, 20),
        footer
    ]

    doc.build(_dictionary)
    response.write(buff.getvalue())
    buff.close()
    return response


def pdf_get_orders_for_status_account(request):
    header = [(
        'N°'.upper(),
        'Cliente'.upper(),
        'Pago Faltante (Efectivo)'.upper(),
        'Cantidad Faltante (Fierros)'.upper(),
    )]

    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    d = get_orders_for_status_account(subsidiary_obj=subsidiary_obj)
    summary_sum_total_remaining_repay_loan = d['summary_sum_total_remaining_repay_loan']
    summary_sum_total_remaining_return_loan = d['summary_sum_total_remaining_return_loan']
    client_dict = d['client_dict']
    body = []
    for k, c in client_dict.items():
        body.append(
            (
                c['client_id'],
                c['client_names'],
                round(c['sum_total_remaining_repay_loan'], 2),
                round(c['sum_total_remaining_return_loan']),
            )
        )
    title = 'ESTADO DE CUENTAS DE {}'.format(str(subsidiary_obj.name).upper())

    labeled = [

        ['TOTAL PAGO FALTANTE: ', str(round(summary_sum_total_remaining_repay_loan, 2)), '', ''],
        ['TOTAL CANTIDAD FALTANTE:', str(round(summary_sum_total_remaining_return_loan, 0)), '', ''],

    ]
    footer = Table(labeled)

    return create_pdf(header=header, body=body, footer=footer, title=title, cols=4)


logo = "static/assets/avatar/logo-anderquin-original.png"


def print_quotation(request, pk=None, t=None):
    _a4 = (8.3 * inch, 11.7 * inch)
    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch

    _bts = 8.3 * inch - 0.25 * inch - 0.25 * inch

    order_obj = Order.objects.get(id=pk)

    I = Image(logo)
    I.drawHeight = 3.60 * inch / 2.9
    I.drawWidth = 3.9 * inch / 2.9

    subsidiary_obj = Subsidiary.objects.get(id=order_obj.subsidiary.id)

    telephone_subsidiary = '-'
    email_subsidiary = 'correo@anderquim.com'
    address_subsidiary = subsidiary_obj.address
    # employee_obj = Employee.objects.filter(worker__user=order_obj.user).last()
    # if employee_obj is not None:
    #     telephone_subsidiary = employee_obj.telephone_number
    #     email_subsidiary = employee_obj.email
    # else:
    #     telephone_subsidiary = '999973999'
    #     email_subsidiary = 'roldem@roldem.com'

    tbl1_col__2 = [
        [Paragraph('INDUSTRIAS ANDERQUIN', styles["Justify_Newgot_title"])],
        [Paragraph('JR. CARABAYA NRO. 443', styles['Normal'])],
        ['Celular: ' + str('951 622 449')],
        # ['Teléfono Fijo: ' + str('-')],
        ['Correo: ' + str(email_subsidiary)],
    ]
    col_2 = Table(tbl1_col__2)
    style_table_col_2 = [
        # ('GRID', (0, 3), (0, 3), 0.9, colors.red),
        ('TEXTCOLOR', (0, 2), (0, 3), colors.blue),
    ]
    col_2.setStyle(TableStyle(style_table_col_2))

    tbl1_col__3 = [
        [Paragraph('RUC: 20604193053 ', styles["Center_Newgot_title"])],
        [Paragraph('COTIZACIÓN Nº', styles["Center_Newgot_title"])],
        [Paragraph(order_obj.subsidiary.serial + '-' + str(str(order_obj.correlative).zfill(6)),
                   styles["Center_Newgot_title"])],
    ]
    col_3 = Table(tbl1_col__3, colWidths=[_bts * 28 / 100])
    style_table_col_3 = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.red),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    col_3.setStyle(TableStyle(style_table_col_3))

    _tbl_header = [
        [I, col_2, col_3],
    ]
    header_page = Table(_tbl_header, colWidths=[_bts * 20 / 100, _bts * 50 / 100, _bts * 30 / 100])
    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    header_page.setStyle(TableStyle(style_table_header))
    # ---------------------------------Datos Cliente----------------------------#
    telephone = '-'
    email = '-'
    client_id = order_obj.client.id
    client_obj = Client.objects.get(id=client_id)
    type_client = client_obj.clienttype_set.first().document_type.id
    info_document = client_obj.clienttype_set.first().document_number

    if client_obj.phone is not None:
        telephone = client_obj.phone
    if client_obj.email is not None:
        email = client_obj.email
    info_address = '-'
    payment = '-'
    description = '-'

    if order_obj.way_to_pay_type:
        payment = order_obj.get_way_to_pay_type_display()
    else:
        payment = 'Efectivo'

    info_address = client_obj.clientaddress_set.first().address.upper()

    tbl2_col1 = [
        ['Señor(es) :', Paragraph(str(client_obj.names), styles['Left_Square'])],
        ['RUC/DNI :', Paragraph(str(info_document), styles['Left_Square'])],
        ['Dirección :', Paragraph(str(info_address), styles['Left_Square'])],
        ['Teléfono :', Paragraph(str(telephone), styles['Left_Square'])],
        ['Correo :', Paragraph(str(email), styles['Left_Square'])],
        # ['Forma Pago:', Paragraph(str(description), styles['Left_Square'])],
        ['Lugar de Entrega  : ', Paragraph(str(order_obj.place_delivery.upper()), styles['Left_Square'])],
    ]
    tbl2_col_1 = Table(tbl2_col1, colWidths=[_bts * 20 / 100, _bts * 50 / 100])
    style_table2_col1 = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'LEFT'),  # first column
        ('LEFTPADDING', (0, 0), (0, -1), 13),  # first column
    ]
    tbl2_col_1.setStyle(TableStyle(style_table2_col1))

    tbl2_col2 = [
        ['Fecha Emisión: ', Paragraph(order_obj.create_at.strftime("%d-%m-%Y"), styles['Left_Square'])],
        ['Fecha Vencimiento: ', Paragraph(order_obj.validity_date.strftime("%d-%m-%Y"), styles['Left_Square'])],
        # ['Vendedor: ', Paragraph(order_obj.user.username.upper(), styles['Left_Square'])],
        # ['Moneda: ', Paragraph(order_obj.get_coin_display(), styles['Left_Square'])],
        ['Cond. Venta: ', Paragraph(str(payment.upper()), styles['Left_Square'])],
        ['Plazo: ', Paragraph(str(order_obj.date_completion) + ' dia(s)', styles['Left_Square'])],
        [],
        # ['Tipo: ', Paragraph(str(order_obj.get_type_quotation_display()), styles['Left_Square'])],
        # ['Nombre: ', Paragraph(str(order_obj.type_name_quotation.upper()), styles['Left_Square'])]
    ]
    tbl2_col_2 = Table(tbl2_col2, colWidths=[_bts * 18 / 100, _bts * 14 / 100])
    tbl2_col_2.setStyle(TableStyle(style_table2_col1))

    _tbl_header2 = [
        [tbl2_col_1, tbl2_col_2],
    ]
    header2_page = Table(_tbl_header2, colWidths=[_bts * 66 / 100, _bts * 34 / 100])
    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    header2_page.setStyle(TableStyle(style_table_header))
    # ------------ENCABEZADO DEL DETALLE-------------------#
    style_table_header_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Newgot'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 1, colors.fidblue),  # all columns
        ('BACKGROUND', (0, 0), (-1, -1), colors.fidblue),  # all columns
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),  # all columns
        ('RIGHTPADDING', (1, 0), (1, -1), 10),  # second column
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # all column
        ('ALIGNMENT', (2, 0), (2, -1), 'LEFT'),  # second column
    ]
    width_table = [_bts * 5 / 100, _bts * 11 / 100, _bts * 44 / 100, _bts * 10 / 100, _bts * 9 / 100,
                   _bts * 8 / 100, _bts * 13 / 100]
    header_detail = Table([('Item', 'Código', 'Descripción', 'Cantidad', 'U.M.', 'P. Unit', 'Total')],
                          colWidths=width_table)
    header_detail.setStyle(TableStyle(style_table_header_detail))
    line = '-------------------------------------------------------------------------------------------------------------'
    # -------------------DETAIL---------------------#
    style_table_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.fidblue),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGNMENT', (6, 0), (6, -1), 'RIGHT'),  # seven column
        ('ALIGNMENT', (5, 0), (5, -1), 'RIGHT'),  # six column
        ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
        ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),  # second column
        # ('ALIGNMENT', (3, 0), (3, -1), 'CENTER'),  # four column
        # ('ALIGNMENT', (4, 0), (4, -1), 'CENTER'),  # five column
        ('ALIGNMENT', (3, 0), (3, -1), 'CENTER'),  # three column
        ('ALIGNMENT', (4, 0), (4, -1), 'CENTER'),  # three column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # first column
        ('RIGHTPADDING', (3, 0), (3, -1), 10),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),  # all columns
        # ('BACKGROUND', (4, 0), (4, -1),  colors.green),  # four column
    ]

    detail_rows = []
    count = 0
    sub_total = 0
    _total = 0

    # for d in order_obj.orderdetail_set.all():
    #     P0 = Paragraph(d.commentary.upper(), styles["Justify"])
    #     _rows.append((P0, str(decimal.Decimal(round(d.quantity_sold, 3))), d.unit.name, str(d.price_unit),
    #                   str(decimal.Decimal(round(d.quantity_sold * d.price_unit, 2)))))
    #     base_total = d.quantity_sold * d.price_unit
    #     base_amount = base_total / decimal.Decimal(1.1800)
    #     igv = base_total - base_amount
    #     sub_total = sub_total + base_amount
    #     total = total + base_total
    #     igv_total = igv_total + igv

    details_list = order_obj.orderdetail_set.all()
    total = 0
    for detail in details_list.order_by('id'):
        _code = '-'
        if detail.product.code:
            _code = str(detail.product.code.zfill(6))

        count = count + 1
        _product_plus_brand = Paragraph(str(detail.commentary.upper()), styles["Justify_Square"])
        # _product_name = Paragraph(str(detail.product.name), styles["Justify_Square"])
        _quantity = str(decimal.Decimal(round(detail.quantity_sold, 2)))
        _unit = str(detail.unit.name)
        _price_unit = round(decimal.Decimal(detail.price_unit) * decimal.Decimal(1.18), 2)
        _total = round(detail.quantity_sold * decimal.Decimal(detail.price_unit), 2)

        detail_rows.append((count, _code, _product_plus_brand, _quantity, _unit, detail.price_unit, '{:,}'.format(_total)))
        total += _total

    detail_body = Table(detail_rows,
                        colWidths=[_bts * 5 / 100, _bts * 11 / 100, _bts * 44 / 100, _bts * 10 / 100, _bts * 9 / 100,
                                   _bts * 8 / 100, _bts * 13 / 100])
    detail_body.setStyle(TableStyle(style_table_detail))
    # difference = sub_total * decimal.Decimal(0.18)
    _text = 'DESCUENTO'
    _discount = 0
    total_with_igv = round(total * decimal.Decimal(1.18), 2)
    # if order_obj.type_discount == 'E':
    #     _text = 'DESCUENTO:'
    #     _discount = order_obj.discount
    # elif order_obj.type_discount == 'P':
    #     _text = 'DESCUENTO(' + str(order_obj.discount) + '%)'
    #     _discount = (sub_total * order_obj.discount) / 100
    # difference = (sub_total - _discount) * decimal.Decimal(0.18)
    valor_venta = decimal.Decimal(total) / decimal.Decimal(1.18)
    igv = decimal.Decimal(total) - valor_venta
    # ---------------------Totales-----------------------#
    table_bank = [
        [Paragraph('BANCO', styles['Center_Newgot_1']),
         Paragraph('MONEDA', styles['Center_Newgot_1']),
         Paragraph('CODIGO DE CUENTA CORRIENTE', styles['Center_Newgot_1']),
         Paragraph('CODIGO DE CUENTA INTERBANCARIO', styles['Center_Newgot_1'])],

        [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
         Paragraph('SOLES', styles['Center-text']), Paragraph('405-2663807-0-48', styles['Center-text']),
         Paragraph('002-405-002663807048-97', styles['Center-text'])],

        # [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
        #  Paragraph('SOLES', styles['Center-text']), Paragraph('215-9844079-0-56', styles['Center-text']),
        #  Paragraph('002-215-009844079056-20', styles['Center-text'])],
        #
        # [Paragraph('CUENTA BBVA', styles['Center_Newgot_1']),
        #  Paragraph('SOLES', styles['Left-text']), Paragraph('0011 0418 0100018341 16', styles['Left-text']),
        #  Paragraph('011 418 000100018341 16', styles['Left-text'])],
        #
        # [Paragraph('BBVA', styles['Center_Newgot_1']),
        #  Paragraph('DOLARES', styles['Left-text']), Paragraph('0011 0418 0100018368 19', styles['Left-text']),
        #  Paragraph('011 418 000100018368 19', styles['Left-text'])],
    ]
    t_bank = Table(table_bank, colWidths=[_bts * 7 / 100, _bts * 7 / 100, _bts * 24 / 100, _bts * 24 / 100])
    style_bank = [
        # ('SPAN', (0, 1), (0, 2)),
        # ('SPAN', (0, 3), (0, 4)),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        # ('BACKGROUND', (2, 1), (2, 1), colors.blue),  # four column
    ]
    t_bank.setStyle(TableStyle(style_bank))

    total_col1 = [
        [Paragraph(
            'OBSERVACION: ' + order_obj.observation,
            styles["Justify_Newgot"])],
        [Paragraph('SON: ' + numero_a_moneda(round(decimal.Decimal(total), 2), ),
                   styles["Justify_Newgot"])],
        [t_bank],
    ]
    total_col_1 = Table(total_col1, colWidths=[_bts * 63 / 100])
    style_table_col1 = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),
    ]
    total_col_1.setStyle(TableStyle(style_table_col1))
    money = 'S/'
    # if order_obj.coin == 'S':
    #     money = 'S/.'
    # elif order_obj.coin == 'D':
    #     money = '$'

    total_col2 = [
        [Paragraph('VALOR DE VENTA:', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str('{:,}'.format(round(valor_venta, 2))), styles["Right_Newgot"])],
        # [Paragraph(_text, styles["Justify_Newgot"]),
        #  Paragraph(money + ' ' + str(round(_discount, 3)), styles["Right_Newgot"])],
        # [Paragraph('OPERACION GRAVADAS', styles["Justify_Newgot"]),
        #  Paragraph(money + ' ' + str(round(sub_total - _discount, 3)), styles["Right_Newgot"])],
        [Paragraph('I.G.V(18%):', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str('{:,}'.format(round(igv, 2))), styles["Right_Newgot"])],
        [Paragraph('IMPORTE TOTAL:', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str('{:,}'.format(round(valor_venta + igv, 2))), styles["Right_Newgot"])],
    ]
    total_col_2 = Table(total_col2, colWidths=[_bts * 14 / 100, _bts * 19 / 100])

    style_table_col2 = [
        # ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    total_col_2.setStyle(TableStyle(style_table_col2))

    total_ = [
        [total_col_1, total_col_2],
    ]
    total_page = Table(total_, colWidths=[_bts * 65 / 100, _bts * 35 / 100])
    style_table_page = [
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),  # three column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # first column
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.red),
    ]
    total_page.setStyle(TableStyle(style_table_page))

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=(8.3 * inch, 11.7 * inch),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='COTIZACION ' + str(str(order_obj.correlative).zfill(6))
                            )
    dictionary = []
    dictionary.append(header_page)
    dictionary.append(OutputPrintQuotation(count_row=count))
    dictionary.append(header2_page)
    dictionary.append(Spacer(1, 16))
    dictionary.append(header_detail)
    # dictionary.append(Paragraph(line, styles["Center_Newgot_title"]))
    dictionary.append(detail_body)
    dictionary.append(Spacer(1, 15))
    dictionary.append(total_page)
    dictionary.append(Paragraph(line, styles["Center_Newgot_title"]))
    dictionary.append(Paragraph(
        'Cumplimos con las especificaciones tecnicas del requerimiento para lograr un producto que esté a entera satisfacción de nuestros clientes.',
        styles["Center_Newgot"]))
    # dictionary.append(Paragraph('www.roldemperu.com', styles["Center_Newgot"]))
    response = HttpResponse(content_type='application/pdf')
    doc.build(dictionary)
    response.write(buff.getvalue())
    buff.close()
    return response


def print_order_bill(request, pk=None):
    _a4 = (8.3 * inch, 11.7 * inch)
    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch

    _bts = 8.3 * inch - 0.25 * inch - 0.25 * inch

    # service_obj = GuideService.objects.get(id=pk)
    order_obj = Order.objects.get(id=pk)
    subsidiary_obj = Subsidiary.objects.get(id=order_obj.subsidiary.id)
    I = Image(logo)
    I.drawHeight = 3.60 * inch / 2.9
    I.drawWidth = 3.9 * inch / 2.9

    email_subsidiary = 'correo@anderquim.com'

    tbl1_col__2 = [
        [Paragraph('INDUSTRIAS ANDERQUIN', styles["Justify_Newgot_title"])],
        [Paragraph('JR. CARABAYA NRO. 443', styles['Normal'])],
        ['Celular: ' + str('951 622 449')],
        ['Correo: ' + str(email_subsidiary)],
    ]
    col_2 = Table(tbl1_col__2)
    style_table_col_2 = [
        # ('GRID', (0, 3), (0, 3), 0.9, colors.red),
        ('TEXTCOLOR', (0, 3), (0, 3), colors.blue),
    ]
    col_2.setStyle(TableStyle(style_table_col_2))
    order_bill_set = OrderBill.objects.filter(order=order_obj)

    order_bill_obj = None
    type_bill = order_obj.get_type_document_display()
    serial = order_obj.serial
    correlative = order_obj.correlative
    datatable = 'https://4soluciones.pse.pe/20539633075'
    if order_bill_set.exists():
        order_bill_obj = order_bill_set.last()
        datatable = order_bill_obj.code_qr
        type_bill = order_bill_obj.get_type_display().upper()
        serial = order_bill_obj.serial
        correlative = order_bill_obj.n_receipt
    tbl1_col__3 = [
        [Paragraph('RUC 20539633075', styles["Center_Newgot_title"])],
        [Paragraph(str(type_bill) + ' ELECTRÓNICA', styles["Center_Newgot_title"])],
        [Paragraph(serial + '-' + str(str(correlative).zfill(8)),
                   styles["Center_Newgot_title"])],
    ]
    col_3 = Table(tbl1_col__3, colWidths=[_bts * 28 / 100])
    style_table_col_3 = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.red),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    col_3.setStyle(TableStyle(style_table_col_3))

    _tbl_header = [
        [I, col_2, col_3],
    ]
    header_page = Table(_tbl_header, colWidths=[_bts * 20 / 100, _bts * 50 / 100, _bts * 30 / 100])
    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    header_page.setStyle(TableStyle(style_table_header))
    # ---------------------------------Datos Cliente----------------------------#
    client_id = order_obj.client.id
    client_obj = Client.objects.get(id=client_id)
    type_client = client_obj.clienttype_set.first().document_type.id
    info_document = client_obj.clienttype_set.first().document_number
    telephone = client_obj.phone
    if telephone is None:
        telephone = '-'
    email = client_obj.email
    if email is None:
        email = '-'
    info_address = ''
    loan_payment_get = LoanPayment.objects.filter(order=order_obj).last()
    transaction_payment_get = TransactionPayment.objects.filter(loan_payment=loan_payment_get).last()
    payment = transaction_payment_get.get_type_display()

    if type_client == '06':
        info_address = client_obj.clientaddress_set.last().address

    pay_condition = '-'
    if order_obj.pay_condition:
        pay_condition = order_obj.pay_condition

    tbl2_col1 = [
        ['Señor(es) :', Paragraph(str(client_obj.names), styles['Left_Square'])],
        ['Ruc/dni    :', Paragraph(str(info_document), styles['Left_Square'])],
        ['Direccion :', Paragraph(str(info_address.upper()), styles['Left_Square'])],
        ['Telefono  :', Paragraph(str(telephone), styles['Left_Square'])],
        ['Correo     :', Paragraph(str(email), styles['Left_Square'])],
        ['Cond. Pago : ', Paragraph(str(pay_condition), styles['Left_Square'])],
    ]
    tbl2_col_1 = Table(tbl2_col1, colWidths=[_bts * 15 / 100, _bts * 54 / 100])
    style_table2_col1 = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'LEFT'),  # first column
        ('LEFTPADDING', (0, 0), (0, -1), 13),  # first column
    ]
    tbl2_col_1.setStyle(TableStyle(style_table2_col1))

    tbl2_col2 = [
        ['Fecha Emision: ', Paragraph(order_obj.create_at.strftime("%d-%m-%Y"), styles['Left_Square'])],
        ['Vendedor: ', Paragraph(order_obj.user.username.upper(), styles['Left_Square'])],
        # ['Moneda: ', 'coin'],
        ['Cond. Venta: ', Paragraph(str(payment.upper()), styles['Left_Square'])],
        # ['Nº Compra Cliente: ', Paragraph(str(nro_purchase_client), styles['Left_Square'])]
    ]
    tbl2_col_2 = Table(tbl2_col2, colWidths=[_bts * 18 / 100, _bts * 14 / 100])

    _tbl_header2 = [
        [tbl2_col_1, tbl2_col_2],
    ]
    header2_page = Table(_tbl_header2, colWidths=[_bts * 66 / 100, _bts * 34 / 100])
    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
        # ('GRID', (0, 0), (-1, -1), 2, colors.lightgrey),
        # ('GRID', (0, 0), (0, 1), 3.5, colors.red)
    ]
    header2_page.setStyle(TableStyle(style_table_header))
    # ------------ENCABEZADO DEL DETALLE-------------------#
    style_table_header_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Newgot'),  # all columns
        ('GRID', (0, 0), (-1, -1), 1, colors.darkgray),  # all columns
        ('BACKGROUND', (0, 0), (-1, -1), colors.darkgray),  # all columns
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),  # all columns
        ('RIGHTPADDING', (1, 0), (1, -1), 10),  # second column
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # all column
        ('ALIGNMENT', (2, 0), (2, -1), 'LEFT'),  # second column
    ]
    width_table = [_bts * 8 / 100, _bts * 8 / 100, _bts * 12 / 100, _bts * 42 / 100, _bts * 14 / 100, _bts * 16 / 100]
    header_detail = Table([('Item', 'Cantidad', 'Unidad', 'Descripción', 'Precio U.', 'Total')], colWidths=width_table)
    header_detail.setStyle(TableStyle(style_table_header_detail))
    line = '-------------------------------------------------------------------------------------------------------------'
    # -------------------DETAIL---------------------#
    style_table_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.darkgray),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # all column
        ('ALIGNMENT', (2, 0), (2, -1), 'LEFT'),  # three column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # first column
        ('RIGHTPADDING', (3, 0), (3, -1), 10),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),  # all columns
        # ('BACKGROUND', (1, 0), (1, -1),  colors.green),  # four column
    ]
    detail_rows = []
    count = 0
    _total = 0
    for detail in order_obj.orderdetail_set.all():
        count = count + 1
        _product = Paragraph(str(detail.product.name), styles["Justify_Square"])
        # _product_plus_brand = Paragraph(str(detail.commentary.upper()) + ' - ' + str(detail.product.product_brand.name),
        #                                 styles["Justify_Square"])
        detail_rows.append(
            (str(count), str(decimal.Decimal(round(detail.quantity_sold, 2))), str(detail.unit.description),
             _product,
             str(detail.price_unit), str(round(detail.quantity_sold * detail.price_unit, 2))))
        _total = _total + detail.quantity_sold * detail.price_unit
    detail_body = Table(detail_rows,
                        colWidths=[_bts * 8 / 100, _bts * 8 / 100, _bts * 12 / 100, _bts * 42 / 100, _bts * 14 / 100,
                                   _bts * 16 / 100])
    detail_body.setStyle(TableStyle(style_table_detail))
    _text = 'DESCUENTO'
    _discount = decimal.Decimal(0.00)
    valor_venta = decimal.Decimal(_total) / decimal.Decimal(1.18)
    igv = decimal.Decimal(_total) - valor_venta
    # ---------------------Totales-----------------------#
    table_bank = [
        [Paragraph('BANCO', styles['Center_Newgot_1']),
         Paragraph('MONEDA', styles['Center_Newgot_1']),
         Paragraph('CODIGO DE CUENTA CORRIENTE', styles['Center_Newgot_1']),
         Paragraph('CODIGO DE CUENTA INTERBANCARIO', styles['Center_Newgot_1'])],

        [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
         Paragraph('SOLES', styles['Center-text']), Paragraph('405-2663807-0-48', styles['Center-text']),
         Paragraph('002-405-002663807048-97', styles['Center-text'])],

        # [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
        #  Paragraph('SOLES', styles['Center-text']), Paragraph('215-9844079-0-56', styles['Center-text']),
        #  Paragraph('002-215-009844079056-20', styles['Center-text'])],

        # [Paragraph('CUENTA BBVA', styles['Center_Newgot_1']),
        #  Paragraph('SOLES', styles['Left-text']), Paragraph('0011 0418 0100018341 16', styles['Left-text']),
        #  Paragraph('011 418 000100018341 16', styles['Left-text'])],
        #
        # [Paragraph('CUENTA BBVA', styles['Center_Newgot_1']),
        #  Paragraph('SOLES', styles['Left-text']), Paragraph('0011 0418 0100018341 16', styles['Left-text']),
        #  Paragraph('011 418 000100018341 16', styles['Left-text'])],
        #
        # [Paragraph('BBVA', styles['Center_Newgot_1']),
        #  Paragraph('DOLARES', styles['Left-text']), Paragraph('0011 0418 0100018368 19', styles['Left-text']),
        #  Paragraph('011 418 000100018368 19', styles['Left-text'])],
    ]
    t_bank = Table(table_bank, colWidths=[_bts * 7 / 100, _bts * 7 / 100, _bts * 24 / 100, _bts * 24 / 100])
    style_bank = [
        # ('SPAN', (0, 1), (0, 2)),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
    ]
    t_bank.setStyle(TableStyle(style_bank))

    money = 'S/.'
    retention = ""
    serial_guide = ''
    correlative_guide = ''
    if order_obj.contractdetail_set.last():
        guide_obj = order_obj.contractdetail_set.last().guide_set.last()
        serial_guide = guide_obj.serial
        correlative_guide = str(guide_obj.correlative).zfill(5)

    total_col1 = [
        [t_bank],
        [Paragraph('OBSERVACION: ' + order_obj.observation.upper(), styles["Justify_Newgot"])],
        [Paragraph('SON: ' + numero_a_moneda(round(_total, 2), ),
                   styles["Justify_Newgot"])],
        [Paragraph('GUÍA DE REMISIÓN: ' + str(serial_guide) + '-' + str(correlative_guide),
                   styles["Justify_Newgot"])],
        [Paragraph(str(retention),
                   styles["Justify_Newgot"])]
    ]
    total_col_1 = Table(total_col1, colWidths=[_bts * 63 / 100])
    style_table_col1 = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), -5),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),
    ]
    total_col_1.setStyle(TableStyle(style_table_col1))

    total_col2 = [
        [Paragraph('GRAVADA', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(valor_venta, 2)), styles["Right_Newgot"])],
        [Paragraph(_text, styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(_discount, 2)), styles["Right_Newgot"])],
        [Paragraph('I.G.V.(18.00 %)', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(igv, 2)), styles["Right_Newgot"])],
        [Paragraph('TOTAL', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(valor_venta + igv, 2)), styles["Right_Newgot"])],
    ]
    total_col_2 = Table(total_col2, colWidths=[_bts * 19 / 100, _bts * 14 / 100])

    style_table_col2 = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    total_col_2.setStyle(TableStyle(style_table_col2))

    total_ = [
        [total_col_1, total_col_2],
    ]
    total_page = Table(total_, colWidths=[_bts * 65 / 100, _bts * 35 / 100])
    style_table_page = [
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),  # three column
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # first column
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.red),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]
    total_page.setStyle(TableStyle(style_table_page))
    # -----------------

    footer_1 = [
        [Paragraph('Representación impresa de la ' + str(type_bill).upper() + ' ELECTRÓNICA, para ver el documento visita',
                   styles["Left-text"])],
        [Paragraph('https://4soluciones.pse.pe/20539633075', styles["Left-text"])],
        [Paragraph(
            'Emitido mediante un PROVEEDOR Autorizado por la SUNAT mediante Resolución de Intendencia No.034-005-0005315',
            styles["Left-text"])],
        [Paragraph('', styles["Left-text"])],
        [Paragraph('', styles["Left-text"])],
    ]
    f_1 = Table(footer_1, colWidths=[_bts * 80 / 100])

    style_f1 = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    f_1.setStyle(TableStyle(style_f1))

    # my_style_qr = [
    #     # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),   # all columns
    #     ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
    #     ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
    #     ('SPAN', (0, 0), (1, 0)),  # first row
    # ]
    # qr_ = Table([(qr_code('kldkdsjkdssd'), '')], colWidths=[_bts * 99 / 100, _bts * 1 / 100])
    # qr_.setStyle(TableStyle(my_style_qr))

    _footer = [
        [f_1, qr_code(datatable)],
    ]
    total_footer = Table(_footer, colWidths=[_bts * 80 / 100, _bts * 20 / 100])
    style_total_footer = [
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    total_footer.setStyle(TableStyle(style_total_footer))

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=(8.3 * inch, 11.7 * inch),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title=str(serial).upper() + '-' + str(
                                str(correlative).zfill(4))
                            )
    dictionary = []
    dictionary.append(header_page)
    dictionary.append(OutputInvoiceGuide(count_row=count))
    dictionary.append(header2_page)
    dictionary.append(Spacer(1, 16))
    dictionary.append(header_detail)
    # dictionary.append(Paragraph(line, styles["Center_Newgot_title"]))
    dictionary.append(detail_body)
    dictionary.append(Spacer(1, 5))
    dictionary.append(total_page)
    # if cash_flow_set.last().type_payment == 'C':
    #     dictionary.append(credit_list)
    dictionary.append(Spacer(1, 5))
    dictionary.append(total_footer)
    dictionary.append(Paragraph('Gracias por su confianza', styles["Center_Newgot"]))
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="{}.pdf"'.format(str(type_bill) + ' ' + str(serial) + '-' + str(correlative))
    doc.build(dictionary)
    response.write(buff.getvalue())
    buff.close()
    return response


def qr_code(table):
    # generate and rescale QR
    qr_code = qr.QrCodeWidget(table)
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    drawing = Drawing(
        3.5 * cm, 3.5 * cm, transform=[3.5 * cm / width, 0, 0, 3.5 * cm / height, 0, 0])
    drawing.add(qr_code)

    return drawing


class OutputInvoiceGuide(Flowable):
    def __init__(self, width=200, height=3, count_row=None):
        self.width = width
        self.height = height
        self.count_row = count_row

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        canvas = self.canv  # El atributo que permite dibujar en canvas

        canvas.saveState()
        canvas.setLineWidth(1)
        canvas.setFillColor(Color(0, 0, 0, alpha=0.1))
        # canvas.setFont('Newgot', 30)
        # canvas.setFillColorRGB(0.5, 0.5, 0.5)
        # canvas.roundRect(395, 8, 155, 80, 10, stroke=1, fill=0)
        # canvas.roundRect(0, -105, 550, 105, 10, stroke=1, fill=0)
        canvas.roundRect(386, 8, 169, 80, 10, stroke=1, fill=1)
        # canvas.roundRect(-7, -140, 563, 140, 10, stroke=1, fill=0)
        # canvas.roundRect(0, -(d + 110), 550, d, 10, stroke=1, fill=0)
        # canvas.roundRect(left, bottom, width, height, radius, activa borde, activa color fondo)
        canvas.restoreState()


class OutputPrintQuotation(Flowable):
    def __init__(self, width=200, height=3, count_row=None):
        self.width = width
        self.height = height
        self.count_row = count_row

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        canvas = self.canv  # El atributo que permite dibujar en canvas

        canvas.saveState()
        canvas.setLineWidth(2)
        canvas.setFillColor(red)
        row_d = 0
        row_d = self.count_row
        # canvas.setFont('Newgot', 30)
        # canvas.setFillColorRGB(0.5, 0.5, 0.5)
        if row_d == 1:
            d = 50 + row_d * 25
        else:
            d = 30 + row_d * 25

        # canvas.roundRect(395, 8, 155, 80, 10, stroke=1, fill=0)
        # canvas.roundRect(0, -105, 550, 105, 10, stroke=1, fill=0)
        canvas.roundRect(386, 8, 169, 80, 10, stroke=1, fill=0)
        canvas.roundRect(-7, -120, 563, 120, 10, stroke=1, fill=0)
        # canvas.roundRect(0, -(d + 110), 550, d, 10, stroke=1, fill=0)
        canvas.restoreState()