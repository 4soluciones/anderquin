from django.db import models
from django.contrib.auth.models import User
import decimal

# Create your models here.
from django.db.models import Sum, Count


class TransactionAccount(models.Model):
    DOCUMENT_TYPE_ATTACHED_CHOICES = (
        ('F', 'Factura'), ('B', 'Boleta'), ('T', 'Ticket'), ('V', 'Vale'),
        ('O', 'Otro'))
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)
    product = models.ForeignKey('sales.Product', on_delete=models.SET_NULL, null=True, blank=True)
    order_detail = models.ForeignKey('sales.OrderDetail', on_delete=models.SET_NULL, null=True, blank=True)
    create_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    transaction_date = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    description = models.CharField('Descripcion', max_length=100, null=True, blank=True)
    serial = models.CharField('Serie', max_length=5, null=True, blank=True)
    n_receipt = models.IntegerField('Numero de Comprobante', default=0, null=True, blank=True)
    document_type_attached = models.CharField('Tipo documento', max_length=1, choices=DOCUMENT_TYPE_ATTACHED_CHOICES,
                                              default='O', )

    def __str__(self):
        return str(self.pk)


class AccountingAccount(models.Model):
    code = models.CharField('Codigo', max_length=45, null=True, blank=True)
    description = models.CharField('Descripcion', max_length=200, null=True, blank=True)
    parent_code = models.CharField('Codigo Padre', max_length=45, null=True, blank=True)

    def __str__(self):
        return str(self.code)


class LedgerEntry(models.Model):
    TYPE_CHOICES = (('D', 'Debito'), ('C', 'Credito'),)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField('Precio', max_digits=30, decimal_places=15, default=0)
    product = models.ForeignKey('sales.Product', on_delete=models.SET_NULL, null=True, blank=True)
    order_detail = models.ForeignKey('sales.OrderDetail', on_delete=models.SET_NULL, null=True, blank=True)
    create_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    type = models.CharField('Tipo', max_length=1, choices=TYPE_CHOICES, default='D', )

    account = models.ForeignKey(AccountingAccount, on_delete=models.SET_NULL, null=True, blank=True)
    transaction = models.ForeignKey(TransactionAccount, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return str(self.pk)


class Cash(models.Model):
    CURRENCY_TYPE_CHOICES = (('S', 'Soles'), ('E', 'Euros'), ('D', 'Dolares'),)
    name = models.CharField('Nombre', max_length=100, unique=True, null=True, blank=True)
    subsidiary = models.ForeignKey('hrm.Subsidiary', on_delete=models.SET_NULL, null=True, blank=True)
    account_number = models.CharField(max_length=14, null=True, blank=True)
    accounting_account = models.ForeignKey(AccountingAccount, on_delete=models.SET_NULL, null=True, blank=True)
    initial = models.DecimalField(max_digits=10, decimal_places=2, default='0', )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    currency_type = models.CharField('Tipo de moneda', max_length=1, choices=CURRENCY_TYPE_CHOICES, default='S', )

    def __str__(self):
        return str(self.name)

    def current_balance(self):
        inputs = 0
        outputs = 0
        opening = 0
        cash_flow_set = CashFlow.objects.filter(cash_id=self.pk)
        initial = self.initial

        if cash_flow_set:
            last_cash_flow_obj = cash_flow_set.last()
            inputs_bank_flow_set = cash_flow_set.filter(type='D').values('type').annotate(totals=Sum('total'))
            outputs_bank_flow_set = cash_flow_set.filter(type='R').values('type').annotate(totals=Sum('total'))

            cash_flow_set = cash_flow_set.filter(transaction_date__date=last_cash_flow_obj.transaction_date.date())
            inputs_cash_flow_set = cash_flow_set.filter(type='E').values('transaction_date__date').annotate(
                totals=Sum('total'))
            outputs_cash_flow_set = cash_flow_set.filter(type='S').values('transaction_date__date').annotate(
                totals=Sum('total'))
            if self.accounting_account.code.startswith('1041'):
                if last_cash_flow_obj.type == 'D':
                    if inputs_bank_flow_set:
                        inputs = inputs_bank_flow_set[0].get('totals')
                    opening = initial
                    if outputs_bank_flow_set:
                        outputs = outputs_bank_flow_set[0].get('totals')
                elif last_cash_flow_obj.type == 'R':
                    if outputs_bank_flow_set:
                        outputs = outputs_bank_flow_set[0].get('totals')
                    opening = initial
                    if inputs_bank_flow_set:
                        inputs = inputs_bank_flow_set[0].get('totals')

            elif self.accounting_account.code.startswith('101'):

                if last_cash_flow_obj.type == 'A':
                    opening = last_cash_flow_obj.total
                elif last_cash_flow_obj.type == 'C':
                    opening = last_cash_flow_obj.total
                elif last_cash_flow_obj.type == 'E':

                    opening_cash_flow_set = cash_flow_set.filter(type='A')
                    if opening_cash_flow_set:
                        opening = opening_cash_flow_set.last().total

                    inputs = inputs_cash_flow_set[0].get('totals')
                    if outputs_cash_flow_set:
                        outputs = outputs_cash_flow_set[0].get('totals')

                elif last_cash_flow_obj.type == 'S':

                    opening_cash_flow_set = cash_flow_set.filter(type='A')
                    if opening_cash_flow_set:
                        opening = opening_cash_flow_set.last().total

                    outputs = outputs_cash_flow_set[0].get('totals')
                    if inputs_cash_flow_set:
                        inputs = inputs_cash_flow_set[0].get('totals')

        else:
            opening = self.initial

        return opening + inputs - outputs


class CashTransfer(models.Model):
    STATUS_CHOICES = (('P', 'Pendiente'), ('A', 'Aceptado'), ('C', 'Cancelado'),)
    id = models.AutoField(primary_key=True)
    status = models.CharField('Tipo de Transferencia', max_length=1, choices=STATUS_CHOICES, default='P', )

    def __str__(self):
        return str(self.id)

    def get_origin(self):
        origin_set = CashTransferRoute.objects.filter(cash_transfer__id=self.id, type='O')
        origin = None
        if origin_set.count() > 0:
            origin = origin_set.last().cash
        return origin

    def get_destiny(self):
        destiny_set = CashTransferRoute.objects.filter(cash_transfer__id=self.id, type='D')
        destiny = None
        if destiny_set.count() > 0:
            destiny = destiny_set.last().cash
        return destiny

    def the_one_that_requests(self):
        action_set = CashTransferAction.objects.filter(cash_transfer__id=self.id, operation='E')
        cash_transfer_action = None
        if action_set.count() > 0:
            cash_transfer_action = action_set.last()
        return cash_transfer_action

    def the_one_that_approves(self):
        action_set = CashTransferAction.objects.filter(cash_transfer__id=self.id, operation='A')
        cash_transfer_action = None
        if action_set.count() > 0:
            cash_transfer_action = action_set.last()
        return cash_transfer_action

    def the_one_that_cancel(self):
        action_set = CashTransferAction.objects.filter(cash_transfer__id=self.id, operation='C')
        cash_transfer_action = None
        if action_set.count() > 0:
            cash_transfer_action = action_set.last()
        return cash_transfer_action

    def get_amount(self):
        cash_origin_obj = self.get_origin()
        amount = 0
        if cash_origin_obj:
            cash_flow_set = cash_origin_obj.cashflow_set.filter(cash_transfer__id=self.id)
            if cash_flow_set:
                amount = cash_flow_set.first().total
        return amount

    class Meta:
        verbose_name = 'Transferencia de caja'
        verbose_name_plural = 'Transferencias de cajas'


class CashFlow(models.Model):
    DOCUMENT_TYPE_ATTACHED_CHOICES = (
        ('F', 'Factura'), ('B', 'Boleta'), ('T', 'Ticket'), ('V', 'Vale'), ('O', 'Otro'))
    OPERATION_TYPE_CHOICES = (
    ('1', 'Deposito'), ('2', 'Pago electronico'), ('3', 'Compra electronica'), ('4', 'Extraccion bancaria'),
    ('5', 'Transferencia bancaria'), ('6', 'Transferencia de Caja a Caja'), ('7', 'Transferencia de Caja a banco'),
    ('0', 'Ninguno'))
    TYPE_CHOICES = (
    ('A', 'Apertura'), ('C', 'Cierre'), ('E', 'Entrada'), ('S', 'Salida'), ('D', 'Deposito'), ('R', 'Retiro'),
    ('T', 'Transferencia'),)
    transaction_date = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    description = models.CharField('Descripcion', max_length=200, null=True, blank=True)
    serial = models.CharField('Serie', max_length=5, null=True, blank=True)
    n_receipt = models.IntegerField('Numero de Comprobante', default=0, null=True, blank=True)
    document_type_attached = models.CharField('Tipo documento', max_length=1, choices=DOCUMENT_TYPE_ATTACHED_CHOICES,
                                              default='O', )
    type = models.CharField('Tipo de transaccion', max_length=1, choices=TYPE_CHOICES, default='E', )
    subtotal = models.DecimalField('subtotal', max_digits=30, decimal_places=15, default=0)
    total = models.DecimalField('total', max_digits=30, decimal_places=15, default=0)
    igv = models.DecimalField('Igv total', max_digits=30, decimal_places=15, default=0)
    cash = models.ForeignKey(Cash, on_delete=models.SET_NULL, null=True, blank=True)
    operation_code = models.CharField(
        verbose_name='Codigo de operación', max_length=45, null=True, blank=True)
    order = models.ForeignKey('sales.Order', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE, null=True, blank=True)
    operation_type = models.CharField('Tipo operacion', max_length=1, choices=OPERATION_TYPE_CHOICES, default='0', )
    cash_transfer = models.ForeignKey('CashTransfer', on_delete=models.SET_NULL, null=True, blank=True)
    purchase = models.ForeignKey('buys.Purchase', on_delete=models.SET_NULL, null=True, blank=True)
    requirement_buys = models.ForeignKey('buys.Requirement_buys', on_delete=models.CASCADE, null=True, blank=True)
    requirement_programming = models.ForeignKey('buys.RequirementBuysProgramming', on_delete=models.CASCADE, null=True,
                                                blank=True)

    def __str__(self):
        return str(self.pk)

    def return_inputs(self):
        response = 0
        cash_flow_set = CashFlow.objects.filter(cash=self.cash, transaction_date__date=self.transaction_date.date(),
                                                type='E').values(
            'transaction_date__date').annotate(totals=Sum('total'))
        if cash_flow_set.count() > 0:
            response = cash_flow_set[0].get('totals')
        return response

    def return_roses(self):
        response = 0
        cash_flow_set = CashFlow.objects.filter(cash=self.cash,
                                                transaction_date__date=self.transaction_date.date()).values(
            'transaction_date__date').annotate(counter=Count('id'))
        if cash_flow_set.count() > 0:
            response = cash_flow_set[0].get('counter')
        return response

    def return_outputs(self):
        response = 0
        cash_flow_set = CashFlow.objects.filter(cash=self.cash, transaction_date__date=self.transaction_date.date(),
                                                type='S').values(
            'transaction_date__date').annotate(totals=Sum('total'))
        if cash_flow_set.count() > 0:
            response = cash_flow_set[0].get('totals')
        return response

    def return_balance(self):
        cash_flow_set = CashFlow.objects.filter(cash=self.cash, transaction_date__date=self.transaction_date.date(),
                                                type='A')
        opening = 0
        if cash_flow_set.count() > 0:
            opening = cash_flow_set.first().total
        response = opening + self.return_inputs() - self.return_outputs()
        return response

    def return_status(self):
        cash_flow_set = CashFlow.objects.filter(cash=self.cash, transaction_date__date=self.transaction_date.date(),
                                                type='C')
        closed = False
        if cash_flow_set.count() > 0:
            closed = True
        return closed

    def return_last_cash_open(self):
        cash_flow_set = CashFlow.objects.filter(cash=self.cash, type='A')
        cash_flow = None
        if cash_flow_set:
            cash_flow = cash_flow_set.last()
        return cash_flow


class CashTransferRoute(models.Model):
    TYPE_CHOICES = (('O', 'Origen'), ('D', 'Destino'),)
    id = models.AutoField(primary_key=True)
    cash_transfer = models.ForeignKey('CashTransfer', on_delete=models.CASCADE)
    cash = models.ForeignKey('Cash', on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField('Tipo', max_length=1, choices=TYPE_CHOICES, default='O', )

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Sede con tranferencia'
        verbose_name_plural = 'Sedes con tranferencias'


class CashTransferAction(models.Model):
    OPERATION_CHOICES = (('E', 'Envio'), ('A', 'Acepto'), ('C', 'Cancelo'),)
    id = models.AutoField(primary_key=True)
    cash_transfer = models.ForeignKey('CashTransfer', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    operation = models.CharField('Operacion', max_length=1, choices=OPERATION_CHOICES, default='E', )
    register_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Usuario involucrado'
        verbose_name_plural = 'Usuarios involucrados'


class CashFlowLog(models.Model):
    id = models.AutoField(primary_key=True)
    cash_flow = models.ForeignKey('CashFlow', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField('Motivo', max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Caja reajuste'
        verbose_name_plural = 'Caja reajustes'


class Salary(models.Model):
    TYPE_CHOICES = (('S', 'Salario'),  ('G', 'Gratificacion'),)
    id = models.AutoField(primary_key=True)
    year = models.IntegerField('Año', default=0, null=True, blank=True)
    month = models.IntegerField('Meses', default=0, null=True, blank=True)
    worker = models.ForeignKey('hrm.Worker', on_delete=models.SET_NULL, null=True, blank=True)
    cash_flow = models.ForeignKey('CashFlow', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    type = models.CharField('Tipo de Pago', max_length=1, choices=TYPE_CHOICES, default='S', )

    def __str__(self):
        return str(self.id)


class Tributes(models.Model):
    id = models.AutoField(primary_key=True)
    year = models.IntegerField('Año', default=0, null=True, blank=True)
    month = models.IntegerField('Meses', default=0, null=True, blank=True)
    base_total_purchase = models.DecimalField('Total base mponible Compras', max_digits=10, decimal_places=2, default=0)
    igv_total_purchase = models.DecimalField('Total IGV compras', max_digits=30, decimal_places=2, default=0)
    total_purchase = models.DecimalField('Total compras', max_digits=30, decimal_places=2, default=0)
    base_total_sales = models.DecimalField('Total base ventas', max_digits=30, decimal_places=2, default=0)
    igv_total_sales = models.DecimalField('Total IGV ventas', max_digits=30, decimal_places=2, default=0)
    total_total_sales = models.DecimalField('Total ventas', max_digits=30, decimal_places=2, default=0)

    def __str__(self):
        return str(self.id)








