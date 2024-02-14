import decimal
import os

import reportlab
import io
from datetime import datetime, timedelta, date

import requests
from dateutil.relativedelta import relativedelta
from django.http import HttpResponse
from reportlab.lib.colors import Color, black, white, HexColor
from reportlab.lib.pagesizes import landscape, A5, portrait, A6, A4, letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Spacer, Image, Flowable
from reportlab.platypus import Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode import qr
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.rl_settings import defaultPageSize
# from reportlab.platypus.tables import ROUNDEDCORNERS


from anderquin import settings
from .models import BillPurchase
from ..hrm.models import Worker, Subsidiary
from ..buys.models import Purchase, PurchaseDetail, EntityReference, MoneyChange, AddressEntityReference, Bill, BillDetail
from ..sales.models import Supplier, ProductSupplier, ProductDetail, Client
from ..sales.number_to_letters import numero_a_moneda

PAGE_HEIGHT = defaultPageSize[1]
PAGE_WIDTH = defaultPageSize[0]

COLOR_PDF = colors.Color(red=(152.0 / 255), green=(29.0 / 255), blue=(31.0 / 255))
COLOR_BLUE = colors.Color(red=(27.0 / 255), green=(140.0 / 255), blue=(66.0 / 255))
COLOR_BLUE = colors.Color(red=(133.0 / 255), green=(180.0 / 255), blue=(242.0 / 255))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, leading=30, fontName='Square', fontSize=25))
styles.add(ParagraphStyle(name='JustifyTitle', alignment=TA_CENTER, leading=30, fontName='Square-Bold', fontSize=25))
styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='JustifySquare', alignment=TA_JUSTIFY, leading=12, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='LeftSquare', alignment=TA_LEFT, leading=12, fontName='Square', fontSize=13))
styles.add(ParagraphStyle(name='LeftSquareSmall', alignment=TA_LEFT, leading=9, fontName='Square', fontSize=10))
styles.add(ParagraphStyle(name='LeftSquareSmall2', alignment=TA_LEFT, leading=9, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Justify-Dotcirful', alignment=TA_JUSTIFY, leading=12, fontName='Dotcirful-Regular',
                          fontSize=10))
styles.add(
    ParagraphStyle(name='Justify-Dotcirful-table', alignment=TA_JUSTIFY, leading=12, fontName='Dotcirful-Regular',
                   fontSize=7))
styles.add(ParagraphStyle(name='Justify_Bold', alignment=TA_JUSTIFY, leading=8, fontName='Square-Bold', fontSize=8))

styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, leading=50, fontName='Square-Bold', fontSize=35,
                          textColor=colors.black))
styles.add(ParagraphStyle(name='Center-fecha', alignment=TA_CENTER, leading=10, fontName='Square-Bold', fontSize=10,
                          textColor=colors.black))
styles.add(ParagraphStyle(name='Center-datos', alignment=TA_CENTER, leading=10, fontName='Square', fontSize=10,
                          textColor=colors.black))
styles.add(ParagraphStyle(name='Center-arequipa', alignment=TA_CENTER, leading=19, fontName='Square-Bold', fontSize=10,
                          textColor=COLOR_PDF))
# styles.add(ParagraphStyle(name='Center-titulo', alignment=TA_CENTER, leading=20, fontName='Square-Bold', fontSize=20,
#                          textColor=colors.steelblue))
styles.add(ParagraphStyle(name='Center-titulo', alignment=TA_CENTER, leading=40, fontName='Square-Bold', fontSize=40,
                          textColor=colors.black))
styles.add(ParagraphStyle(name='Center-recibo', alignment=TA_CENTER, leading=20, fontName='Square-Bold', fontSize=20,
                          textColor=colors.white))
styles.add(ParagraphStyle(name='Center-id', alignment=TA_CENTER, leading=40, fontName='Lucida-Console', fontSize=30,
                          textColor=colors.black))
styles.add(ParagraphStyle(name='Center-ng', alignment=TA_CENTER, leading=10, fontName='Square-Bold', fontSize=10,
                          textColor=colors.white))
styles.add(
    ParagraphStyle(name='Left', alignment=TA_LEFT, leading=30, fontName='Square', fontSize=25, textColor=colors.black))
styles.add(
    ParagraphStyle(name='CenterSquare', alignment=TA_CENTER, leading=30, fontName='Square', fontSize=25, textColor=colors.black))
styles.add(
    ParagraphStyle(name='Left-Simple', alignment=TA_LEFT, leading=15, fontName='Square', fontSize=15,
                   textColor=colors.black))
styles.add(ParagraphStyle(name='Left-name', alignment=TA_LEFT, leading=8, fontName='Square-Bold', fontSize=8,
                          textColor=COLOR_PDF))
styles.add(ParagraphStyle(name='Left-datos', alignment=TA_LEFT, leading=10, fontName='Square-Bold', fontSize=10,
                          textColor=colors.black))

styles.add(ParagraphStyle(name='Center4', alignment=TA_CENTER, leading=12, fontName='Square-Bold',
                          fontSize=14, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='Center5', alignment=TA_LEFT, leading=15, fontName='ticketing.regular',
                          fontSize=12))
styles.add(
    ParagraphStyle(name='Center-Dotcirful', alignment=TA_CENTER, leading=12, fontName='Dotcirful-Regular', fontSize=10))
styles.add(ParagraphStyle(name='CenterTitle', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=8))
styles.add(ParagraphStyle(name='CenterTitle-Dotcirful', alignment=TA_CENTER, leading=12, fontName='Dotcirful-Regular',
                          fontSize=10))
styles.add(ParagraphStyle(name='CenterTitle2', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=12))
styles.add(ParagraphStyle(name='Center_Regular', alignment=TA_CENTER, leading=8, fontName='Ticketing', fontSize=10))
styles.add(ParagraphStyle(name='Center_Bold', alignment=TA_CENTER,
                          leading=8, fontName='Square-Bold', fontSize=12, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='ticketing.regular', alignment=TA_CENTER,
                          leading=8, fontName='ticketing.regular', fontSize=14, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='Center2', alignment=TA_CENTER, leading=8, fontName='Ticketing', fontSize=8))
styles.add(ParagraphStyle(name='Center3', alignment=TA_JUSTIFY, leading=8, fontName='Ticketing', fontSize=6))
styles.add(
    ParagraphStyle(name='Justify_Newgot_title', alignment=TA_JUSTIFY, leading=14, fontName='Newgot', fontSize=14))
styles.add(
    ParagraphStyle(name='Center_Newgot_title', alignment=TA_CENTER, leading=15, fontName='Newgot', fontSize=15))
styles.add(ParagraphStyle(name='Left_Square', alignment=TA_LEFT, leading=10, fontName='Square', fontSize=10))
styles.add(ParagraphStyle(name='Center_Square', alignment=TA_CENTER, leading=10, fontName='Square', fontSize=10))
styles.add(ParagraphStyle(name='Justify_Square', alignment=TA_JUSTIFY, leading=10, fontName='Square', fontSize=9))
styles.add(ParagraphStyle(name='Center_Newgot_1', alignment=TA_CENTER, leading=11, fontName='Newgot', fontSize=9))
styles.add(ParagraphStyle(name='Center-text', alignment=TA_CENTER, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Justify_Newgot', alignment=TA_JUSTIFY, leading=10, fontName='Newgot', fontSize=10))
styles.add(ParagraphStyle(name='Right_Newgot', alignment=TA_RIGHT, leading=12, fontName='Newgot', fontSize=12))
style = styles["Normal"]

reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
pdfmetrics.registerFont(TTFont('Narrow', 'Arial Narrow.ttf'))
pdfmetrics.registerFont(TTFont('Square', 'square-721-condensed-bt.ttf'))
pdfmetrics.registerFont(TTFont('Square-Bold', 'sqr721bc.ttf'))
pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))
pdfmetrics.registerFont(TTFont('Ticketing', 'ticketing.regular.ttf'))
pdfmetrics.registerFont(TTFont('Lucida-Console', 'lucida-console.ttf'))
pdfmetrics.registerFont(TTFont('Square-Dot', 'square_dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Serif-Dot', 'serif_dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Enhanced-Dot-Digital', 'enhanced-dot-digital-7.regular.ttf'))
pdfmetrics.registerFont(TTFont('Merchant-Copy-Wide', 'MerchantCopyWide.ttf'))
pdfmetrics.registerFont(TTFont('Dot-Digital', 'dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Raleway-Dots-Regular', 'RalewayDotsRegular.ttf'))
pdfmetrics.registerFont(TTFont('Ordre-Depart', 'Ordre-de-Depart.ttf'))
pdfmetrics.registerFont(TTFont('Dotcirful-Regular', 'DotcirfulRegular.otf'))
pdfmetrics.registerFont(TTFont('Nationfd', 'Nationfd.ttf'))
pdfmetrics.registerFont(TTFont('Kg-Primary-Dots', 'KgPrimaryDots-Pl0E.ttf'))
pdfmetrics.registerFont(TTFont('Dot-line', 'Dotline-LA7g.ttf'))
pdfmetrics.registerFont(TTFont('Dot-line-Light', 'DotlineLight-XXeo.ttf'))
pdfmetrics.registerFont(TTFont('Jd-Lcd-Rounded', 'JdLcdRoundedRegular-vXwE.ttf'))
pdfmetrics.registerFont(TTFont('ticketing.regular', 'ticketing.regular.ttf'))
pdfmetrics.registerFont(TTFont('allerta_medium', 'allerta_medium.ttf'))
# pdfmetrics.registerFont(TTFont('Romanesque_Serif', 'Romanesque Serif.ttf'))


LOGO = "static/assests/img/logo-anderquin.png"

class Background(Flowable):
    def __init__(self, width=200, height=100, obj=None):
        self.width = width
        self.height = height
        self.obj = obj

    def wrap(self, *args):
        """Provee el tamaño del área de dibujo"""
        return (self.width, self.height)

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.setLineWidth(1)
        # canvas.setFillColor(black)
        canvas.setFillColor(Color(0, 0, 0, alpha=0.4))

        # canvas.drawImage(LOGO, 200, -200, mask='auto', width=150, height=150)
        # canvas.setStrokeGray(0.1)

        # canvas.drawImage(firma, 195, -444, mask='auto', width=150, height=140)
        canvas.setFont('Narrow', 12)
        canvas.setFont('Square', 9)
        canvas.setFillColor(white)
        canvas.restoreState()


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


def print_pdf_bill_finances(request, pk=None):
    _a4 = (8.3 * inch, 11.7 * inch)
    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch

    _bts = 8.3 * inch - 0.25 * inch - 0.25 * inch

    I = Image(LOGO)
    I.drawHeight = 3.60 * inch / 2.9
    I.drawWidth = 3.9 * inch / 2.9

    bill_obj = BillPurchase.objects.get(id=pk)

    tbl1_col__2 = [
        [Paragraph('INDUSTRIAS ANDERQUIN EIRL', styles["Justify_Newgot_title"])],
        [Paragraph('JR. CARABAYA NRO. 443', styles['Normal'])],
        [Paragraph('JULIACA - SAN ROMAN - PUNO', styles['Normal'])],
        ['Telefono: ' + str('999999999')],
        ['Correo: ' + str('email@anderquin.com')],
    ]
    col_2 = Table(tbl1_col__2)
    style_table_col_2 = [
        # ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]
    col_2.setStyle(TableStyle(style_table_col_2))

    tbl1_col__3 = [
        [Paragraph('RUC 20604193053', styles["Center_Newgot_title"])],
        [Paragraph('FACTURA ' + ' ELECTRÓNICA', styles["Center_Newgot_title"])],
        [Paragraph(str(bill_obj.serial.upper()) + '-' + str(bill_obj.correlative), styles["Center_Newgot_title"])],
    ]
    col_3 = Table(tbl1_col__3, colWidths=[_bts * 28 / 100])
    style_table_col_3 = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.red),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (0, 0)),  # first row
    ]
    col_3.setStyle(TableStyle(style_table_col_3))

    colwidth_table_1 = [_bts * 20 / 100, _bts * 50 / 100, _bts * 30 / 100]

    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (1, 0), (1, 0), 'TOP'),  # all columns
        ('VALIGN', (2, 0), (2, 0), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, 0), 'CENTER'),
    ]

    _tbl_header = Table(
        [(I, col_2, col_3)],
        colWidths=colwidth_table_1)
    _tbl_header.setStyle(TableStyle(style_table_header))

    # ---------------------------------Datos Cliente----------------------------#
    # client_id = bill_obj.client.id
    # client_obj = Client.objects.get(id=client_id)
    # type_client = client_obj.clienttype_set.first().document_type.id
    # info_document = client_obj.clienttype_set.first().document_number
    # telephone = client_obj.phone
    # email = client_obj.email
    info_address = ''
    # if telephone is None:
    #     telephone = '-'
    # if email is None:
    #     email = '-'
    # if type_client == '06':
    #     info_address = client_obj.clientaddress_set.last().address

    client_ruc = '20604193053'
    client_name = 'INDUSTRIAS ANDERQUIN EIRL'
    client_address = 'Jr. Carabaya No. 443 (Frente a la Plaza Manco Cápac) - JULIACA - JULIACA'

    tbl2_col1 = [
        ['Fecha de emisión', Paragraph(': ' + str(bill_obj.register_date.strftime("%d/%m/%Y")), styles['Left_Square']),
         'Lugar: ', Paragraph('JULIACA', styles['Left_Square'])],
        ['Señor(es)', Paragraph(': ' + str(client_name), styles['Left_Square']), '', ''],
        ['Direccion', Paragraph(': ' + str(client_address.upper()), styles['Left_Square']), '', ''],
        ['Doc. Identidad', Paragraph(': ' + str('RUC: ' + client_ruc), styles['Left_Square']), 'Moneda:',
         Paragraph('SOL', styles['Left_Square'])],
        # ['Telefono          :', Paragraph(str(telephone), styles['Left_Square'])],
        # ['Correo             :', Paragraph(str(email), styles['Left_Square'])],
        # ['Des. Pago : ', Paragraph(str(bill_obj), styles['Left_Square'])],
    ]
    header_description = Table(tbl2_col1,
                               colWidths=[_bts * 15 / 100, _bts * 50 / 100, _bts * 15 / 100, _bts * 20 / 100])
    style_table2_col1 = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'LEFT'),  # first column
        ('ALIGNMENT', (2, 0), (2, 0), 'RIGHT'),  # first column
        ('ALIGNMENT', (2, 3), (2, 3), 'RIGHT'),  # first column
        ('SPAN', (1, 1), (3, 1)),
        ('SPAN', (1, 2), (3, 2)),
        # ('BOX', (0, 0), (-1, -1), 0.9, colors.black),
        # ('BACKGROUND', (2, 0), (2, 0), colors.red),
        # ('BACKGROUND', (2, 3), (2, 3), colors.red),
        # ('LEFTPADDING', (0, 0), (0, -1), 13),  # first column
    ]
    header_description.setStyle(TableStyle(style_table2_col1))

    array_oc = []
    str_array_oc = ''
    # for p in bill_obj.purchase.all():
    #     if p.correlative:
    #         oc = p.correlative
    #     else:
    #         oc = int(p.bill_number[-5:])
    #     array_oc.append(oc)
    #     str_array_oc = str(array_oc).replace('[', '').replace(']', '')

    tbl3_col1 = [
        [Paragraph('Fecha de Pedido', styles['Center_Square']), Paragraph('Nº de Pedido', styles['Center_Square']),
         Paragraph('Nº O/C', styles['Center_Square'])],
        [Paragraph(str(bill_obj.register_date.strftime("%d/%m/%Y")), styles['Center_Square']),
         Paragraph(str(bill_obj.order_number), styles['Center_Square']),
         Paragraph(str(bill_obj.purchase.bill_number), styles['Center_Square'])]
    ]
    tbl2_col_1 = Table(tbl3_col1, colWidths=[_bts * 15 / 100, _bts * 15 / 100, _bts * 30 / 100])
    style_table2_col1 = [
        ('GRID', (0, 0), (-1, -1), 0.9, colors.black),  # all columns
        ('BACKGROUND', (0, 0), (3, 0), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
    ]
    tbl2_col_1.setStyle(TableStyle(style_table2_col1))

    tbl3_col2 = [
        [Paragraph('Condición de Pago', styles['Center_Square']),
         Paragraph('Fecha de Vencimiento', styles['Center_Square'])],
        [Paragraph('Factura a ' + str(bill_obj.payment_condition) + ' días', styles['Center_Square']),
         Paragraph(str(bill_obj.expiration_date.strftime("%d/%m/%Y")), styles['Center_Square'])],
    ]
    tbl2_col_2 = Table(tbl3_col2, colWidths=[_bts * 19.5 / 100])
    style_table2_col1 = [
        ('GRID', (0, 0), (-1, -1), 0.9, colors.black),  # all columns
        ('BACKGROUND', (0, 0), (2, 0), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
    ]
    tbl2_col_2.setStyle(TableStyle(style_table2_col1))

    _tbl_description_2 = [
        [tbl2_col_1, tbl2_col_2],
    ]
    description_2 = Table(_tbl_description_2, colWidths=[_bts * 60 / 100, _bts * 40 / 100])
    style_table_header = [
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        # ('SPAN', (0, 0), (0, 0)),  # first row
        # ('GRID', (0, 0), (-1, -1), 2, colors.lightgrey),
        # ('GRID', (0, 0), (0, 1), 3.5, colors.red)
    ]
    description_2.setStyle(TableStyle(style_table_header))

    style_table_header_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Newgot'),  # all columns
        ('GRID', (0, 0), (-1, -1), 1, colors.darkgray),  # all columns
        ('BACKGROUND', (0, 0), (-1, -1), colors.darkgray),  # all columns
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),  # all columns
        ('RIGHTPADDING', (1, 0), (1, -1), 10),  # second column
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # all column
        ('ALIGNMENT', (2, 0), (2, -1), 'LEFT'),  # second column
    ]
    width_table = [_bts * 8 / 100, _bts * 8 / 100, _bts * 7 / 100, _bts * 41 / 100, _bts * 10 / 100, _bts * 8 / 100,
                   _bts * 8 / 100, _bts * 10 / 100]
    header_detail = Table(
        [('Código', 'Cantidad', 'U. Venta', 'Descripción', 'Precio U.', 'V. Lista', 'Dsctos(%)', 'V. Venta Total')],
        colWidths=width_table)
    header_detail.setStyle(TableStyle(style_table_header_detail))

    style_table_detail = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.darkgray),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # all column
        ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'),  # three column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # first column
        ('RIGHTPADDING', (3, 0), (3, -1), 10),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),  # all columns
        # ('BACKGROUND', (1, 0), (1, -1),  colors.green),  # four column
    ]
    detail_rows = []
    _total = 0

    for d in bill_obj.purchase.purchasedetail_set.all():
        _product = Paragraph(str(d.product.name), styles["Justify_Square"])
        _detail_total = '{:,}'.format(round(d.quantity * d.price_unit, 2))
        detail_rows.append(
            (str(d.product.code), str(decimal.Decimal(round(d.quantity, 2))), str(d.unit.description), _product,
             str(decimal.Decimal(round(d.price_unit, 2))), str(0.00), str(0.00), _detail_total))
        _total = _total + d.quantity * d.price_unit
    detail_body = Table(detail_rows,
                        colWidths=width_table)
    detail_body.setStyle(TableStyle(style_table_detail))

    sub_total = decimal.Decimal(_total) / decimal.Decimal(1.18)
    igv = decimal.Decimal(_total) - sub_total

    table_bank = [
        [Paragraph('BANCO', styles['Center_Newgot_1']),
         Paragraph('MONEDA', styles['Center_Newgot_1']),
         Paragraph('CODIGO DE CUENTA CORRIENTE', styles['Center_Newgot_1']),
         Paragraph('CODIGO DE CUENTA INTERBANCARIO', styles['Center_Newgot_1'])],

        [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
         Paragraph('SOLES', styles['Center-text']), Paragraph('215-2023417-0-71', styles['Center-text']),
         Paragraph('002-215-002023417071-28', styles['Center-text'])],

        [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
         Paragraph('SOLES', styles['Center-text']), Paragraph('215-9844079-0-56', styles['Center-text']),
         Paragraph('002-215-009844079056-20', styles['Center-text'])],
    ]
    t_bank = Table(table_bank, colWidths=[_bts * 7 / 100, _bts * 7 / 100, _bts * 24 / 100, _bts * 24 / 100])
    style_bank = [
        ('SPAN', (0, 1), (0, 2)),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
    ]
    t_bank.setStyle(TableStyle(style_bank))

    total_col1 = [
        [t_bank],
        [Paragraph('OBSERVACION: ' + ' ', styles["Justify_Newgot"])],
        [Paragraph('SON: ' + numero_a_moneda(round(_total, 2), ),
                   styles["Justify_Newgot"])],
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

    money = 'S/.'
    _text = 'DESCUENTO'
    _discount = 0.00

    total_col2 = [
        [Paragraph('GRAVADA', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str('{:,}'.format(round(sub_total, 2))), styles["Right_Newgot"])],
        [Paragraph(_text, styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str(round(_discount, 2)), styles["Right_Newgot"])],
        [Paragraph('I.G.V.(18.00 %)', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str('{:,}'.format(round(igv, 2))), styles["Right_Newgot"])],
        [Paragraph('TOTAL', styles["Justify_Newgot"]),
         Paragraph(money + ' ' + str('{:,}'.format(round(sub_total + igv, 2))), styles["Right_Newgot"])],
    ]
    total_col_2 = Table(total_col2, colWidths=[_bts * 14 / 100, _bts * 19 / 100])

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

    _dictionary = []
    _dictionary.append(_tbl_header)
    _dictionary.append(OutputInvoiceGuide(count_row=1))
    _dictionary.append(Spacer(1, 5))
    _dictionary.append(header_description)
    _dictionary.append(Spacer(1, 5))
    _dictionary.append(description_2)
    _dictionary.append(Spacer(1, 10))
    _dictionary.append(header_detail)
    _dictionary.append(detail_body)
    _dictionary.append(Spacer(1, 10))
    _dictionary.append(total_page)

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=(8.3 * inch, 11.7 * inch),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='Factura'
                            )
    doc.build(_dictionary)

    response = HttpResponse(content_type='application/pdf')
    # response['Content-Disposition'] = 'attachment; filename="[{}].pdf"'.format(str('Factura:') + str(bill_obj.serial) + str(bill_obj.correlative))
    response.write(buff.getvalue())

    buff.close()
    return response


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
