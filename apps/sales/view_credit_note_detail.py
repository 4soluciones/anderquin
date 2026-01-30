def view_credit_note_order_detail(request):
    """View to display credit note order details in a modal"""
    if request.method == 'GET':
        credit_note_id = request.GET.get('credit_note_id', '')
        
        try:
            credit_note = CreditNoteOrder.objects.select_related('order', 'order__client').get(id=int(credit_note_id))
            details = credit_note.creditnoteorderdetail_set.select_related('product', 'unit').all()
            
            # Calculate totals
            total = credit_note.get_total()
            subtotal = total / decimal.Decimal('1.18')
            igv = total - subtotal
            
            t = loader.get_template('sales/modal_credit_note_order_detail.html')
            c = {
                'credit_note': credit_note,
                'details': details,
                'total': total,
                'subtotal': subtotal,
                'igv': igv,
            }
            
            return JsonResponse({
                'html': t.render(c, request),
            })
        except CreditNoteOrder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Nota de crédito no encontrada'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al cargar el detalle: {str(e)}'
            }, status=500)
    
    return JsonResponse({'message': 'Método no permitido'}, status=400)
