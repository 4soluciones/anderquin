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
from .models import Purchase, PurchaseDetail, MoneyChange
from ..hrm.models import Worker, Subsidiary
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


LOGO = "static/assets/avatar/logo-anderquin-original.png"

MONTH = (
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE",
    "DICIEMBRE"
)


def query_apis_net_money(date_now):
    context = {}

    url = 'https://api.apis.net.pe/v1/tipo-cambio-sunat?fecha={}'.format(date_now)
    headers = {
        "Content-Type": 'application/json',
        'authorization': 'Bearer apis-token-5453.4I3HhSqKHJBWk0qpnTBCJGhi5qmoYJgF',
    }

    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        result = r.json()

        context = {
            'success': True,
            'fecha_busqueda': result.get('fecha'),
            'fecha_sunat': result.get('fecha'),
            'venta': result.get('venta'),
            'compra': result.get('compra'),
            'origen': result.get('origen'),
            'moneda': result.get('moneda'),
        }
    else:
        result = r.json()
        context = {
            'status': False,
            'errors': '400 Bad Request',
        }

    return context


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


def is_dollar(purchase_obj):
    if purchase_obj.currency_type == 'D':
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        r = query_apis_net_money(formatdate)

        if r.get('fecha_busqueda') == formatdate:
            sell = round(r.get('venta'), 3)
            buy = round(r.get('compra'), 3)
            search_date = r.get('fecha_busqueda')
            sunat_date = r.get('fecha_sunat')

            money_change_obj, created = MoneyChange.objects.get_or_create(
                search_date=search_date,
                sunat_date=sunat_date,
            )
            money_change_obj.sell = sell
            money_change_obj.buy = buy

            # money_change_obj = MoneyChange(
            #     search_date=search_date,
            #     sunat_date=sunat_date,
            #     sell=sell,
            #     buy=buy
            # )

            money_change_obj.save()
            purchase_obj.money_change = money_change_obj
            purchase_obj.save()
            return True

    return False


# ALTURA = 5.826772
# BASE = 8.26772
BASE = 21
ALTURA = 29.7


def print_pdf(request, pk=None):  # TICKET PASSENGER OLD
    _wt = BASE * inch - 50 * 0.05 * inch  # termical
    tbh_business_name_address = ''
    ml = 0.0 * inch
    mr = 0.0 * inch
    ms = 0.039 * inch
    mi = 0.039 * inch

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    I = Image(LOGO)
    I.drawHeight = inch * 3
    I.drawWidth = inch * 3

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    purchase_obj = Purchase.objects.get(id=pk)
    purchase_detail = PurchaseDetail.objects.filter(purchase__id=purchase_obj.id)

    supplier_obj = purchase_obj.supplier

    DIRECCION_CENTRAL = 'JR. CARABAYA NRO. 443 (AL FRENTE DE LA PLAZA MANCO CAPAC) PUNO - SAN ROMAN - JULIACA'
    DIRECCION_ALMACEN = 'JR. PALMERAS-STA. ASUNCION MZA. I5 LOTE 10 FRENTE A LA PLAZA DE SANTA ASUNCION PUNO-SAN ROMAN-JULIACA'

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    style_table_0 = [
        # ('BOX', (0, 0), (-1, -1), 3, colors.black),
        ('VALIGN', (0, 1), (0, 1), 'TOP'),
        # ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]

    RUC = f'20604193053'
    p0_1 = Paragraph(f'INDUSTRIAS ANDERQUIN EIRL', styles["Center-titulo"])
    p0_2 = Paragraph(f'RUC: {RUC}', styles["Center-titulo"])

    colwiths_table_0 = [_wt * 0.6 * 100 / 100]
    rowwiths_table_0 = [inch * 0.75, inch * 0.75]
    ana_c0 = Table(
        [(p0_1,)] +
        [(p0_2,)],
        colWidths=colwiths_table_0, rowHeights=rowwiths_table_0)
    ana_c0.setStyle(TableStyle(style_table_0))

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    style_table_1 = [
        ('BOX', (1, 0), (-1, -1), 3, colors.black),
        ('BOX', (1, 1), (-1, -1), 3, colors.black),
        ('GRID', (-1, 0), (-1, -1), 3, colors.black),
        # ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (1, -1), (1, -1), 'TOP'),
        ('VALIGN', (-1, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (-1, 1), (-1, 1), 'CENTER'),
        # ('BACKGROUND', (0, 0), (-1, -1), colors.grey),

        ('TOPPADDING', (0, 0), (1, 0), 0),
        ('LEFTPADDING', (0, 0), (1, 0), 0),
        ('RIGHPADDING', (0, 0), (1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (1, 0), 0),

        ('SPAN', (0, 0), (0, -1)),
        ('SPAN', (2, 1), (2, -1)),
    ]

    ORDEN_COMPRA = f'{purchase_obj.bill_number}'
    p1_1 = Paragraph(f'ORDEN DE COMPRA', styles["Center-titulo"])
    p1_2 = Paragraph(f'{ORDEN_COMPRA}', styles["Center-titulo"])
    p1_3 = Paragraph(f'SIG - FO - 029', styles["Center-titulo"])
    p1_4 = Paragraph(f'VERSION : 01', styles["Center-titulo"])

    colwiths_table_1 = [_wt * 20 / 100, _wt * 60 / 100, _wt * 20 / 100]
    rowwiths_table_1 = [inch * 1.5, inch * 0.75, inch * 0.75]
    ana_c1 = Table(
        [(I, ana_c0, p1_3)] +
        [('', p1_1, p1_4)] +
        [('', p1_2, '')],
        colWidths=colwiths_table_1, rowHeights=rowwiths_table_1)
    ana_c1.setStyle(TableStyle(style_table_1))

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    style_table_2 = [
        # ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]

    FECHA = purchase_obj.purchase_date

    if FECHA.day < 10:
        FECHA_DAY = f'0{FECHA.day}'
    else:
        FECHA_DAY = FECHA.day
    if FECHA.month < 10:
        FECHA_MONTH = f'0{FECHA.month}'
    else:
        FECHA_MONTH = FECHA.month

    FECHA_YEAR = FECHA.year
    p2_1 = Paragraph(f'FECHA: {FECHA_DAY}/{FECHA_MONTH}/{FECHA_YEAR}', styles["Left"])

    colwiths_table_2 = [_wt * 100 / 100]
    rowwiths_table_2 = [inch * 0.75]
    ana_c2 = Table(
        [(p2_1,)],
        colWidths=colwiths_table_2, rowHeights=rowwiths_table_2)
    ana_c2.setStyle(TableStyle(style_table_2))

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    style_table_3 = [
        # ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (0, 0), 2, colors.black),
        ('BOX', (0, 0), (0, -1), 2, colors.black),
        ('BOX', (0, 0), (0, 2), 2, colors.black),
        ('BACKGROUND', (0, 0), (0, 0), COLOR_BLUE),
        ('SPAN', (-1, -2), (-1, -1)),

        ('BOX', (2, 0), (2, 0), 2, colors.black),
        ('BOX', (2, 0), (2, -1), 2, colors.black),
        ('BACKGROUND', (2, 0), (2, 0), COLOR_BLUE),
    ]

    NOMBRE_PROVEEDOR = f'{supplier_obj.name}'
    RUC_PROVEEDOR = f'{supplier_obj.ruc}'
    CONDICION_PAGO = f'{purchase_obj.payment_condition}'
    METODO_PAGO = f'{purchase_obj.get_payment_method()}'
    TIPO_MONEDA = f'{purchase_obj.get_currency_type()}'

    moneda = f'{TIPO_MONEDA}'
    currency_type = is_dollar(purchase_obj)
    if currency_type:
        MONEY_CHANGE = f'{purchase_obj.money_change.sell}'
        moneda += f' [TIPO DE CAMBIO REFERENCIAL: {MONEY_CHANGE}]'

    p3_1 = Paragraph(f'PROVEEDOR:', styles["Left"])
    p3_2 = Paragraph(f'{NOMBRE_PROVEEDOR}', styles["Left"])
    p3_3 = Paragraph(f'RUC: {RUC_PROVEEDOR}', styles["Left"])
    p3_4_1 = Paragraph(f'Condición de Pago: {CONDICION_PAGO}', styles["Left"])
    p3_4_2 = Paragraph(f'Método de Pago: {METODO_PAGO}', styles["Left"])
    p3_4_3 = Paragraph(f'Moneda: {moneda}', styles["Left"])

    worker_obj = Worker.objects.get(user_id=request.user.id)
    TELEFONO = f'{worker_obj.employee.telephone_number}'
    # DIRECCION = f'{DIRECCION_ALMACEN}'
    DIRECCION = f'{DIRECCION_CENTRAL}'
    p3_4 = Paragraph(f'FACTURAR A:', styles["Left"])
    p3_5 = Paragraph(f'INDUSTRIAS ANDERQUIN EIRL', styles["Left"])
    p3_5_1 = Paragraph(f'RUC: 20604193053', styles["Left"])
    p3_6 = Paragraph(f'Telf.: 954001800', styles["Left"])
    p3_7 = Paragraph(f'{DIRECCION}', styles["Left"])

    colwiths_table_3 = [_wt * 49 / 100, _wt * 2 / 100, _wt * 49 / 100]
    rowwiths_table_3 = [inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5]
    ana_c3 = Table(
        [(p3_1, '', p3_4)] +
        [(p3_2, '', p3_5)] +
        [(p3_3, '', p3_5_1)] +
        [(p3_4_1, '', p3_6)] +
        [(p3_4_2, '', p3_7)] +
        [(p3_4_3, '', '')],
        colWidths=colwiths_table_3, rowHeights=rowwiths_table_3)
    ana_c3.setStyle(TableStyle(style_table_3))

    _dictionary = []
    # _dictionary.append(Background())
    # _dictionary.append(Spacer(1, 5))
    # _dictionary.append(Spacer(0, 0))
    _dictionary.append(Spacer(width=0, height=50))
    _dictionary.append(ana_c1)
    _dictionary.append(Spacer(width=8, height=8))
    _dictionary.append(ana_c2)
    _dictionary.append(Spacer(width=8, height=8))
    _dictionary.append(ana_c3)

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    style_table_4 = [
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BLUE),
        # ('BACKGROUND', (0, 0), (4, 0), COLOR_BLUE),
        # ('BACKGROUND', (5, 0), (7, 0), colors.lightgreen),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'),
    ]

    p4_1 = Paragraph(f'N°', styles["CenterSquare"])
    p4_2 = Paragraph(f'COD', styles["Left"])
    p4_3 = Paragraph(f'DESCRIPCIÓN', styles["Left"])
    p4_4 = Paragraph(f'CANTIDAD', styles["CenterSquare"])
    # p4_4 = Paragraph(f'UM', styles["Left"])
    p4_5 = Paragraph(f'U. M.', styles["CenterSquare"])
    p4_6 = Paragraph(f'CANT./U. M.', styles["Left"])
    # p4_6 = Paragraph(f'UNIDADES', styles["Left"])
    p4_7 = Paragraph(f'PRECIO UNIT.', styles["Left"])
    p4_8 = Paragraph(f'SUB TOTAL', styles["Right"])

    colwiths_table_4 = [_wt * 3 / 100, _wt * 9 / 100, _wt * 30 / 100, _wt * 11 / 100, _wt * 15 / 100, _wt * 10 / 100,
                        _wt * 11 / 100, _wt * 11 / 100]
    rowwiths_table_4 = [inch * 1]
    ana_c4 = Table(
        [(p4_1, p4_2, p4_3, p4_4, p4_5, p4_6, p4_7, p4_8)],
        colWidths=colwiths_table_4, rowHeights=rowwiths_table_4)
    ana_c4.setStyle(TableStyle(style_table_4))

    _dictionary.append(Spacer(width=8, height=16))
    _dictionary.append(ana_c4)

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    total = 0
    contador = 1
    # for i in range(products):
    style_table_5 = [
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('ALIGNMENT', (0, 0), (-1, 0), 'CENTER'),
        # ('GRID', (0, 0), (-1, -1), 0.9, colors.red),
    ]
    for i in purchase_detail.all():
        product = i.product
        product_detail_obj = ProductDetail.objects.get(product=product, unit=i.unit)
        quantity_minimum = product_detail_obj.quantity_minimum

        # quantity_x_und = (i.quantity / cantidad_unidad).quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_UP)
        num = f'{contador}'
        contador += 1
        cod = f'{product.code}'
        description = f'{product.name}'
        um = f'{i.unit.description}({int(quantity_minimum)}UND)'

        quantity_und = decimal.Decimal(i.quantity * quantity_minimum)
        quantity = round(i.quantity, 2)
        price_unit = round(i.price_unit, 6)
        sub_total = (i.price_unit * quantity).quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN)

        total += sub_total

        p5_1 = Paragraph(num, styles["CenterSquare"])
        p5_2 = Paragraph(cod, styles["Left"])
        p5_3 = Paragraph(description, styles["Left"])
        p5_4 = Paragraph(um, styles["CenterSquare"])
        p5_5 = Paragraph(f'{quantity}', styles["CenterSquare"])
        p5_6 = Paragraph(f'{int(quantity_und)}', styles["CenterSquare"])
        p5_7 = Paragraph(f'{price_unit}', styles["Left"])
        p5_8 = Paragraph('{:,}'.format(sub_total), styles["Right"])

        colwiths_table_5 = [_wt * 3 / 100, _wt * 9 / 100, _wt * 30 / 100, _wt * 11 / 100, _wt * 15 / 100, _wt * 10 / 100,
                            _wt * 11 / 100, _wt * 11 / 100]
        # rowwiths_table_5 = [inch * 0.5]
        ana_c5 = Table(
            [(p5_1, p5_2, p5_3, p5_6, p5_4, p5_5, p5_7, p5_8)],
            colWidths=colwiths_table_5)
        ana_c5.setStyle(TableStyle(style_table_5))

        _dictionary.append(ana_c5)

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #
    style_table_6 = [
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        # ('BACKGROUND', (0, 0), (-1, -1), COLOR_BLUE),
    ]
    str_total = '{:,}'.format(total)
    if currency_type:
        p6_1 = Paragraph(f'TOTAL: $ {str_total}', styles["Right"])
    else:
        p6_1 = Paragraph(f'TOTAL: S/ {str_total}', styles["Right"])

    colwiths_table_6 = [_wt * 100 / 100]
    rowwiths_table_6 = [inch * 0.5]
    ana_c6 = Table(
        [(p6_1,)],
        colWidths=colwiths_table_6, rowHeights=rowwiths_table_6)
    ana_c6.setStyle(TableStyle(style_table_6))

    _dictionary.append(Spacer(width=8, height=16))
    _dictionary.append(ana_c6)

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    style_table_7 = [
        # ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('BOX', (0, 0), (1, -1), 2, colors.black),
        ('BOX', (-1, 0), (-1, -1), 2, colors.black),
        # ('LEADING', (0, 0), (0, 0), 30),
        # ('SPAN', (0, 0), (0, -1)),
        # ('SPAN', (3, 0), (3, -1)),
    ]
    p7_1 = Paragraph(f'FACTURAR A', styles["Left"])
    p7_2 = Paragraph(f'INDUSTRIAS ANDERQUIN EIRL', styles["Left"])
    p7_3 = Paragraph(f'RUC: 20604193053', styles["Left"])
    p7_4 = Paragraph(f'JR. CARABAYA NRO. 443 (AL FRENTE DE LA PLAZA MANCO CAPAC) PUNO - SAN ROMAN - JULIACA',
                     styles["Left"])
    p7_5 = Paragraph(f'Juliaca, San Roman, Puno', styles["Left"])

    # reference_obj = purchase_obj.reference

    p7_6 = Paragraph(f'LUGAR DE ENTREGA:', styles["Right"])

    # if not supplier_obj.is_type_reference:
    #     if purchase_obj.delivery == 'A':
    #         direccion = f'JR. CARABAYA NRO. 443 (AL FRENTE DE LA PLAZA MANCO CAPAC) PUNO - SAN ROMAN - JULIACA'
    #     elif purchase_obj.delivery == 'P':
    #         direccion = f'{supplier_obj.address}'
    # elif supplier_obj.is_type_reference and reference_obj.is_private:
    #     direccion = f'{purchase_obj.reference_entity.address}'
    # else:
    #     direccion = f'{reference_obj.address}'

    p7_7 = Paragraph(f'{purchase_obj.delivery_address}', styles["Left"])
    p7_8 = Paragraph(f'{purchase_obj.city}', styles["JustifyTitle"])

    colwiths_table_7 = [_wt * 14 / 100, _wt * 1 / 100, _wt * 1 / 100, _wt * 69 / 100, _wt * 15 / 100]
    rowwiths_table_7 = [inch * 1]
    ana_c7 = Table(
        [(p7_6, '', '', p7_7, p7_8)],
        colWidths=colwiths_table_7, rowHeights=rowwiths_table_7)
    ana_c7.setStyle(TableStyle(style_table_7))

    _dictionary.append(Spacer(width=8, height=16))
    _dictionary.append(ana_c7)

    # **************************************************************************************************************** #
    # ********************* if ********************* #
    # **************************************************************************************************************** #
    if purchase_obj.client_reference:
        client_reference = purchase_obj.client_reference
        style_table_8 = [
            # ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]

        p8_1 = Paragraph(f'Referencia de Venta', styles["Left"])

        colwiths_table_8 = [_wt * 100 / 100]
        rowwiths_table_8 = [inch * 0.75]
        ana_c8 = Table(
            [(p8_1,)],
            colWidths=colwiths_table_8, rowHeights=rowwiths_table_8)
        ana_c8.setStyle(TableStyle(style_table_8))
        _dictionary.append(Spacer(width=8, height=16))
        _dictionary.append(ana_c8)

        # **************************************************************************************************************** #
        # **************************************************************************************************************** #

        style_table_9 = [
            # ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            # ('BOX', (0, 4), (-1, -1), 2, colors.black),
            # ('BOX', (-1, -4), (-1, -1), 2, colors.black),
            # ('BOX', (0, 0), (0, -1), 2, colors.black),

            # ('SPAN', (-1, 0), (-1, 3)),
            # ('SPAN', (-1, 0), (-1, 3)),
            # ('SPAN', (1, 4), (1, 5)),

        ]
        reference = ''
        if purchase_obj.reference:
            reference = purchase_obj.reference.upper()

        # addressEntity_obj = reference_obj.entity_address.all().first()

        client_address = '-'
        siaf = '-'
        if client_reference.clientaddress_set.exists():
            client_address = client_reference.clientaddress_set.last().address.upper()
        if purchase_obj.client_reference.cod_siaf:
            siaf = purchase_obj.client_reference.cod_siaf

        p9_1 = Paragraph(f'Razón Social: ', styles["Right"])
        p9_2 = Paragraph(f'{client_reference.names.upper()}', styles["Left"])
        p9_3 = Paragraph(f'RUC: ', styles["Right"])
        p9_4 = Paragraph(f'{client_reference.clienttype_set.last().document_number}', styles["Left"])
        p9_5 = Paragraph(f'Dirección: ', styles["Right"])
        p9_6 = Paragraph(f'{client_address}', styles["Left"])
        p9_7 = Paragraph(f'Referencia: ', styles["Right"])
        # p9_8 = Paragraph(f'{purchase_obj.oc_supplier}', styles["Left"])
        p9_8 = Paragraph(f'{reference}', styles["Left"])
        p9_9 = Paragraph(f'Código SIAF: ', styles["Right"])
        p9_10 = Paragraph(f'{siaf}', styles["Left"])
        p9_11 = Paragraph(f'Fecha de Entrega: ', styles["Right"])
        p9_12 = Paragraph(f'{purchase_obj.delivery_date.strftime("%d/%m/%Y")}', styles["Left"])

        colwiths_table_9 = [_wt * 14 / 100, _wt * 2 / 100, _wt * 84 / 100]
        rowwiths_table_9 = [inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.75, inch * 0.5, inch * 0.75]
        ana_c9 = Table(
            [(p9_1, '', p9_2)] +
            [(p9_3, '', p9_4)] +
            [(p9_9, '', p9_10)] +
            [(p9_5, '', p9_6)] +
            [(p9_7, '', p9_8)] +
            [(p9_11, '', p9_12)],
            colWidths=colwiths_table_9, rowHeights=rowwiths_table_9)
        ana_c9.setStyle(TableStyle(style_table_9))

        _dictionary.append(Spacer(width=8, height=16))
        _dictionary.append(ana_c9)

        # ********************* if ********************* #
        if purchase_obj.client_reference_entity:
            client_reference_entity = purchase_obj.client_reference_entity
            style_table_10 = [
                # ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]

            p10_1 = Paragraph(f'Referencia de Venta a la Entidad', styles["Left"])

            colwiths_table_10 = [_wt * 100 / 100]
            rowwiths_table_10 = [inch * 0.75]
            ana_c10 = Table(
                [(p10_1,)],
                colWidths=colwiths_table_10, rowHeights=rowwiths_table_10)
            ana_c10.setStyle(TableStyle(style_table_10))
            _dictionary.append(Spacer(width=8, height=16))
            _dictionary.append(ana_c10)

            # **************************************************************************************************************** #
            # **************************************************************************************************************** #

            style_table_11 = [
                # ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 2, colors.black),
                # ('BACKGROUND', (0, 2), (0, 2), COLOR_BLUE),
                ('VALIGN', (0, 2), (0, 2), 'TOP'),
                # ('BOX', (0, 4), (-1, -1), 2, colors.black),
                # ('BOX', (-1, -4), (-1, -1), 2, colors.black),
                # ('BOX', (0, 0), (0, -1), 2, colors.black),

                # ('SPAN', (-1, 0), (-1, 3)),
                # ('SPAN', (-1, 0), (-1, 3)),
                # ('SPAN', (1, 4), (1, 5)),
            ]

            # reference_entity_obj = purchase_obj.reference_entity

            address_entity = '-'
            if client_reference_entity.clientaddress_set.exists():
                address_entity = client_reference_entity.clientaddress_set.last().address.upper()

            p11_1 = Paragraph(f'Razón Social: ', styles["Right"])
            p11_2 = Paragraph(f'{client_reference_entity.names.upper()}', styles["Left"])
            p11_3 = Paragraph(f'RUC: ', styles["Right"])
            p11_4 = Paragraph(f'{client_reference_entity.clienttype_set.last().document_number}', styles["Left"])
            p11_5 = Paragraph(f'Dirección: ', styles["Right"])
            p11_6 = Paragraph(f'{address_entity}', styles["Left"])
            # p10_6 = Paragraph(f'Referencia: ', styles["Right"])

            colwiths_table_11 = [_wt * 14 / 100, _wt * 2 / 100, _wt * 84 / 100]
            # rowwiths_table_11 = [inch * 0.5, inch * 0.5, inch * 0.5]
            ana_c11 = Table(
                [(p11_1, '', p11_2)] +
                [(p11_3, '', p11_4)] +
                [(p11_5, '', p11_6)],
                colWidths=colwiths_table_11)
            ana_c11.setStyle(TableStyle(style_table_11))

            _dictionary.append(Spacer(width=8, height=16))
            _dictionary.append(ana_c11)
    #
    #         # ********************* endif ********************* #
    #
    #     # **************************************************************************************************************** #
    #     # ********************* endif ********************* #
    #     # **************************************************************************************************************** #
    if purchase_obj.observation:
        style_table_12 = [
            # ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]

        p12_1 = Paragraph(f'Observaciones', styles["Left"])

        colwiths_table_12 = [_wt * 100 / 100]
        rowwiths_table_12 = [inch * 0.75]
        ana_c12 = Table(
            [(p12_1,)],
            colWidths=colwiths_table_12, rowHeights=rowwiths_table_12)
        ana_c12.setStyle(TableStyle(style_table_12))
        _dictionary.append(Spacer(width=8, height=16))
        _dictionary.append(ana_c12)

        # **************************************************************************************************************** #
        # **************************************************************************************************************** #

        style_table_13 = [
            # ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            # ('BOX', (0, 4), (-1, -1), 2, colors.black),
            # ('BOX', (-1, -4), (-1, -1), 2, colors.black),
            # ('BOX', (0, 0), (0, -1), 2, colors.black),

            # ('SPAN', (-1, 0), (-1, 3)),
            # ('SPAN', (-1, 0), (-1, 3)),
            # ('SPAN', (1, 4), (1, 5)),

        ]

        observations = purchase_obj.observation.upper()

        p13_1 = Paragraph(f'Observacion: ', styles["Right"])
        p13_2 = Paragraph(f'{observations}', styles["Left"])

        colwiths_table_13 = [_wt * 14 / 100, _wt * 2 / 100, _wt * 84 / 100]
        rowwiths_table_13 = [inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5]
        ana_c13 = Table(
            [(p13_1, '', p13_2)] +
            [('', '', '')] +
            [('', '', '')] +
            [('', '', '')],
            colWidths=colwiths_table_13, rowHeights=rowwiths_table_13)
        ana_c13.setStyle(TableStyle(style_table_13))

        _dictionary.append(Spacer(width=8, height=16))
        _dictionary.append(ana_c13)
    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    style_table_99 = [
        # ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]
    _datetime = datetime.now()
    _datetime_str = _datetime.strftime('%d-%m-%Y %H:%M')

    usuario = request.user
    p99_1 = Paragraph(f'Usuario: {usuario} - {_datetime_str}', styles["Left-Simple"])

    colwiths_table_99 = [_wt * 100 / 100]
    rowwiths_table_99 = [inch * 0.75]
    ana_c99 = Table(
        [(p99_1,)],
        colWidths=colwiths_table_99, rowHeights=rowwiths_table_99)
    ana_c99.setStyle(TableStyle(style_table_99))
    _dictionary.append(Spacer(width=8, height=16))
    _dictionary.append(ana_c99)

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    # _dictionary.append(Spacer(-4, -4))
    # _dictionary.append(Spacer(-2, -2))
    buff = io.BytesIO()

    pz_matricial = (2.57 * inch, 11.6 * inch)
    # pz_termical = (3.14961 * inch, 11.6 * inch)
    pz_termical = (BASE * inch, ALTURA * inch)

    doc = SimpleDocTemplate(buff,
                            pagesize=pz_termical,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='Orden de Compra'
                            )
    doc.build(_dictionary)
    # doc.build(elements)
    # doc.build(Story)
    #
    # response = HttpResponse(content_type='application/pdf')
    # response['Content-Disposition'] = 'attachment; filename="{}-{}.pdf"'.format(order_obj.nombres, order_obj.pagos.id)
    #

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="[{}].pdf"'.format(purchase_obj.bill_number)

    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=0, minute=0, second=0)
    expires = datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")

    response.set_cookie('bp', value=pk, expires=expires)

    response.write(buff.getvalue())

    buff.close()
    return response


# def print_pdf_bill(request, pk=None):
#     _a4 = (8.3 * inch, 11.7 * inch)
#     ml = 0.25 * inch
#     mr = 0.25 * inch
#     ms = 0.25 * inch
#     mi = 0.25 * inch
#
#     _bts = 8.3 * inch - 0.25 * inch - 0.25 * inch
#
#     I = Image(LOGO)
#     I.drawHeight = 3.60 * inch / 2.9
#     I.drawWidth = 3.9 * inch / 2.9
#
#     bill_obj = Bill.objects.get(id=pk)
#     bill_detail = BillDetail.objects.filter(bill=bill_obj)
#
#     tbl1_col__2 = [
#         [Paragraph('INDUSTRIAS ANDERQUIN EIRL', styles["Justify_Newgot_title"])],
#         [Paragraph('JR. CARABAYA NRO. 443', styles['Normal'])],
#         [Paragraph('JULIACA - SAN ROMAN - PUNO', styles['Normal'])],
#         ['Telefono: ' + str('999999999')],
#         ['Correo: ' + str('email@anderquin.com')],
#     ]
#     col_2 = Table(tbl1_col__2)
#     style_table_col_2 = [
#         # ('GRID', (0, 0), (-1, -1), 1, colors.black),
#     ]
#     col_2.setStyle(TableStyle(style_table_col_2))
#
#     tbl1_col__3 = [
#         [Paragraph('RUC 20604193053', styles["Center_Newgot_title"])],
#         [Paragraph('FACTURA ' + ' ELECTRÓNICA', styles["Center_Newgot_title"])],
#         [Paragraph('F001' + '-' + '0001', styles["Center_Newgot_title"])],
#     ]
#     col_3 = Table(tbl1_col__3, colWidths=[_bts * 28 / 100])
#     style_table_col_3 = [
#         # ('GRID', (0, 0), (-1, -1), 0.9, colors.red),  # all columns
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
#         ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
#         ('SPAN', (0, 0), (0, 0)),  # first row
#     ]
#     col_3.setStyle(TableStyle(style_table_col_3))
#
#     colwidth_table_1 = [_bts * 20 / 100, _bts * 50 / 100, _bts * 30 / 100]
#
#     style_table_header = [
#         # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
#         ('VALIGN', (1, 0), (1, 0), 'TOP'),  # all columns
#         ('VALIGN', (2, 0), (2, 0), 'MIDDLE'),  # all columns
#         ('ALIGNMENT', (0, 0), (0, 0), 'CENTER'),
#     ]
#
#     _tbl_header = Table(
#         [(I, col_2, col_3)],
#         colWidths=colwidth_table_1)
#     _tbl_header.setStyle(TableStyle(style_table_header))
#
#     # ---------------------------------Datos Cliente----------------------------#
#     client_id = bill_obj.client.id
#     client_obj = Client.objects.get(id=client_id)
#     type_client = client_obj.clienttype_set.first().document_type.id
#     info_document = client_obj.clienttype_set.first().document_number
#     telephone = client_obj.phone
#     email = client_obj.email
#     info_address = ''
#     if telephone is None:
#         telephone = '-'
#     if email is None:
#         email = '-'
#     if type_client == '06':
#         info_address = client_obj.clientaddress_set.last().address
#
#     tbl2_col1 = [
#         ['Fecha de emisión', Paragraph(': ' + str(bill_obj.issue_date.strftime("%d/%m/%Y")), styles['Left_Square']),
#          'Lugar: ', Paragraph('JULIACA', styles['Left_Square'])],
#         ['Señor(es)', Paragraph(': ' + str(client_obj.names), styles['Left_Square']), '', ''],
#         ['Direccion', Paragraph(': ' + str(info_address.upper()), styles['Left_Square']), '', ''],
#         ['Doc. Identidad', Paragraph(': ' + str('RUC: ' + info_document), styles['Left_Square']), 'Moneda:',
#          Paragraph('SOL', styles['Left_Square'])],
#         # ['Telefono          :', Paragraph(str(telephone), styles['Left_Square'])],
#         # ['Correo             :', Paragraph(str(email), styles['Left_Square'])],
#         # ['Des. Pago : ', Paragraph(str(bill_obj), styles['Left_Square'])],
#     ]
#     header_description = Table(tbl2_col1,
#                                colWidths=[_bts * 15 / 100, _bts * 50 / 100, _bts * 15 / 100, _bts * 20 / 100])
#     style_table2_col1 = [
#         # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
#         ('ALIGNMENT', (0, 0), (0, -1), 'LEFT'),  # first column
#         ('ALIGNMENT', (2, 0), (2, 0), 'RIGHT'),  # first column
#         ('ALIGNMENT', (2, 3), (2, 3), 'RIGHT'),  # first column
#         ('SPAN', (1, 1), (3, 1)),
#         ('SPAN', (1, 2), (3, 2)),
#         # ('BOX', (0, 0), (-1, -1), 0.9, colors.black),
#         # ('BACKGROUND', (2, 0), (2, 0), colors.red),
#         # ('BACKGROUND', (2, 3), (2, 3), colors.red),
#         # ('LEFTPADDING', (0, 0), (0, -1), 13),  # first column
#     ]
#     header_description.setStyle(TableStyle(style_table2_col1))
#
#     array_oc = []
#     str_array_oc = ''
#     for p in bill_obj.purchase.all():
#         if p.correlative:
#             oc = p.correlative
#         else:
#             oc = int(p.bill_number[-5:])
#         array_oc.append(oc)
#         str_array_oc = str(array_oc).replace('[', '').replace(']', '')
#
#     tbl3_col1 = [
#         [Paragraph('Fecha de Pedido', styles['Center_Square']), Paragraph('Nº de Pedido', styles['Center_Square']),
#          Paragraph('Nº O/C', styles['Center_Square'])],
#         [Paragraph(str(bill_obj.order_date.strftime("%d/%m/%Y")), styles['Center_Square']),
#          Paragraph(str(bill_obj.order_number), styles['Center_Square']),
#          Paragraph(str_array_oc, styles['Center_Square'])]
#     ]
#     tbl2_col_1 = Table(tbl3_col1, colWidths=[_bts * 15 / 100, _bts * 15 / 100, _bts * 30 / 100])
#     style_table2_col1 = [
#         ('GRID', (0, 0), (-1, -1), 0.9, colors.black),  # all columns
#         ('BACKGROUND', (0, 0), (3, 0), colors.lightgrey),
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
#         ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
#     ]
#     tbl2_col_1.setStyle(TableStyle(style_table2_col1))
#
#     tbl3_col2 = [
#         [Paragraph('Condición de Pago', styles['Center_Square']),
#          Paragraph('Fecha de Vencimiento', styles['Center_Square'])],
#         [Paragraph('Factura a ' + str(bill_obj.pay_condition) + ' días', styles['Center_Square']),
#          Paragraph(str(bill_obj.due_date.strftime("%d/%m/%Y")), styles['Center_Square'])],
#     ]
#     tbl2_col_2 = Table(tbl3_col2, colWidths=[_bts * 19.5 / 100])
#     style_table2_col1 = [
#         ('GRID', (0, 0), (-1, -1), 0.9, colors.black),  # all columns
#         ('BACKGROUND', (0, 0), (2, 0), colors.lightgrey),
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
#         ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
#     ]
#     tbl2_col_2.setStyle(TableStyle(style_table2_col1))
#
#     _tbl_description_2 = [
#         [tbl2_col_1, tbl2_col_2],
#     ]
#     description_2 = Table(_tbl_description_2, colWidths=[_bts * 60 / 100, _bts * 40 / 100])
#     style_table_header = [
#         # ('GRID', (0, 0), (-1, -1), 0.9, colors.blue),  # all columns
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
#         ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
#         # ('SPAN', (0, 0), (0, 0)),  # first row
#         # ('GRID', (0, 0), (-1, -1), 2, colors.lightgrey),
#         # ('GRID', (0, 0), (0, 1), 3.5, colors.red)
#     ]
#     description_2.setStyle(TableStyle(style_table_header))
#
#     style_table_header_detail = [
#         ('FONTNAME', (0, 0), (-1, -1), 'Newgot'),  # all columns
#         ('GRID', (0, 0), (-1, -1), 1, colors.darkgray),  # all columns
#         ('BACKGROUND', (0, 0), (-1, -1), colors.darkgray),  # all columns
#         ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
#         ('FONTSIZE', (0, 0), (-1, -1), 10),  # all columns
#         ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 5),  # all columns
#         ('RIGHTPADDING', (1, 0), (1, -1), 10),  # second column
#         ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # all column
#         ('ALIGNMENT', (2, 0), (2, -1), 'LEFT'),  # second column
#     ]
#     width_table = [_bts * 8 / 100, _bts * 8 / 100, _bts * 7 / 100, _bts * 41 / 100, _bts * 10 / 100, _bts * 8 / 100,
#                    _bts * 8 / 100, _bts * 10 / 100]
#     header_detail = Table(
#         [('Código', 'Cantidad', 'U. Venta', 'Descripción', 'Precio U.', 'V. Lista', 'Dsctos(%)', 'V. Venta Total')],
#         colWidths=width_table)
#     header_detail.setStyle(TableStyle(style_table_header_detail))
#
#     style_table_detail = [
#         ('FONTNAME', (0, 0), (-1, -1), 'Square'),
#         ('GRID', (0, 0), (-1, -1), 0.3, colors.darkgray),
#         ('FONTSIZE', (0, 0), (-1, -1), 9),
#         ('LEFTPADDING', (0, 0), (0, -1), 10),  # first column
#         ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # all column
#         ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'),  # three column
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # first column
#         ('RIGHTPADDING', (3, 0), (3, -1), 10),  # first column
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 4),  # all columns
#         # ('BACKGROUND', (1, 0), (1, -1),  colors.green),  # four column
#     ]
#     detail_rows = []
#     _total = 0
#
#     for d in bill_obj.billdetail_set.all():
#         _product = Paragraph(str(d.product.name), styles["Justify_Square"])
#         _detail_total = '{:,}'.format(round(d.quantity * d.price_unit, 2))
#         detail_rows.append(
#             (str(d.product.code), str(decimal.Decimal(round(d.quantity, 2))), str(d.unit.description), _product,
#              str(decimal.Decimal(round(d.price_unit, 2))), str(0.00), str(0.00), _detail_total))
#         _total = _total + d.quantity * d.price_unit
#     detail_body = Table(detail_rows,
#                         colWidths=width_table)
#     detail_body.setStyle(TableStyle(style_table_detail))
#
#     sub_total = decimal.Decimal(_total) / decimal.Decimal(1.18)
#     igv = decimal.Decimal(_total) - sub_total
#
#     table_bank = [
#         [Paragraph('BANCO', styles['Center_Newgot_1']),
#          Paragraph('MONEDA', styles['Center_Newgot_1']),
#          Paragraph('CODIGO DE CUENTA CORRIENTE', styles['Center_Newgot_1']),
#          Paragraph('CODIGO DE CUENTA INTERBANCARIO', styles['Center_Newgot_1'])],
#
#         [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
#          Paragraph('SOLES', styles['Center-text']), Paragraph('215-2023417-0-71', styles['Center-text']),
#          Paragraph('002-215-002023417071-28', styles['Center-text'])],
#
#         [Paragraph('CUENTAS BCP', styles['Center_Newgot_1']),
#          Paragraph('SOLES', styles['Center-text']), Paragraph('215-9844079-0-56', styles['Center-text']),
#          Paragraph('002-215-009844079056-20', styles['Center-text'])],
#     ]
#     t_bank = Table(table_bank, colWidths=[_bts * 7 / 100, _bts * 7 / 100, _bts * 24 / 100, _bts * 24 / 100])
#     style_bank = [
#         ('SPAN', (0, 1), (0, 2)),
#         ('RIGHTPADDING', (0, 0), (-1, -1), 0),
#         ('LEFTPADDING', (0, 0), (-1, -1), 3),
#         ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
#         ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
#     ]
#     t_bank.setStyle(TableStyle(style_bank))
#
#     total_col1 = [
#         [t_bank],
#         [Paragraph('OBSERVACION: ' + ' ', styles["Justify_Newgot"])],
#         [Paragraph('SON: ' + numero_a_moneda(round(_total, 2), ),
#                    styles["Justify_Newgot"])],
#     ]
#     total_col_1 = Table(total_col1, colWidths=[_bts * 63 / 100])
#     style_table_col1 = [
#         ('RIGHTPADDING', (0, 0), (-1, -1), 20),
#         ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
#         ('TOPPADDING', (0, 0), (-1, -1), 0),
#         ('LEFTPADDING', (0, 0), (-1, -1), -5),
#         # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),
#     ]
#     total_col_1.setStyle(TableStyle(style_table_col1))
#
#     money = 'S/.'
#     _text = 'DESCUENTO'
#     _discount = 0.00
#
#     total_col2 = [
#         [Paragraph('GRAVADA', styles["Justify_Newgot"]),
#          Paragraph(money + ' ' + str('{:,}'.format(round(sub_total, 2))), styles["Right_Newgot"])],
#         [Paragraph(_text, styles["Justify_Newgot"]),
#          Paragraph(money + ' ' + str(round(_discount, 2)), styles["Right_Newgot"])],
#         [Paragraph('I.G.V.(18.00 %)', styles["Justify_Newgot"]),
#          Paragraph(money + ' ' + str('{:,}'.format(round(igv, 2))), styles["Right_Newgot"])],
#         [Paragraph('TOTAL', styles["Justify_Newgot"]),
#          Paragraph(money + ' ' + str('{:,}'.format(round(sub_total + igv, 2))), styles["Right_Newgot"])],
#     ]
#     total_col_2 = Table(total_col2, colWidths=[_bts * 14 / 100, _bts * 19 / 100])
#
#     style_table_col2 = [
#         ('RIGHTPADDING', (0, 0), (-1, -1), 5),
#         ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),
#         ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgray),
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
#     ]
#     total_col_2.setStyle(TableStyle(style_table_col2))
#
#     total_ = [
#         [total_col_1, total_col_2],
#     ]
#     total_page = Table(total_, colWidths=[_bts * 65 / 100, _bts * 35 / 100])
#     style_table_page = [
#         ('ALIGNMENT', (0, 0), (-1, -1), 'LEFT'),  # three column
#         ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # first column
#         # ('GRID', (0, 0), (-1, -1), 0.5, colors.red),
#         ('RIGHTPADDING', (0, 0), (-1, -1), 0),
#     ]
#     total_page.setStyle(TableStyle(style_table_page))
#
#     _dictionary = []
#     _dictionary.append(_tbl_header)
#     _dictionary.append(OutputInvoiceGuide(count_row=1))
#     _dictionary.append(Spacer(1, 5))
#     _dictionary.append(header_description)
#     _dictionary.append(Spacer(1, 5))
#     _dictionary.append(description_2)
#     _dictionary.append(Spacer(1, 10))
#     _dictionary.append(header_detail)
#     _dictionary.append(detail_body)
#     _dictionary.append(Spacer(1, 10))
#     _dictionary.append(total_page)
#
#     buff = io.BytesIO()
#     doc = SimpleDocTemplate(buff,
#                             pagesize=(8.3 * inch, 11.7 * inch),
#                             rightMargin=mr,
#                             leftMargin=ml,
#                             topMargin=ms,
#                             bottomMargin=mi,
#                             title='Factura'
#                             )
#     doc.build(_dictionary)
#
#     response = HttpResponse(content_type='application/pdf')
#     # response['Content-Disposition'] = 'attachment; filename="[{}].pdf"'.format(str('Factura:') + str(bill_obj.serial) + str(bill_obj.correlative))
#     response.write(buff.getvalue())
#
#     buff.close()
#     return response


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
