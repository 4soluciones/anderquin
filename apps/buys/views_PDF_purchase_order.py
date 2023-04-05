import decimal
import os

import reportlab
import io
from datetime import datetime, timedelta, date

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
from .models import Purchase, PurchaseDetail, SalesReference, SalesReferenceEntity
from ..sales.models import Supplier

PAGE_HEIGHT = defaultPageSize[1]
PAGE_WIDTH = defaultPageSize[0]

COLOR_PDF = colors.Color(red=(152.0 / 255), green=(29.0 / 255), blue=(31.0 / 255))
COLOR_GREEN = colors.Color(red=(27.0 / 255), green=(140.0 / 255), blue=(66.0 / 255))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, leading=30, fontName='Square', fontSize=25))
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

styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, leading=10, fontName='Square-Bold', fontSize=10,
                          textColor=COLOR_PDF))
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

MONTH = (
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE",
    "DICIEMBRE"
)


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

    FECHA = date.today()

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
        ('BACKGROUND', (0, 0), (0, 0), COLOR_GREEN),

        ('BOX', (2, 0), (2, 0), 2, colors.black),
        ('BOX', (2, 0), (2, -1), 2, colors.black),
        ('BACKGROUND', (2, 0), (2, 0), COLOR_GREEN),
    ]

    NOMBRE_PROVEEDOR = f'{supplier_obj.name}'
    RUC_PROVEEDOR = f'{supplier_obj.ruc}'

    p3_1 = Paragraph(f'PROVEEDOR:', styles["Left"])
    p3_2 = Paragraph(f'{NOMBRE_PROVEEDOR}', styles["Left"])
    p3_3 = Paragraph(f'{RUC_PROVEEDOR}', styles["Left"])

    TELEFONO = f'987654321'
    DIRECCION = f'JR. PALMERAS-STA. ASUNCION MZA. I5 LOTE 10 FRENTE A LA PLAZA DE SANTA ASUNCION PUNO-SAN ROMAN-JULIACA'
    p3_4 = Paragraph(f'ENVIAR A:', styles["Left"])
    p3_5 = Paragraph(f'INDUSTRIAS ANDERQUIN EIRL', styles["Left"])
    p3_6 = Paragraph(f'Telf.: {TELEFONO}', styles["Left"])
    p3_7 = Paragraph(f'{DIRECCION}', styles["Left"])

    colwiths_table_3 = [_wt * 49 / 100, _wt * 2 / 100, _wt * 49 / 100]
    rowwiths_table_3 = [inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5, inch * 1]
    ana_c3 = Table(
        [(p3_1, '', p3_4)] +
        [(p3_2, '', p3_5)] +
        [(p3_3, '', '')] +
        [('', '', p3_6)] +
        [('', '', p3_7)],
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
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_GREEN),
        ('VALIGN', (0, 0), (-1, 0), 'CENTER'),
    ]

    p4_1 = Paragraph(f'N°', styles["Left"])
    p4_2 = Paragraph(f'COD', styles["Left"])
    p4_3 = Paragraph(f'DESCRIPCION', styles["Left"])
    p4_4 = Paragraph(f'UM', styles["Left"])
    p4_5 = Paragraph(f'P/Und', styles["Left"])
    p4_6 = Paragraph(f'UNIDADES', styles["Left"])
    p4_7 = Paragraph(f'PRECIO UNIDAD', styles["Left"])
    p4_8 = Paragraph(f'SUB TOTAL', styles["Right"])

    colwiths_table_4 = [_wt * 3 / 100, _wt * 9 / 100, _wt * 40 / 100, _wt * 8 / 100, _wt * 10 / 100, _wt * 10 / 100,
                        _wt * 10 / 100, _wt * 10 / 100]
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
    for i in purchase_detail.all():
        style_table_5 = [
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            # ('BACKGROUND', (0, 0), (-1, -1), COLOR_GREEN),
        ]

        product = i.product

        num = f'{contador}'
        contador += 1
        cod = f'{product.code}'
        descripcion = f'{product.name}'
        um = f'{i.unit.name}'
        p_und = f'{round(i.price_unit, 2)}'
        unidades = f'{i.quantity}'
        precio_unidad = f'{round(i.price_unit, 2)}'
        sub_total = round(i.multiplicate(), 2)

        total += sub_total

        p5_1 = Paragraph(num, styles["Left"])
        p5_2 = Paragraph(cod, styles["Left"])
        p5_3 = Paragraph(descripcion, styles["Left"])
        p5_4 = Paragraph(um, styles["Left"])
        p5_5 = Paragraph(f'--', styles["Left"])
        p5_6 = Paragraph(f'{unidades}', styles["Left"])
        p5_7 = Paragraph(f'{precio_unidad}', styles["Left"])
        p5_8 = Paragraph(f'{sub_total}', styles["Right"])

        colwiths_table_5 = [_wt * 3 / 100, _wt * 9 / 100, _wt * 40 / 100, _wt * 8 / 100, _wt * 10 / 100,
                            _wt * 10 / 100, _wt * 10 / 100, _wt * 10 / 100]
        rowwiths_table_5 = [inch * 0.5]
        ana_c5 = Table(
            [(p5_1, p5_2, p5_3, p5_4, p5_5, p5_6, p5_7, p5_8)],
            colWidths=colwiths_table_5, rowHeights=rowwiths_table_5)
        ana_c5.setStyle(TableStyle(style_table_5))

        _dictionary.append(ana_c5)

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #
    style_table_6 = [
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        # ('BACKGROUND', (0, 0), (-1, -1), COLOR_GREEN),
    ]

    p6_1 = Paragraph(f'TOTAL: S/. {total}', styles["Right"])

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
        ('BOX', (0, 0), (-1, 3), 2, colors.black),
        ('BOX', (0, 4), (-1, -1), 2, colors.black),
        ('BOX', (-1, -4), (-1, -1), 2, colors.black),
        ('BOX', (0, 0), (0, -1), 2, colors.black),

        ('SPAN', (-1, 0), (-1, 3)),
        ('SPAN', (-1, 0), (-1, 3)),
        ('SPAN', (1, 4), (1, 5)),
    ]
    entrega = purchase_obj.delivery
    p7_1 = Paragraph(f'FACTURAR A', styles["Left"])
    p7_2 = Paragraph(f'INDUSTRIAS ANDERQUIN EIRL', styles["Left"])
    p7_3 = Paragraph(f'RUC: 20604193053', styles["Left"])
    p7_4 = Paragraph(f'JR. CARABAYA NRO. 443 (AL FRENTE DE LA PLAZA MANCO CAPAC) PUNO - SAN ROMAN - JULIACA',
                     styles["Left"])
    p7_5 = Paragraph(f'Juliaca, San Roman, Puno', styles["Left"])

    p7_6 = Paragraph(f'ENTREGA', styles["Left"])
    p7_7 = Paragraph(f'{entrega}', styles["Left"])

    colwiths_table_7 = [_wt * 15 / 100, _wt * 70 / 100, _wt * 15 / 100]
    rowwiths_table_7 = [inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5]
    ana_c7 = Table(
        [(p7_1, p7_2, '')] +
        [('', p7_3, '')] +
        [('', p7_4, '')] +
        [('', p7_5, '')] +
        [(p7_6, p7_7, '')] +
        [('', '', '')] +
        [('', '', '')] +
        [('', '', '')],
        colWidths=colwiths_table_7, rowHeights=rowwiths_table_7)
    ana_c7.setStyle(TableStyle(style_table_7))

    _dictionary.append(Spacer(width=8, height=16))
    _dictionary.append(ana_c7)

    # **************************************************************************************************************** #
    # ********************* if ********************* #
    # **************************************************************************************************************** #
    if purchase_obj.supplier.is_type_reference:
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
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            # ('BOX', (0, 4), (-1, -1), 2, colors.black),
            # ('BOX', (-1, -4), (-1, -1), 2, colors.black),
            # ('BOX', (0, 0), (0, -1), 2, colors.black),

            # ('SPAN', (-1, 0), (-1, 3)),
            # ('SPAN', (-1, 0), (-1, 3)),
            # ('SPAN', (1, 4), (1, 5)),

        ]

        reference_obj = purchase_obj.sales_reference

        p9_1 = Paragraph(f'Razón Social: ', styles["Right"])
        p9_2 = Paragraph(f'{reference_obj.business_name}', styles["Left"])
        p9_3 = Paragraph(f'RUC: ', styles["Right"])
        p9_4 = Paragraph(f'{reference_obj.ruc}', styles["Left"])
        p9_5 = Paragraph(f'Dirección: ', styles["Right"])
        p9_6 = Paragraph(f'{reference_obj.address}', styles["Left"])
        p9_7 = Paragraph(f'Referencia: ', styles["Right"])
        p9_8 = Paragraph(f'{reference_obj.reference}', styles["Left"])

        colwiths_table_9 = [_wt * 14 / 100, _wt * 2 / 100, _wt * 84 / 100]
        rowwiths_table_9 = [inch * 0.5, inch * 0.5, inch * 0.5, inch * 0.5]
        ana_c9 = Table(
            [(p9_1, '', p9_2)] +
            [(p9_3, '', p9_4)] +
            [(p9_5, '', p9_6)] +
            [(p9_7, '', p9_8)],
            colWidths=colwiths_table_9, rowHeights=rowwiths_table_9)
        ana_c9.setStyle(TableStyle(style_table_9))

        _dictionary.append(Spacer(width=8, height=16))
        _dictionary.append(ana_c9)

        # **************************************************************************************************************** #
        # **************************************************************************************************************** #

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
            # ('BOX', (0, 4), (-1, -1), 2, colors.black),
            # ('BOX', (-1, -4), (-1, -1), 2, colors.black),
            # ('BOX', (0, 0), (0, -1), 2, colors.black),

            # ('SPAN', (-1, 0), (-1, 3)),
            # ('SPAN', (-1, 0), (-1, 3)),
            # ('SPAN', (1, 4), (1, 5)),

        ]

        reference_entity_obj = purchase_obj.sales_reference_entity

        p11_1 = Paragraph(f'Razón Social: ', styles["Right"])
        p11_2 = Paragraph(f'{reference_entity_obj.business_name}', styles["Left"])
        p11_3 = Paragraph(f'RUC: ', styles["Right"])
        p11_4 = Paragraph(f'{reference_entity_obj.ruc}', styles["Left"])
        p11_5 = Paragraph(f'Dirección: ', styles["Right"])
        p11_6 = Paragraph(f'{reference_entity_obj.address}', styles["Left"])
        # p10_6 = Paragraph(f'Referencia: ', styles["Right"])

        colwiths_table_11 = [_wt * 14 / 100, _wt * 2 / 100, _wt * 84 / 100]
        rowwiths_table_11 = [inch * 0.5, inch * 0.5, inch * 0.5]
        ana_c11 = Table(
            [(p11_1, '', p11_2)] +
            [(p11_3, '', p11_4)] +
            [(p11_5, '', p11_6)],
            colWidths=colwiths_table_11, rowHeights=rowwiths_table_11)
        ana_c11.setStyle(TableStyle(style_table_11))

        _dictionary.append(Spacer(width=8, height=16))
        _dictionary.append(ana_c11)

        # **************************************************************************************************************** #
        # ********************* endif ********************* #
        # **************************************************************************************************************** #

    # **************************************************************************************************************** #
    # **************************************************************************************************************** #

    style_table_12 = [
        # ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]

    usuario = request.user
    p12_1 = Paragraph(f'Usuario {usuario} - {datetime.now()}', styles["Left-Simple"])

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
                            title='TICKET'
                            )
    doc.build(_dictionary)
    # doc.build(elements)
    # doc.build(Story)
    #
    # response = HttpResponse(content_type='application/pdf')
    # response['Content-Disposition'] = 'attachment; filename="{}-{}.pdf"'.format(order_obj.nombres, order_obj.pagos.id)
    #

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="[{}].pdf"'.format(ORDEN_COMPRA + '-' + str(637))

    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=0, minute=0, second=0)
    expires = datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")

    response.set_cookie('bp', value=pk, expires=expires)

    response.write(buff.getvalue())

    buff.close()
    return response
