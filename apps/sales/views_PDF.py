import reportlab
from django.http import HttpResponse
from reportlab.lib.colors import black, white, gray, red, green, blue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Spacer, tables
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4, A5, C7
from reportlab.lib.units import mm, cm, inch
from reportlab.platypus import Table, Flowable
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import Canvas
# from reportlab.rl_config import defaultPageSize
from functools import partial
from reportlab.lib.colors import PCMYKColor, PCMYKColorSep, Color, black, blue, red, pink, green
from .models import Product, Client, Order, OrderDetail, SubsidiaryStore, ProductStore, Kardex, LoanPayment
from django.contrib.auth.models import User
from apps.hrm.views import get_subsidiary_by_user
from .views import get_context_kardex_glp, get_dict_orders, total_remaining_repay_loan, total_remaining_return_loan, \
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
styles = getSampleStyleSheet()
styleN = styles['Normal']
styleH = styles['Heading1']

styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='CenterTitle2', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=12))
styles.add(ParagraphStyle(name='Center_Regular', alignment=TA_CENTER, leading=8, fontName='Ticketing', fontSize=10))

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


def kardex_glp_pdf(request, pk):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    if request.method == 'GET':
        if pk != '':
            html = get_context_kardex_glp(subsidiary_obj, pk, is_pdf=True)
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

