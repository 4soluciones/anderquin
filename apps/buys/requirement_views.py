"""Módulo de requerimientos de compra.

Completa el proceso que faltaba entre la necesidad interna de una sede y la
emisión de una orden de compra (O/C). Usa los modelos existentes
``sales.Requirement`` y ``sales.RequirementDetail``.
"""
import decimal
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.hrm.views import get_subsidiary_by_user
from apps.sales.models import Product, ProductDetail, Requirement, RequirementDetail, Unit, Supplier

from .models import Purchase, PurchaseDetail
from .views import get_correlative_by_subsidiary


def _get_subsidiary(request):
    try:
        return get_subsidiary_by_user(request.user)
    except Exception:
        return None


def _status_label(status):
    return dict(Requirement.STATUS_CHOICES).get(status, status)


@login_required
def requirement_list(request):
    subsidiary = _get_subsidiary(request)
    queryset = Requirement.objects.select_related('user', 'subsidiary', 'purchase_order').prefetch_related(
        'requirementdetail_set'
    ).order_by('-id')
    if subsidiary:
        # Mostrar las de la sede actual y las históricas sin sede asignada.
        queryset = queryset.filter(subsidiary__in=[subsidiary, None])

    status = request.GET.get('status', '')
    req_type = request.GET.get('type', '')
    search = request.GET.get('q', '').strip()
    if status:
        queryset = queryset.filter(status=status)
    if req_type:
        queryset = queryset.filter(type=req_type)
    if search:
        queryset = queryset.filter(
            requirementdetail__product__name__icontains=search
        ).distinct()

    requirements = []
    status_styles = {
        '1': 'erp-badge-warning',
        '2': 'erp-badge-success',
        '3': 'erp-badge-success',
        '4': 'erp-badge-danger',
        '5': 'erp-badge',
        '6': 'erp-badge-danger',
    }
    for req in queryset:
        details = list(req.requirementdetail_set.all())
        requirements.append({
            'obj': req,
            'detail_count': len(details),
            'total_quantity': sum((d.quantity or 0) for d in details),
            'status_label': _status_label(req.status),
            'status_style': status_styles.get(req.status, 'erp-badge'),
        })

    return render(request, 'buys/requirement_list.html', {
        'requirements': requirements,
        'status_choices': Requirement.STATUS_CHOICES,
        'type_choices': Requirement.TYPE_CHOICES,
        'selected_status': status,
        'selected_type': req_type,
        'search': search,
        'subsidiary': subsidiary,
        'pending_count': Requirement.objects.exclude(status__in=['3', '6']).count(),
    })


@login_required
def requirement_create(request):
    subsidiary = _get_subsidiary(request)
    products = Product.objects.all().order_by('name')
    product_details = ProductDetail.objects.select_related('product', 'unit').filter(
        is_enabled=True
    ).order_by('product__name', 'unit__name')

    if request.method == 'POST':
        req_type = request.POST.get('type', 'M')
        creation_date = request.POST.get('creation_date') or timezone.localdate()
        delivery_date = request.POST.get('delivery_date') or None
        commentary = request.POST.get('commentary', '').strip()
        product_ids = request.POST.getlist('product[]')
        unit_ids = request.POST.getlist('unit[]')
        quantities = request.POST.getlist('quantity[]')
        comments = request.POST.getlist('commentary_detail[]')

        rows = []
        for product_id, unit_id, quantity, detail_comment in zip(product_ids, unit_ids, quantities, comments):
            if not product_id or not unit_id or not quantity:
                continue
            try:
                qty = int(float(quantity))
            except (TypeError, ValueError):
                continue
            if qty <= 0:
                continue
            rows.append((product_id, unit_id, qty, detail_comment.strip()))

        if not rows:
            messages.error(request, 'Debe agregar al menos un producto con cantidad mayor a cero.')
        else:
            with transaction.atomic():
                requirement = Requirement.objects.create(
                    status='1',
                    type=req_type,
                    creation_date=creation_date,
                    delivery_date=delivery_date,
                    user=request.user,
                    subsidiary=subsidiary,
                )
                for product_id, unit_id, qty, detail_comment in rows:
                    product = Product.objects.filter(pk=product_id).first()
                    unit = Unit.objects.filter(pk=unit_id).first()
                    if product and unit:
                        RequirementDetail.objects.create(
                            requirement=requirement,
                            product=product,
                            unit=unit,
                            quantity=qty,
                            commentary=detail_comment or commentary,
                        )
            messages.success(request, f'Requerimiento #{requirement.id} registrado correctamente.')
            return redirect('buys:requirement_detail', pk=requirement.pk)

    return render(request, 'buys/requirement_form.html', {
        'products': products,
        'product_details': product_details,
        'type_choices': Requirement.TYPE_CHOICES,
        'today': timezone.localdate(),
        'subsidiary': subsidiary,
    })


@login_required
def requirement_detail(request, pk):
    requirement = get_object_or_404(
        Requirement.objects.select_related('user', 'subsidiary', 'purchase_order').prefetch_related(
            'requirementdetail_set__product', 'requirementdetail_set__unit'
        ),
        pk=pk,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve' and requirement.status in ['1', '4']:
            requirement.status = '2'
            requirement.approval_date = timezone.localdate()
            requirement.save(update_fields=['status', 'approval_date'])
            messages.success(request, 'Requerimiento aprobado. Ya puede generar la orden de compra.')
        elif action == 'cancel' and requirement.status not in ['3', '6']:
            requirement.status = '6'
            requirement.save(update_fields=['status'])
            messages.warning(request, 'Requerimiento anulado.')
        elif action == 'observe' and requirement.status not in ['3', '6']:
            requirement.status = '4'
            requirement.save(update_fields=['status'])
            messages.warning(request, 'Requerimiento marcado como observado.')
        return redirect('buys:requirement_detail', pk=requirement.pk)

    details = requirement.requirementdetail_set.select_related('product', 'unit').all()
    total_quantity = sum((d.quantity or 0) for d in details)
    return render(request, 'buys/requirement_detail.html', {
        'requirement': requirement,
        'details': details,
        'total_quantity': total_quantity,
        'can_approve': requirement.status in ['1', '4'],
        'can_cancel': requirement.status not in ['3', '6'],
        'can_convert': requirement.status == '2' and not requirement.purchase_order_id,
    })


@login_required
def requirement_convert(request, pk):
    requirement = get_object_or_404(
        Requirement.objects.select_related('subsidiary').prefetch_related(
            'requirementdetail_set__product', 'requirementdetail_set__unit'
        ),
        pk=pk,
    )
    if requirement.purchase_order_id:
        messages.info(request, f'Este requerimiento ya generó la orden {requirement.purchase_order.bill_number}.')
        return redirect('buys:requirement_detail', pk=requirement.pk)
    if requirement.status != '2':
        messages.warning(request, 'El requerimiento debe estar aprobado antes de generar una orden de compra.')
        return redirect('buys:requirement_detail', pk=requirement.pk)

    details = list(requirement.requirementdetail_set.select_related('product', 'unit').all())
    for detail in details:
        presentation = ProductDetail.objects.filter(product=detail.product, unit=detail.unit).first()
        detail.suggested_price = presentation.price_purchase if presentation else decimal.Decimal('0')
    if not details:
        messages.error(request, 'El requerimiento no tiene productos.')
        return redirect('buys:requirement_detail', pk=requirement.pk)

    if request.method == 'POST':
        supplier = Supplier.objects.filter(pk=request.POST.get('supplier')).first()
        if not supplier:
            messages.error(request, 'Seleccione un proveedor válido.')
        else:
            year = timezone.localdate().year
            correlative = get_correlative_by_subsidiary(requirement.subsidiary, year)
            with transaction.atomic():
                purchase = Purchase.objects.create(
                    supplier=supplier,
                    purchase_date=timezone.localdate(),
                    user=request.user,
                    subsidiary=requirement.subsidiary,
                    bill_number=f'OC-{year}-{str(correlative).zfill(4)}',
                    correlative=correlative,
                    year=year,
                    status='S',
                    payment_method='CO',
                    delivery_choice='S',
                    delivery_subsidiary=requirement.subsidiary,
                    observation=request.POST.get('observation', '').strip() or f'Generada desde requerimiento #{requirement.id}',
                    reference=f'REQ-{requirement.id}',
                    delivery_date=requirement.delivery_date,
                )
                for detail in details:
                    raw_price = request.POST.get(f'price_{detail.id}', '0') or '0'
                    try:
                        price = decimal.Decimal(raw_price)
                    except decimal.InvalidOperation:
                        price = decimal.Decimal('0')
                    PurchaseDetail.objects.create(
                        purchase=purchase,
                        product=detail.product,
                        quantity=detail.quantity,
                        unit=detail.unit,
                        price_unit=price,
                    )
                    detail.condition = 'S'
                    detail.save(update_fields=['condition'])
                requirement.purchase_order = purchase
                requirement.status = '5'
                requirement.save(update_fields=['purchase_order', 'status'])
            messages.success(request, f'Orden de compra {purchase.bill_number} generada correctamente.')
            return redirect('buys:buy_order_list')

    return render(request, 'buys/requirement_convert.html', {
        'requirement': requirement,
        'details': details,
        'suppliers': Supplier.objects.all().order_by('name'),
    })
