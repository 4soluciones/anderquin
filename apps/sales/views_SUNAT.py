# from django.contrib.sites import requests
import requests
from django.http import JsonResponse
from http import HTTPStatus
from .models import *
import math
from apps.hrm.models import Department, Province
from django.contrib.auth.models import User
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime
from django.db import DatabaseError, IntegrityError
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from .number_to_letters import numero_a_moneda
from apps.comercial.models import DistributionMobil, Truck
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import time


def send_bill(order_id):
    order_obj = Order.objects.get(id=int(order_id))
    details = OrderDetail.objects.filter(order=order_obj)
    client_obj = order_obj.client
    client_first_address = client_obj.clientaddress_set.first()
    client_document = client_obj.clienttype_set.filter(document_type_id='06').first()
    client_department = Department.objects.get(id=client_first_address.district[:2])
    register_date = datetime.now()
    formatdate = register_date.strftime("%Y-%m-%d")

    items = []
    index = 1
    sub_total = 0
    total = 0
    igv_total = 0
    for d in details:
        base_total = round(d.quantity_sold * d.price_unit)  # 5 * 20 = 100
        base_amount = round((base_total / 1.18), 2)  # 100 / 1.18 = 84.75
        igv = round((base_total - base_amount), 2)  # 100 - 84.75 = 15.25
        sub_total = round((sub_total + base_amount), 2)
        total = total + base_total
        igv_total = igv_total + igv
        # redondear a un decimal
        item = {
            "ITEM": index,
            "UNIDAD_MEDIDA": d.unit.name,
            "CANTIDAD": d.quantity_sold,
            "PRECIO": float(d.price_unit),
            "IMPORTE": base_total,
            "PRECIO_TIPO_CODIGO": "01",  # 01--TABLA SUNAT = APLICA IGV
            "IGV": igv,
            "ISC": 0.0,
            "COD_TIPO_OPERACION": "10",  # 10--OPERACION ONEROSA
            "CODIGO": d.product.code,
            "DESCRIPCION": d.product.name,
            "PRECIO_SIN_IMPUESTO": float(d.price_unit)

        }
        items.append(item)
        index = index + 1

    params = {
        "TIPO_OPERACION": "",
        "TOTAL_GRAVADAS": sub_total,
        "TOTAL_INAFECTA": 0.0,
        "TOTAL_EXONERADAS": 0.0,
        "TOTAL_GRATUITAS": 0.0,
        "TOTAL_PERCEPCIONES": 0.0,
        "TOTAL_RETENCIONES": 0.0,
        "TOTAL_DETRACCIONES": 0.0,
        "TOTAL_BONIFICACIONES": 0.0,
        "TOTAL_DESCUENTO": 0.0,
        "SUB_TOTAL": sub_total,
        "POR_IGV": 0.0,
        "TOTAL_IGV": igv_total,
        "TOTAL_ISC": 0.0,
        "TOTAL_EXPORTACION": 0.0,
        "TOTAL_OTR_IMP": 0.0,
        "TOTAL": total,
        "TOTAL_LETRAS": numero_a_moneda(total),
        "NRO_COMPROBANTE": "F001-0010",
        "FECHA_DOCUMENTO": formatdate,
        "COD_TIPO_DOCUMENTO": "01",  # 01=FACTURA, 03=BOLETA, 07=NOTA CREDITO, 08=NOTA DEBITO
        "COD_MONEDA": "PEN",
        "NRO_DOCUMENTO_CLIENTE": client_document.document_number,
        "RAZON_SOCIAL_CLIENTE": client_obj.names,
        "TIPO_DOCUMENTO_CLIENTE": "6",  # 1=DNI,6=RUC
        "DIRECCION_CLIENTE": client_first_address.address,
        "CIUDAD_CLIENTE": client_department,
        "COD_PAIS_CLIENTE": "PE",
        "NRO_DOCUMENTO_EMPRESA": "20434893217",
        "TIPO_DOCUMENTO_EMPRESA": "6",
        "NOMBRE_COMERCIAL_EMPRESA": "METALNOX EDMA S.R.L.",
        "CODIGO_UBIGEO_EMPRESA": "040112",
        "DIRECCION_EMPRESA": "VILLA JESUS MZA. E LOTE. 6 (FRENTE POSTA VILLA MEDICA VILLA JESUS)",
        "DEPARTAMENTO_EMPRESA": "AREQUIPA",
        "PROVINCIA_EMPRESA": "AREQUIPA",
        "DISTRITO_EMPRESA": "PAUCARPATA",
        "CODIGO_PAIS_EMPRESA": "PE",
        "RAZON_SOCIAL_EMPRESA": "METALNOX EDMA SOCIEDAD COMERCIAL DE RESPONSABILIDAD LIMITADA - METALNOX EDMA S.R.L.",
        "USUARIO_SOL_EMPRESA": "METALNOX",
        "PASS_SOL_EMPRESA": "Metalnox1",
        "CONTRA": "123456.",
        "TIPO_PROCESO": "3",
        "FLG_ANTICIPO": "0",
        "FLG_REGU_ANTICIPO": "0",
        "MONTO_REGU_ANTICIPO": "0",
        "PASS_FIRMA": "Ax123456789",
        "Detalle": items
    }

    url = 'http://www.facturacioncloud.com/cpesunatUBL21/CpeServlet?accion=WSSunatCPE_V2'
    headers = {'content-type': 'application/json'}
    response = requests.post(url, json=params, headers=headers)

    if response.status_code == 200:
        result = response.json()

        context = {
            'message': result.get("des_msj_sunat"),
            'params': params
        }
        return context


def query_dni(self):
    url = 'https://www.facturacionelectronica.us/facturacion/controller/ws_consulta_rucdni_v2.php'
    params = {
        'usuario': '20498189637',
        'password': 'marvisur.123.',
        'documento': 'DNI',
        'nro_documento': '40395588'
    }
    r = requests.get(url, params)

    if r.status_code == 200:
        result = r.json()
        # return result.get('statusMessage')
        return JsonResponse({
            'success': result.get('success'),
            'statusMessage': result.get('statusMessage'),
            'result': result.get('result'),
            'DNI': result.get('result').get('DNI'),
            'Nombre': result.get('result').get('Nombre')
        })


# SEND_BILL_NUBEFACT

def send_bill_nubefact(order_id, is_demo=False):
    global total_perceptron, total_with_perceptron
    order_obj = Order.objects.get(id=int(order_id))
    truck_obj = order_obj.truck
    truck_id = truck_obj.id
    serie = order_obj.truck.serial
    n_receipt = get_correlative(truck_id, '1')
    details = OrderDetail.objects.filter(order=order_obj)
    client_obj = order_obj.client
    client_first_address = client_obj.clientaddress_set.first()
    client_document = client_obj.clienttype_set.filter(document_type_id='06').first()
    # client_department = Dep/artment.objects.get(id=client_first_address.district[:2])
    register_date = order_obj.create_at
    formatdate = register_date.strftime("%d-%m-%Y")

    items = []
    index = 1
    sub_total = 0
    total = 0
    igv_total = 0
    for d in details:
        base_total = d.quantity_sold * d.price_unit  # 5 * 20 = 100
        value_unit = float(d.price_unit / decimal.Decimal(1.1800))
        base_amount = value_unit * float(d.quantity_sold)  # 100 / 1.18 = 84.75
        igv = float(base_total) - float(base_amount)  # 100 - 84.75 = 15.25
        sub_total = sub_total + base_amount
        total = total + base_total
        igv_total = igv_total + igv
        total_perceptron = (total * 2) / 100
        total_with_perceptron = total + total_perceptron

        # redondear a un decimal
        item = {
            "item": index,  # index para los detalles
            "unidad_de_medida": 'NIU',  # NIU viene del nubefact NIU=PRODUCTO
            "codigo": "001",  # codigo del producto opcional
            "codigo_producto_sunat": "10000000",  # codigo del producto excel-sunat
            "descripcion": d.product.name,
            "cantidad": float(round(d.quantity_sold)),
            "valor_unitario": value_unit,  # valor unitario sin IGV
            "precio_unitario": float(d.price_unit),
            "descuento": "",
            "subtotal": float(base_amount),  # resultado del valor unitario por la cantidad menos el descuento
            "tipo_de_igv": 1,  # operacion onerosa
            "igv": float(igv),
            "total": float(base_total),
            "anticipo_regularizacion": 'false',
            "anticipo_documento_serie": "",
            "anticipo_documento_numero": "",
        }
        items.append(item)
        index = index + 1

    params = {
        "operacion": "generar_comprobante",
        "tipo_de_comprobante": 1,
        "serie": 'F' + serie[:3],
        "numero": n_receipt,
        "sunat_transaction": 15,
        # "sunat_transaction": 1,
        "cliente_tipo_de_documento": 6,
        "cliente_numero_de_documento": client_document.document_number,
        "cliente_denominacion": client_obj.names,
        "cliente_direccion": client_first_address.address,
        "cliente_email": client_obj.email,
        "cliente_email_1": "",
        "cliente_email_2": "",
        "fecha_de_emision": formatdate,
        "fecha_de_vencimiento": "",
        "moneda": 1,

        "descuento_global": "",
        "total_descuento": "",
        "total_anticipo": "",
        "total_gravada": float(sub_total),
        "total_inafecta": "",
        "total_exonerada": "",
        "total_igv": float(igv_total),
        "total_gratuita": "",
        "total_otros_cargos": "",
        "total": float(total),
        "percepcion_tipo": 1,
        "percepcion_base_imponible": float(total),
        "total_percepcion": float(total_perceptron),
        "total_incluido_percepcion": float(total_with_perceptron),
        #
        # "percepcion_tipo": "",
        # "percepcion_base_imponible": "",
        # "total_percepcion": "",
        # "total_incluido_percepcion": "",

        "total_impuestos_bolsas": "",
        "detraccion": 'false',
        "observaciones": "",
        "documento_que_se_modifica_tipo": "",
        "documento_que_se_modifica_serie": "",
        "documento_que_se_modifica_numero": "",
        "tipo_de_nota_de_credito": "",
        "tipo_de_nota_de_debito": "",
        "enviar_automaticamente_a_la_sunat": 'true',
        "enviar_automaticamente_al_cliente": 'false',
        "condiciones_de_pago": "",
        "medio_de_pago": "",
        "placa_vehiculo": "",
        "orden_compra_servicio": "",
        "formato_de_pdf": "",
        "generado_por_contingencia": "",
        "bienes_region_selva": "",
        "servicios_region_selva": "",
        "items": items,
    }
    # if is_demo:
    #     _url = 'https://www.pse.pe/api/v1/91900d0da6424013b4cf9a8c4fdf8846b67addc7bbcb41328e137a9c93479e26'
    #     _authorization = 'eyJhbGciOiJIUzI1NiJ9.IjY1NTJmNDE1NGZhOTQ5ZGU4MjFjYTIwYmE4ZWM4ZDg1MzAxMDRlZmNlNGNjNDcyMGI0ZDU2MGE5ZGQwOGNhMmQi.GNzvsfMsCITQ-xwfK-yl_TQwcLd4F-264wYK19frMXE'
    # else:
    _url = 'https://www.pse.pe/api/v1/cb5a9c35389844faa6368c0ffd4bdeb075e3c1dc4b564813ac1d5f8aba523921'
    _authorization = 'eyJhbGciOiJIUzI1NiJ9.IjQzZmJiZWQ0ZjNmNDQ3M2E5NjEyY2U1ZjVlODk0YzQxMGU3YWM1OTRjZGFiNGU5ODhjNDdlMmE2NDljN2ZkOGMi.FQyoaAcuUyGUelMLI_ttscd3GI_4XyOoMiomAgTmoDQ'

    url = _url
    headers = {
        "Authorization": _authorization,
        "Content-Type": 'application/json'
    }
    response = requests.post(url, json=params, headers=headers)

    if response.status_code == 200:
        result = response.json()

        context = {
            'tipo_de_comprobante': result.get("tipo_de_comprobante"),
            'serie': result.get("serie"),
            'numero': result.get("numero"),
            'aceptada_por_sunat': result.get("aceptada_por_sunat"),
            'sunat_description': result.get("sunat_description"),
            'enlace_del_pdf': result.get("enlace_del_pdf"),
            'cadena_para_codigo_qr': result.get("cadena_para_codigo_qr"),
            'codigo_hash': result.get("codigo_hash"),
            'params': params
        }
    else:
        result = response.json()
        context = {
            'errors': result.get("errors"),
            'codigo': result.get("codigo"),
        }
    return context


def send_receipt_nubefact(order_id, is_demo=False):
    order_obj = Order.objects.get(id=int(order_id))
    truck_obj = order_obj.truck
    truck_id = truck_obj.id
    serie = order_obj.truck.serial
    n_receipt = get_correlative(truck_id, '2')
    details = OrderDetail.objects.filter(order=order_obj)
    client_obj = order_obj.client
    client_first_address = ""
    if client_obj.clientaddress_set.first():
        client_first_address = client_obj.clientaddress_set.first().address
    client_document = client_obj.clienttype_set.filter(document_type_id='01').first()
    # client_department = Department.objects.get(id=client_first_address.district[:2])
    register_date = order_obj.create_at
    formatdate = register_date.strftime("%d-%m-%Y")

    items = []
    index = 1
    sub_total = 0
    total = 0
    igv_total = 0
    for d in details:
        base_total = d.quantity_sold * d.price_unit  # 5 * 20 = 100
        base_amount = base_total / decimal.Decimal(1.1800)  # 100 / 1.18 = 84.75
        igv = base_total - base_amount  # 100 - 84.75 = 15.25
        sub_total = sub_total + base_amount
        total = total + base_total
        igv_total = igv_total + igv

        # redondear a un decimal
        item = {
            "item": index,  # index para los detalles
            "unidad_de_medida": 'NIU',  # NIU viene del nubefact NIU=PRODUCTO
            "codigo": "001",  # codigo del producto opcional
            "codigo_producto_sunat": "10000000",  # codigo del producto excel-sunat
            "descripcion": d.product.name,
            "cantidad": float(round(d.quantity_sold)),
            "valor_unitario": float(round((base_amount / d.quantity_sold), 2)),  # valor unitario sin IGV
            "precio_unitario": float(round(d.price_unit, 2)),
            "descuento": "",
            "subtotal": float(round(base_amount, 2)),  # resultado del valor unitario por la cantidad menos el descuento
            "tipo_de_igv": 1,  # operacion onerosa
            "igv": float(round(igv, 2)),
            "total": float(round(base_total, 2)),
            "anticipo_regularizacion": 'false',
            "anticipo_documento_serie": "",
            "anticipo_documento_numero": "",
        }
        items.append(item)
        index = index + 1

    params = {
        "operacion": "generar_comprobante",
        "tipo_de_comprobante": 2,
        "serie": 'B' + serie[:3],
        "numero": n_receipt,
        "sunat_transaction": 1,
        "cliente_tipo_de_documento": 1,  # cambiar cuando este bien
        "cliente_numero_de_documento": client_document.document_number,
        "cliente_denominacion": client_obj.names,
        "cliente_direccion": client_first_address,
        "cliente_email": client_obj.email,
        "cliente_email_1": "",
        "cliente_email_2": "",
        "fecha_de_emision": formatdate,
        "fecha_de_vencimiento": "",
        "moneda": 1,
        "tipo_de_cambio": "",
        "porcentaje_de_igv": 18.00,
        "descuento_global": "",
        "total_descuento": "",
        "total_anticipo": "",
        "total_gravada": float(round(sub_total, 2)),
        "total_inafecta": "",
        "total_exonerada": "",
        "total_igv": float(round(igv_total, 2)),
        "total_gratuita": "",
        "total_otros_cargos": "",
        "total": float(round(total, 2)),
        "percepcion_tipo": "",
        "percepcion_base_imponible": "",
        "total_percepcion": "",
        "total_incluido_percepcion": "",
        "total_impuestos_bolsas": "",
        "detraccion": 'false',
        "observaciones": "",
        "documento_que_se_modifica_tipo": "",
        "documento_que_se_modifica_serie": "",
        "documento_que_se_modifica_numero": "",
        "tipo_de_nota_de_credito": "",
        "tipo_de_nota_de_debito": "",
        "enviar_automaticamente_a_la_sunat": 'true',
        "enviar_automaticamente_al_cliente": 'false',
        "codigo_unico": "",
        "condiciones_de_pago": "",
        "medio_de_pago": "",
        "placa_vehiculo": "",
        "orden_compra_servicio": "",
        "tabla_personalizada_codigo": "",
        "formato_de_pdf": "",
        "items": items,
    }

    # if is_demo:
    #     _url = 'https://www.pse.pe/api/v1/91900d0da6424013b4cf9a8c4fdf8846b67addc7bbcb41328e137a9c93479e26'
    #     _authorization = 'eyJhbGciOiJIUzI1NiJ9.IjY1NTJmNDE1NGZhOTQ5ZGU4MjFjYTIwYmE4ZWM4ZDg1MzAxMDRlZmNlNGNjNDcyMGI0ZDU2MGE5ZGQwOGNhMmQi.GNzvsfMsCITQ-xwfK-yl_TQwcLd4F-264wYK19frMXE'
    # else:
    _url = 'https://www.pse.pe/api/v1/cb5a9c35389844faa6368c0ffd4bdeb075e3c1dc4b564813ac1d5f8aba523921'
    _authorization = 'eyJhbGciOiJIUzI1NiJ9.IjQzZmJiZWQ0ZjNmNDQ3M2E5NjEyY2U1ZjVlODk0YzQxMGU3YWM1OTRjZGFiNGU5ODhjNDdlMmE2NDljN2ZkOGMi.FQyoaAcuUyGUelMLI_ttscd3GI_4XyOoMiomAgTmoDQ'

    url = _url
    headers = {
        "Authorization": _authorization,
        "Content-Type": 'application/json'
    }
    context = 'Max retries exceeded'
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            response = requests.post(url, json=params, headers=headers)

            if response.status_code == 200:
                result = response.json()

                context = {
                    'tipo_de_comprobante': result.get("tipo_de_comprobante"),
                    'serie': result.get("serie"),
                    'numero': result.get("numero"),
                    'aceptada_por_sunat': result.get("aceptada_por_sunat"),
                    'sunat_description': result.get("sunat_description"),
                    'enlace_del_pdf': result.get("enlace_del_pdf"),
                    'cadena_para_codigo_qr': result.get("cadena_para_codigo_qr"),
                    'codigo_hash': result.get("codigo_hash"),
                    'params': params
                }
            else:
                # print("response", response)
                # print("result", result)
                result = response.json()
                context = {
                    'errors': result.get("errors"),
                    'codigo': result.get("codigo"),
                }
            break
        except requests.exceptions.RequestException as e:
            retry_count += 1
            if retry_count == max_retries:
                raise Exception("Max retries exceeded")
            time.sleep(2)
    return context

    # try:
    #     response = requests.post(url, json=params, headers=headers, timeout=5)
    #     # print("response", response)
    #     if response.status_code == 200:
    #         result = response.json()
    #
    #         context = {
    #             'tipo_de_comprobante': result.get("tipo_de_comprobante"),
    #             'serie': result.get("serie"),
    #             'numero': result.get("numero"),
    #             'aceptada_por_sunat': result.get("aceptada_por_sunat"),
    #             'sunat_description': result.get("sunat_description"),
    #             'enlace_del_pdf': result.get("enlace_del_pdf"),
    #             'cadena_para_codigo_qr': result.get("cadena_para_codigo_qr"),
    #             'codigo_hash': result.get("codigo_hash"),
    #             'params': params
    #         }
    #     else:
    #         # print("response", response)
    #         # print("result", result)
    #         result = response.json()
    #         context = {
    #             'errors': result.get("errors"),
    #             'codigo': result.get("codigo"),
    #         }
    #
    # except requests.ReadTimeout:
    #     print("READ NUBEFACT")
    #     time.sleep(5)
    #     context = {
    #         'errors': True
    #     }

    # return context


def get_correlative(truck_id, type):
    truck_obj = Truck.objects.get(id=truck_id)
    if type == '1':
        serie = 'F' + truck_obj.serial[:3]
    else:
        serie = 'B' + truck_obj.serial[:3]

    order_bill_set = OrderBill.objects.filter(serial=serie, type=type)
    if order_bill_set:
        n_receipt = order_bill_set.last().n_receipt
        new_n_receipt = n_receipt + 1
        return new_n_receipt
    else:
        return 1
