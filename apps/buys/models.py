import decimal

from django.db import models
from django.contrib.auth.models import User

from apps import accounting, sales, hrm
from apps.hrm.models import Subsidiary, District, DocumentType
from apps.sales.models import Unit, Product, Supplier, SubsidiaryStore, LoanPayment, City
from apps.comercial.models import Truck


class MoneyChange(models.Model):
    id = models.AutoField(primary_key=True)
    search_date = models.DateField('Fecha de busqueda', null=True, blank=True, unique=True)
    sunat_date = models.DateField('Fecha de sunat', null=True, blank=True, unique=True)
    sell = models.DecimalField('Venta', max_digits=10, decimal_places=4, default=0)
    buy = models.DecimalField('Compra', max_digits=10, decimal_places=4, default=0)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Cambio de Moneda'
        verbose_name_plural = 'Cambio de Monedas'


class Purchase(models.Model):
    BILL_CHOICES = (('S', 'SIN FACTURA'), ('I', 'INCOMPLETO'), ('C', 'CON FACTURA'), ('A', 'ANULADO'),)
    STATUS_CHOICES = (('S', 'SIN ALMACEN'), ('A', 'EN ALMACEN'), ('N', 'ANULADO'),)
    DELIVERY_CHOICES = (('S', 'SUCURSAL'), ('P', 'PROVIDER'), ('CR', 'CLIENTE REFERENCIA'), ('CP', 'CLIENTE ENTIDAD'))
    # TYPE_CHOICES = (('T', 'TICKET'), ('B', 'BOLETA'), ('F', 'FACTURA'),)
    CURRENCY_TYPE_CHOICES = (('S', 'SOL'), ('D', 'DOLAR'),)
    PAYMENT_METHOD_CHOICES = (('CO', 'CONTADO'), ('CR', 'CREDITO'),)
    id = models.AutoField(primary_key=True)
    supplier = models.ForeignKey(Supplier, verbose_name='Proveedor', on_delete=models.CASCADE, null=True, blank=True)
    purchase_date = models.DateField('Fecha compra', null=True, blank=True)
    bill_number = models.CharField(max_length=100, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE, null=True, blank=True)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='S')
    # type_bill = models.CharField('Tipo de comprobante', max_length=1, choices=TYPE_CHOICES, default='T')
    delivery_choice = models.CharField('Entrega a', max_length=2, choices=DELIVERY_CHOICES, default='S')
    currency_type = models.CharField('Tipo de moneda', max_length=1, choices=CURRENCY_TYPE_CHOICES, default='S')
    client_reference = models.ForeignKey('sales.Client', verbose_name='Cliente de venta', on_delete=models.CASCADE,
                                         null=True, blank=True)
    client_reference_entity = models.ForeignKey('sales.Client', verbose_name='Cliente de entidad',
                                                on_delete=models.CASCADE,
                                                null=True, blank=True, related_name='client_entity')
    payment_method = models.CharField('Método de Pago', max_length=2, choices=PAYMENT_METHOD_CHOICES, default='CO')
    payment_condition = models.CharField('Condicion de Pago', max_length=255, null=True, blank=True)
    delivery_address = models.CharField('Direccion de envio', max_length=200, null=True, blank=True)
    city = models.CharField('Ciudad', max_length=200, null=True, blank=True)
    observation = models.TextField('Observación', blank=True, null=True)
    # contract_detail = models.ForeignKey('buys.ContractDetail', on_delete=models.CASCADE, null=True, blank=True)
    delivery_date = models.DateField('Fecha de entrega', null=True, blank=True)
    correlative = models.IntegerField('Correlativo', null=True, blank=True)
    reference = models.CharField('Referencia', max_length=100, blank=True, null=True)
    check_igv = models.BooleanField('Habilitado IGV', default=True)
    delivery_subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='delivery_subsidiary')
    delivery_supplier = models.ForeignKey('sales.SupplierAddress', on_delete=models.CASCADE, null=True, blank=True)
    delivery_client = models.ForeignKey('sales.ClientAddress', on_delete=models.CASCADE, null=True, blank=True)
    batch_number = models.CharField('Numero de Lote', max_length=50, null=True, blank=True)
    batch_expiration_date = models.DateField('Fecha de expiracion de lote', null=True, blank=True)
    guide_number = models.CharField('Numero de Guia', max_length=50, null=True, blank=True)
    assign_date = models.DateField('Fecha de Ingreso a Almacen', null=True, blank=True)
    year = models.IntegerField('Year', null=True, blank=True)
    bill_status = models.CharField('Estado Factura', max_length=1, choices=BILL_CHOICES, default='S')
    parent_purchase = models.ForeignKey('Purchase', on_delete=models.SET_NULL, null=True, blank=True)
    store_destiny = models.ForeignKey(SubsidiaryStore, on_delete=models.SET_NULL, null=True, blank=True)
    is_simple_buy = models.BooleanField(default=False)

    # delivery_client_final = models.ForeignKey('sales.Client', on_delete=models.CASCADE, null=True, blank=True,
    #                                           related_name='delivery_client_final')

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    def get_currency_type(self):
        currency_set = {
            'S': 'SOL',
            'D': 'DOLAR'
        }
        return currency_set[self.currency_type]

    def get_payment_method(self):
        payment_method_set = {
            'CO': 'CONTADO',
            'CR': 'CRÉDITO'
        }
        return payment_method_set[self.payment_method]

    def total(self):
        response = 0
        purchase_detail_set = PurchaseDetail.objects.filter(purchase__id=self.id)
        for pd in purchase_detail_set:
            response = response + (pd.quantity * pd.price_unit)
        return round(response, 4)

    def base_total_purchase(self):
        response = 0
        purchase_detail_set = PurchaseDetail.objects.filter(purchase__id=self.id)
        for pd in purchase_detail_set:
            response = response + (pd.quantity * pd.price_unit)
        base_total = round(response / decimal.Decimal(1.18), 4)
        return round(base_total, 4)

    def igv_total_purchase(self):
        response = 0
        purchase_detail_set = PurchaseDetail.objects.filter(purchase__id=self.id)
        for pd in purchase_detail_set:
            response = response + (pd.quantity * pd.price_unit)
        base_total = round(response / decimal.Decimal(1.18), 4)
        igv = response - base_total
        return round(igv, 4)

    def number_bill(self):
        from apps.accounting.models import BillPurchase
        response = '-'
        purchase_detail_get = PurchaseDetail.objects.filter(purchase__id=self.id).first()
        bill_purchase_set = BillPurchase.objects.filter(purchase_detail=purchase_detail_get)
        if bill_purchase_set.exists():
            response = bill_purchase_set.first().bill.serial + '-' + bill_purchase_set.first().bill.correlative
        return response

    def get_quantity_refund(self):
        response = False
        # purchase_obj = Purchase.objects.get(parent_purchase_id=self.id)
        purchase_detail_set = PurchaseDetail.objects.filter(purchase__parent_purchase__id=self.id)
        if purchase_detail_set.exists():
            for p in purchase_detail_set:
                if p.status_quantity == 'D':
                    response = True
        return response


class PurchaseDetail(models.Model):
    STATUS_CHOICES = (('C', 'COMPRADA'), ('I', 'INGRESADA'), ('D', 'DEVUELTA'), ('V', 'VENDIDA'),)
    id = models.AutoField(primary_key=True)
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.DecimalField('Cantidad comprada', max_digits=10, decimal_places=4, default=0)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    price_unit = models.DecimalField('Precio unitario', max_digits=30, decimal_places=6, default=0)
    status_quantity = models.CharField('Estado Cantidad', max_length=1, choices=STATUS_CHOICES, default='C')
    order = models.ForeignKey('sales.Order', on_delete=models.CASCADE, null=True, blank=True)
    client_entity = models.ForeignKey('sales.Client', verbose_name='Cliente de entidad',
                                      on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    def multiplicate(self):
        return self.quantity * self.price_unit

    class Meta:
        verbose_name = 'Detalle compra'
        verbose_name_plural = 'Detalles de compra'


class Contract(models.Model):
    STATUS_CHOICES = (('P', 'PENDIENTE'), ('C', 'COMPLETADO'), ('S', 'SUSPENDIDO'), ('A', 'ANULADO'))
    id = models.AutoField(primary_key=True)
    contract_number = models.CharField('Numero de Contrato', max_length=200, null=True, blank=True)
    client = models.ForeignKey('sales.Client', on_delete=models.CASCADE, null=True, blank=True)
    register_date = models.DateField('Fecha de Registro', null=True, blank=True)
    photo = models.ImageField(upload_to='images/', default='images/images0.jpg', blank=True)
    subsidiary = models.ForeignKey('hrm.Subsidiary', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    observation = models.TextField('Observación', blank=True, null=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.contract_number)

    def sum_quantity_contract_detail(self):
        quantity_total = 0
        contract_detail_set = ContractDetail.objects.filter(contract__id=self.id)
        for cd in contract_detail_set:
            contract_detail_item_set = ContractDetailItem.objects.filter(contract_detail=cd)
            for ci in contract_detail_item_set:
                quantity_total += ci.quantity
        return quantity_total

    def sum_amount_contract_detail(self):
        amount_total = 0
        contract_detail_set = ContractDetail.objects.filter(contract__id=self.id)
        for cd in contract_detail_set:
            contract_detail_item_set = ContractDetailItem.objects.filter(contract_detail=cd)
            for ci in contract_detail_item_set:
                amount_total += ci.amount()
        return amount_total


class ContractDetail(models.Model):
    id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, null=True, blank=True)
    nro_quota = models.CharField('Numero de Quota', max_length=45, null=True, blank=True)
    date = models.DateField('Fecha', null=True, blank=True)
    order = models.ForeignKey('sales.Order', on_delete=models.CASCADE, null=True, blank=True)
    phase_c = models.BooleanField(default=False)
    date_c = models.DateField('Date Phase C', null=True, blank=True)
    phase_d = models.BooleanField(default=False)
    date_d = models.DateField('Date Phase D', null=True, blank=True)
    phase_g = models.BooleanField(default=False)
    date_g = models.DateField('Date Phase G', null=True, blank=True)

    def __str__(self):
        return str(self.id)


class ContractDetailItem(models.Model):
    id = models.AutoField(primary_key=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price_unit = models.DecimalField('Precio unitario', max_digits=30, decimal_places=6, default=0)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    contract_detail = models.ForeignKey(ContractDetail, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.id)
    
    def amount(self):
        return decimal.Decimal(self.quantity) * decimal.Decimal(self.price_unit)


class ContractDetailPurchase(models.Model):
    id = models.AutoField(primary_key=True)
    contract_detail = models.ForeignKey(ContractDetail, on_delete=models.CASCADE, null=True, blank=True)
    purchase = models.ForeignKey(Purchase, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return str(self.id)


class OrderBuy(models.Model):
    TYPE_CHOICES = (('T', 'TICKET'), ('B', 'BOLETA'), ('F', 'FACTURA'),)
    PAYMENT_METHOD_CHOICES = (('CO', 'CONTADO'), ('CR', 'CREDITO'),)
    CURRENCY_TYPE_CHOICES = (('S', 'SOL'), ('D', 'DOLAR'),)
    id = models.AutoField(primary_key=True)
    order_number = models.CharField('Numero de documento', max_length=200, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, verbose_name='Proveedor', on_delete=models.CASCADE, null=True, blank=True)
    payment_method = models.CharField('Método de Pago', max_length=2, choices=PAYMENT_METHOD_CHOICES, default='CO')
    currency_type = models.CharField('Tipo de moneda', max_length=1, choices=CURRENCY_TYPE_CHOICES, default='S')
    order_date = models.DateField('Fecha de Compra', null=True, blank=True)
    issue_date = models.DateField('Fecha de Emision', null=True, blank=True)
    observation = models.TextField('Observación', blank=True, null=True)
    store_destiny = models.ForeignKey('sales.SubsidiaryStore', on_delete=models.SET_NULL, null=True, blank=True)
    subsidiary = models.ForeignKey('hrm.Subsidiary', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.order_number)

    def total(self):
        response = 0
        order_buy_detail_set = OrderBuyDetail.objects.filter(order_buy__id=self.id)
        for pd in order_buy_detail_set:
            response = response + (pd.quantity * pd.price_unit)
        return round(response, 4)


class OrderBuyDetail(models.Model):
    id = models.AutoField(primary_key=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    price_unit = models.DecimalField('Precio unitario', max_digits=30, decimal_places=6, default=0)
    order_buy = models.ForeignKey(OrderBuy, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    def multiply(self):
        return self.quantity * self.price_unit


class CreditNote(models.Model):
    STATUS_CHOICES = (('E', 'EMITIDA'), ('P', 'PENDIENTE'), ('A', 'ANULADA'),)
    id = models.AutoField(primary_key=True)
    credit_note_serial = models.CharField('Serie de documento', max_length=200, null=True, blank=True)
    credit_note_number = models.CharField('Numero de documento', max_length=200, null=True, blank=True)
    issue_date = models.DateField('Fecha de Emision', null=True, blank=True)
    bill = models.ForeignKey('accounting.Bill', on_delete=models.CASCADE, null=True, blank=True)
    purchase = models.ForeignKey(Purchase, on_delete=models.SET_NULL, null=True, blank=True)
    motive = models.TextField('Motive', blank=True, null=True)
    status = models.CharField('Tipo de moneda', max_length=1, choices=STATUS_CHOICES, default='P')
    bill_note = models.ForeignKey('accounting.Bill', related_name='bill_note',
                                  on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.credit_note_serial}-{self.credit_note_number}"

    def get_total(self):
        return sum(item.total for item in self.creditnotedetail_set.all())


class CreditNoteDetail(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField('Codigo', max_length=50, null=True, blank=True)
    description = models.CharField('Description', max_length=200, null=True, blank=True)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    price_unit = models.DecimalField('Precio unitario', max_digits=30, decimal_places=6, default=0)
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE, null=True, blank=True)
    total = models.DecimalField('Total', max_digits=30, decimal_places=6, default=0)

    def __str__(self):
        return str(self.id)

    def multiply(self):
        return self.quantity * self.price_unit


# ============== MÓDULO DE COMPRAS ADMINISTRATIVAS ==============
# Materiales de oficina, limpieza, etc. Sin kardex ni productos del catálogo.


class AdminSupplier(models.Model):
    """Proveedores de materiales administrativos (independiente del modelo Supplier)."""
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre o Razón Social', max_length=200)
    ruc = models.CharField('RUC/DNI', max_length=20, null=True, blank=True)
    address = models.CharField('Dirección', max_length=255, null=True, blank=True)
    phone = models.CharField('Teléfono', max_length=50, null=True, blank=True)
    email = models.EmailField('Email', null=True, blank=True)
    is_enabled = models.BooleanField('Activo', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Proveedor administrativo'
        verbose_name_plural = 'Proveedores administrativos'


class AdministrativePurchase(models.Model):
    """Cabecera de compra de materiales administrativos."""
    CURRENCY_CHOICES = (('S', 'SOL'), ('D', 'DÓLAR'),)
    PAYMENT_CHOICES = (('CO', 'CONTADO'), ('CR', 'CRÉDITO'),)
    id = models.AutoField(primary_key=True)
    purchase_date = models.DateField('Fecha de compra')
    document_number = models.CharField('Nº Documento', max_length=100, null=True, blank=True)
    supplier = models.ForeignKey(AdminSupplier, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name='Proveedor')
    supplier_name_free = models.CharField('Proveedor (otro)', max_length=200, null=True, blank=True,
                                         help_text='Si no está en la lista, escribir aquí')
    currency = models.CharField('Moneda', max_length=1, choices=CURRENCY_CHOICES, default='S')
    payment_method = models.CharField('Método de pago', max_length=2, choices=PAYMENT_CHOICES, default='CO')
    observation = models.TextField('Observación', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Compra #{self.id} - {self.purchase_date}"

    def get_supplier_display(self):
        if self.supplier:
            return self.supplier.name
        return self.supplier_name_free or '-'

    def total(self):
        total = sum(d.subtotal() for d in self.administrativepurchasedetail_set.all())
        return round(total, 2)

    class Meta:
        verbose_name = 'Compra administrativa'
        verbose_name_plural = 'Compras administrativas'


class AdministrativePurchaseDetail(models.Model):
    """Detalle de compra administrativa. Descripción libre, sin Product."""
    id = models.AutoField(primary_key=True)
    purchase = models.ForeignKey(AdministrativePurchase, on_delete=models.CASCADE)
    description = models.CharField('Descripción', max_length=255)
    quantity = models.DecimalField('Cantidad', max_digits=12, decimal_places=4, default=0)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True)
    unit_name_free = models.CharField('Unidad (otra)', max_length=20, null=True, blank=True)
    price_unit = models.DecimalField('Precio unitario', max_digits=14, decimal_places=4, default=0)

    def __str__(self):
        return f"{self.description} x {self.quantity}"

    def subtotal(self):
        return self.quantity * self.price_unit

    def get_unit_display(self):
        if self.unit:
            return self.unit.name
        return self.unit_name_free or '-'

    class Meta:
        verbose_name = 'Detalle compra administrativa'
        verbose_name_plural = 'Detalles compras administrativas'
