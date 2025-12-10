from django.shortcuts import render, redirect
from django.db.models import Sum, Count, Q
from django.db.models.functions import Extract
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db import transaction
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

from .models import Pelanggan, Sopir, Kendaraan, Produk, StokMasuk, Pemesanan, DetailPemesanan, Feedback
from .forms import SopirEditPengirimanForm, PelangganRegisterForm, PelangganLoginForm, PemesananCheckoutForm, PelangganUpdateForm, ChangePasswordForm

def format_rupiah(amount):
    if amount is None:
        return "Rp 0"
    return f"Rp {int(amount):,}".replace(",", ".")

def add_page_template(canvas, doc, title):
    """Add header and footer to each page"""
    canvas.saveState()
    
    # Header
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawCentredString(A4[0]/2, A4[1]-50, f"Laporan {title} VIQUAM")
    
    # Footer
    canvas.setFont("Helvetica", 10)
    current_date = timezone.now().strftime("%d %B %Y")
    canvas.drawCentredString(A4[0]/2, 30, f"Tanggal Cetak: {current_date}")
    
    canvas.restoreState()

def create_pdf_header(canvas, title, date_range=None):
    """Create PDF header with date range"""
    # Header
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawCentredString(A4[0]/2, A4[1]-50, f"Laporan {title} VIQUAM")
    
    # Date range if provided
    if date_range:
        canvas.setFont("Helvetica", 10)
        canvas.drawCentredString(A4[0]/2, A4[1]-70, f"Periode: {date_range}")
    
    # Footer
    canvas.setFont("Helvetica", 10)
    current_date = timezone.now().strftime("%d %B %Y")
    canvas.drawCentredString(A4[0]/2, 30, f"Tanggal Cetak: {current_date}")

# Preview views
def admin_dashboard(request):
    now = timezone.now()
    
    # 1. Calculation: Start/End of Current Month
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        end_of_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        end_of_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    # --- Urgency & Metrik Lainnya (Semua perhitungan Count dan Sum tetap) ---
    pesanan_perlu_perhatian = Pemesanan.objects.filter(
        status__in=['Diproses', 'Dikirim'],
        tanggalPemesanan__lte=twenty_four_hours_ago
    ).count()
    
    total_pesanan_diproses = Pemesanan.objects.filter(status='Diproses').count()
    
    total_pengiriman_aktif = Pemesanan.objects.filter(status='Dikirim').count()
    
    pendapatan_bulan_ini_result = Pemesanan.objects.filter(
        status='Selesai',
        tanggalPemesanan__gte=start_of_month,
        tanggalPemesanan__lt=end_of_month
    ).aggregate(Sum('total'))['total__sum']
    
    pendapatan_bulan_ini = pendapatan_bulan_ini_result if pendapatan_bulan_ini_result is not None else Decimal('0')
    
    transaksi_selesai_bulan_ini = Pemesanan.objects.filter(
        status='Selesai',
        tanggalPemesanan__gte=start_of_month,
        tanggalPemesanan__lt=end_of_month
    ).count()
    
    produk_stok_menipis = Produk.objects.filter(stok__lt=10).count()
    feedback_terbaru = Feedback.objects.all().order_by('-tanggal')[:3]
    
    # --- 6-Month Revenue Data (Chart) ---
    months = []
    current_date = now.replace(day=1)
    for i in range(6):
        months.insert(0, (current_date.month, current_date.year))
        if current_date.month == 1:
            current_date = current_date.replace(year=current_date.year - 1, month=12)
        else:
            current_date = current_date.replace(month=current_date.month - 1)
            
    start_date_filter = current_date.replace(day=1)
    
    revenue_data = Pemesanan.objects.filter(
        status='Selesai',
        tanggalPemesanan__gte=start_date_filter
    ).annotate(
        month=Extract('tanggalPemesanan', 'month'),
        year=Extract('tanggalPemesanan', 'year')
    ).values('month', 'year').annotate(revenue=Sum('total')).order_by('year', 'month')
    
    chart_labels = []
    chart_data = []
    month_names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    
    for month, year in months:
        label = f"{month_names[month-1]} {str(year)[2:]}"
        chart_labels.append(label)
        
        revenue = 0.0
        for item in revenue_data:
            if item.get('month') == month and item.get('year') == year:
                # Konversi Decimal ke float secara eksplisit
                revenue = float(item.get('revenue')) if item.get('revenue') is not None else 0.0
                break
        chart_data.append(revenue)

    # PENTING: Konversi data ke JSON string dan kirim ke context
    chart_labels_json = json.dumps(chart_labels)
    chart_data_json = json.dumps(chart_data)

    context = {
        'pesanan_perlu_perhatian': pesanan_perlu_perhatian,
        'total_pesanan_diproses': total_pesanan_diproses,
        'total_pengiriman_aktif': total_pengiriman_aktif,
        'pendapatan_bulan_ini': pendapatan_bulan_ini, 
        'transaksi_selesai_bulan_ini': transaksi_selesai_bulan_ini,
        'produk_stok_menipis': produk_stok_menipis,
        'feedback_terbaru': feedback_terbaru,
        # Kirim string JSON
        'chart_labels_json': chart_labels_json,
        'chart_data_json': chart_data_json,
        'twenty_four_hours_ago': twenty_four_hours_ago.strftime('%Y-%m-%d')
    }
    
    return render(request, 'core/dashboard.html', context)

def admin_laporan_pelanggan(request):
    # Get filter parameters
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    
    # Build queryset
    pelanggan_list = Pelanggan.objects.all()
    
    # Apply date filters if provided and not empty
    if tgl_mulai and tgl_akhir:
        # Filter pelanggan based on their last order date
        pelanggan_dengan_pesanan = Pemesanan.objects.filter(
            tanggalPemesanan__date__gte=tgl_mulai,
            tanggalPemesanan__date__lte=tgl_akhir
        ).values_list('idPelanggan', flat=True)
        pelanggan_list = pelanggan_list.filter(idPelanggan__in=pelanggan_dengan_pesanan)
    
    # Calculate total purchases for each customer
    pelanggan_data = []
    for pelanggan in pelanggan_list:
        total_pembelian = Pemesanan.objects.filter(idPelanggan=pelanggan).aggregate(
            total=Sum('total')
        )['total'] or 0
        
        pelanggan_data.append({
            'nama': pelanggan.nama,
            'noWa': pelanggan.noWa,
            'alamat': pelanggan.alamat,
            'username': pelanggan.username,
            'total_pembelian': format_rupiah(total_pembelian)
        })
    
    context = {
        'judul_laporan': 'Data Pelanggan',
        'pelanggan_list': pelanggan_data,
        'tgl_mulai': tgl_mulai,
        'tgl_akhir': tgl_akhir
    }
    return render(request, 'core/laporan_pelanggan.html', context)

def admin_laporan_produk(request):
    filter_tipe = request.GET.get('filter_tipe')
    batas_stok = request.GET.get('batas_stok', 10)
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    
    produk_list = Produk.objects.all()
    
    if filter_tipe == 'terlaris' or (tgl_mulai or tgl_akhir):
        date_filter_q = None
        if tgl_mulai and tgl_akhir:
            date_filter_q = Q(detailpemesanan__idPemesanan__tanggalPemesanan__date__gte=tgl_mulai) & \
                           Q(detailpemesanan__idPemesanan__tanggalPemesanan__date__lte=tgl_akhir)
        elif tgl_mulai:
            date_filter_q = Q(detailpemesanan__idPemesanan__tanggalPemesanan__date__gte=tgl_mulai)
        elif tgl_akhir:
            date_filter_q = Q(detailpemesanan__idPemesanan__tanggalPemesanan__date__lte=tgl_akhir)
        
        if filter_tipe == 'terlaris':
            if date_filter_q:
                produk_list = produk_list.annotate(
                    total_terjual=Sum('detailpemesanan__jumlah', filter=date_filter_q)
                ).order_by('-total_terjual')
            else:
                produk_list = produk_list.annotate(
                    total_terjual=Sum('detailpemesanan__jumlah')
                ).order_by('-total_terjual')
        else:
            produk_list = produk_list.annotate(
                total_terjual=Sum('detailpemesanan__jumlah', filter=date_filter_q) if date_filter_q else Sum('detailpemesanan__jumlah')
            )
    elif filter_tipe == 'stok_menipis':
        produk_list = produk_list.filter(stok__lte=batas_stok).order_by('stok')
    
    produk_data = []
    for produk in produk_list:
        product_date_filter_q = None
        if tgl_mulai and tgl_akhir:
            product_date_filter_q = Q(idPemesanan__tanggalPemesanan__date__gte=tgl_mulai) & \
                                  Q(idPemesanan__tanggalPemesanan__date__lte=tgl_akhir)
        elif tgl_mulai:
            product_date_filter_q = Q(idPemesanan__tanggalPemesanan__date__gte=tgl_mulai)
        elif tgl_akhir:
            product_date_filter_q = Q(idPemesanan__tanggalPemesanan__date__lte=tgl_akhir)
            
        total_terjual = 0
        if filter_tipe == 'terlaris' or (tgl_mulai or tgl_akhir):
            total_terjual_queryset = DetailPemesanan.objects.filter(idProduk=produk)
            if product_date_filter_q:
                total_terjual_queryset = total_terjual_queryset.filter(product_date_filter_q)
            total_terjual = total_terjual_queryset.aggregate(total=Sum('jumlah'))['total'] or 0
        
        produk_data.append({
            'namaProduk': produk.namaProduk,
            'ukuranKemasan': produk.ukuranKemasan,
            'hargaPerDus': format_rupiah(produk.hargaPerDus),
            'stok': produk.stok,
            'total_terjual': total_terjual if (filter_tipe == 'terlaris' or (tgl_mulai or tgl_akhir)) else None
        })
    
    context = {
        'judul_laporan': 'Produk & Stok',
        'produk_list': produk_data,
        'tgl_mulai': tgl_mulai,
        'tgl_akhir': tgl_akhir,
        'filter_tipe': filter_tipe,
        'batas_stok': batas_stok
    }
    return render(request, 'core/laporan_produk.html', context)

def admin_laporan_sopir_kendaraan(request):
    # Get filter parameters
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    
    # Build queryset
    sopir_list = Sopir.objects.all()
    
    # Process data for each driver
    sopir_data = []
    for sopir in sopir_list:
        # Get driver's vehicle
        kendaraan = Kendaraan.objects.filter(idSopir=sopir).first()
        kendaraan_nama = kendaraan.nama if kendaraan else None
        
        # Count completed orders for this driver
        pesanan_selesai_queryset = Pemesanan.objects.filter(
            idSopir=sopir,
            status='Selesai'
        )
        
        # Apply date filters if provided and not empty
        if tgl_mulai:
            pesanan_selesai_queryset = pesanan_selesai_queryset.filter(
                tanggalPemesanan__date__gte=tgl_mulai
            )
        if tgl_akhir:
            pesanan_selesai_queryset = pesanan_selesai_queryset.filter(
                tanggalPemesanan__date__lte=tgl_akhir
            )
            
        pesanan_selesai = pesanan_selesai_queryset.count()
        
        sopir_data.append({
            'nama': sopir.nama,
            'noHp': sopir.noHp,
            'username': sopir.username,
            'kendaraan_nama': kendaraan_nama,
            'pesanan_selesai': pesanan_selesai
        })
    
    context = {
        'judul_laporan': 'Sopir & Kendaraan',
        'sopir_list': sopir_data,
        'tgl_mulai': tgl_mulai,
        'tgl_akhir': tgl_akhir
    }
    return render(request, 'core/laporan_sopir_kendaraan.html', context)

def admin_laporan_pemesanan_pendapatan(request):
    # Get filter parameters
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    status_pesanan = request.GET.get('status_pesanan')
    
    # Build queryset
    pemesanan_list = Pemesanan.objects.all()
    
    # Apply filters
    if tgl_mulai:
        pemesanan_list = pemesanan_list.filter(
            tanggalPemesanan__date__gte=tgl_mulai
        )
    if tgl_akhir:
        pemesanan_list = pemesanan_list.filter(
            tanggalPemesanan__date__lte=tgl_akhir
        )
    
    if status_pesanan:
        pemesanan_list = pemesanan_list.filter(status=status_pesanan)
    
    # Calculate total revenue
    total_pendapatan = pemesanan_list.aggregate(total=Sum('total'))['total'] or 0
    
    # Process data for each order
    pemesanan_data = []
    for pemesanan in pemesanan_list:
        pemesanan_data.append({
            'tanggalPemesanan': pemesanan.tanggalPemesanan,
            'idPelanggan': pemesanan.idPelanggan,
            'alamatPengiriman': pemesanan.alamatPengiriman,
            'status': pemesanan.status,
            'total': format_rupiah(pemesanan.total)
        })
    
    context = {
        'judul_laporan': 'Pemesanan & Pendapatan',
        'pemesanan_list': pemesanan_data,
        'tgl_mulai': tgl_mulai,
        'tgl_akhir': tgl_akhir,
        'status_pesanan': status_pesanan,
        'total_pendapatan': format_rupiah(total_pendapatan)
    }
    return render(request, 'core/laporan_pemesanan_pendapatan.html', context)

def admin_laporan_feedback(request):
    # Get filter parameters
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    
    # Build queryset
    feedback_list = Feedback.objects.all().select_related('idPelanggan')
    
    # Apply date filters if provided and not empty
    if tgl_mulai:
        feedback_list = feedback_list.filter(
            tanggal__date__gte=tgl_mulai
        )
    if tgl_akhir:
        feedback_list = feedback_list.filter(
            tanggal__date__lte=tgl_akhir
        )
    
    # Process data for each feedback
    feedback_data = []
    for feedback in feedback_list:
        feedback_data.append({
            'tanggal': feedback.tanggal,
            'idPelanggan': feedback.idPelanggan,
            'isi': feedback.isi
        })
    
    context = {
        'judul_laporan': 'Feedback Pelanggan',
        'feedback_list': feedback_data,
        'tgl_mulai': tgl_mulai,
        'tgl_akhir': tgl_akhir
    }
    return render(request, 'core/laporan_feedback.html', context)

def laporan_pelanggan(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="laporan_pelanggan.pdf"'
    
    # Create a PDF buffer
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Get filter parameters
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    
    # Build queryset
    pelanggan_list = Pelanggan.objects.all()
    
    # Apply date filters if provided and not empty
    date_range = ""
    if tgl_mulai and tgl_akhir:
        date_range = f"{tgl_mulai} - {tgl_akhir}"
        # Filter pelanggan based on their last order date
        pelanggan_dengan_pesanan = Pemesanan.objects.filter(
            tanggalPemesanan__date__gte=tgl_mulai,
            tanggalPemesanan__date__lte=tgl_akhir
        ).values_list('idPelanggan', flat=True)
        pelanggan_list = pelanggan_list.filter(idPelanggan__in=pelanggan_dengan_pesanan)
    
    # Add header
    create_pdf_header(p, "Data Pelanggan", date_range)
    
    # Prepare data for table
    data = [['No', 'Nama', 'No WA', 'Alamat', 'Username', 'Total Pembelian']]
    
    y_position = 700
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    
    for i, pelanggan in enumerate(pelanggan_list, 1):
        # Calculate total purchases for this customer
        total_pembelian = Pemesanan.objects.filter(idPelanggan=pelanggan).aggregate(
            total=Sum('total')
        )['total'] or 0
        
        row = [
            str(i),
            pelanggan.nama,
            pelanggan.noWa,
            pelanggan.alamat,
            pelanggan.username,
            format_rupiah(total_pembelian)
        ]
        data.append(row)
    
    # Create table with improved styling
    table = Table(data, colWidths=None)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    # Center the table horizontally
    table.hAlign = 'CENTER'
    
    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, (width - table.minWidth()) / 2, y_position - len(data) * 20)
    
    # Save PDF
    p.showPage()
    p.save()
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

def laporan_produk(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="laporan_produk.pdf"'
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    filter_tipe = request.GET.get('filter_tipe')
    batas_stok = request.GET.get('batas_stok', 10)
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    
    produk_list = Produk.objects.all()
    
    date_range = ""
    if tgl_mulai and tgl_akhir:
        date_range = f"{tgl_mulai} - {tgl_akhir}"
    
    if filter_tipe == 'terlaris' or (tgl_mulai or tgl_akhir):
        date_filter_q = None
        if tgl_mulai and tgl_akhir:
            date_filter_q = Q(detailpemesanan__idPemesanan__tanggalPemesanan__date__gte=tgl_mulai) & \
                           Q(detailpemesanan__idPemesanan__tanggalPemesanan__date__lte=tgl_akhir)
        elif tgl_mulai:
            date_filter_q = Q(detailpemesanan__idPemesanan__tanggalPemesanan__date__gte=tgl_mulai)
        elif tgl_akhir:
            date_filter_q = Q(detailpemesanan__idPemesanan__tanggalPemesanan__date__lte=tgl_akhir)
        
        if filter_tipe == 'terlaris':
            if date_filter_q:
                produk_list = produk_list.annotate(
                    total_terjual=Sum('detailpemesanan__jumlah', filter=date_filter_q)
                ).order_by('-total_terjual')
            else:
                produk_list = produk_list.annotate(
                    total_terjual=Sum('detailpemesanan__jumlah')
                ).order_by('-total_terjual')
        else:
            produk_list = produk_list.annotate(
                total_terjual=Sum('detailpemesanan__jumlah', filter=date_filter_q) if date_filter_q else Sum('detailpemesanan__jumlah')
            )
    elif filter_tipe == 'stok_menipis':
        produk_list = produk_list.filter(stok__lte=batas_stok).order_by('stok')
    
    create_pdf_header(p, "Produk & Stok", date_range)
    
    data = [['No', 'Nama Produk', 'Ukuran', 'Harga', 'Stok', 'Terjual']]
    
    y_position = 700
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    
    for i, produk in enumerate(produk_list, 1):
        product_date_filter_q = None
        if tgl_mulai and tgl_akhir:
            product_date_filter_q = Q(idPemesanan__tanggalPemesanan__date__gte=tgl_mulai) & \
                                  Q(idPemesanan__tanggalPemesanan__date__lte=tgl_akhir)
        elif tgl_mulai:
            product_date_filter_q = Q(idPemesanan__tanggalPemesanan__date__gte=tgl_mulai)
        elif tgl_akhir:
            product_date_filter_q = Q(idPemesanan__tanggalPemesanan__date__lte=tgl_akhir)
            
        total_terjual = 0
        if filter_tipe == 'terlaris' or (tgl_mulai or tgl_akhir):
            total_terjual_queryset = DetailPemesanan.objects.filter(idProduk=produk)
            if product_date_filter_q:
                total_terjual_queryset = total_terjual_queryset.filter(product_date_filter_q)
            total_terjual = total_terjual_queryset.aggregate(total=Sum('jumlah'))['total'] or 0
        
        row = [
            str(i),
            produk.namaProduk,
            produk.ukuranKemasan,
            format_rupiah(produk.hargaPerDus),
            str(produk.stok),
            str(total_terjual) if (filter_tipe == 'terlaris' or (tgl_mulai or tgl_akhir)) else "-"
        ]
        data.append(row)
    
    table = Table(data, colWidths=None)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    table.hAlign = 'CENTER'
    
    table.wrapOn(p, width, height)
    table.drawOn(p, (width - table.minWidth()) / 2, y_position - len(data) * 20)
    
    p.showPage()
    p.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

def laporan_sopir_kendaraan(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="laporan_sopir_kendaraan.pdf"'
    
    # Create a PDF buffer
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Get filter parameters
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    
    # Build queryset
    sopir_list = Sopir.objects.all()
    
    # Apply date filters if provided and not empty
    date_range = ""
    if tgl_mulai and tgl_akhir:
        date_range = f"{tgl_mulai} - {tgl_akhir}"
    
    # Add header
    create_pdf_header(p, "Sopir & Kendaraan", date_range)
    
    # Prepare data for table
    data = [['No', 'Nama Sopir', 'No HP', 'Username', 'Kendaraan', 'Pesanan Selesai']]
    
    y_position = 700
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    
    for i, sopir in enumerate(sopir_list, 1):
        # Get driver's vehicle
        kendaraan = Kendaraan.objects.filter(idSopir=sopir).first()
        nama_kendaraan = kendaraan.nama if kendaraan else "-"
        
        # Count completed orders for this driver
        pesanan_selesai_queryset = Pemesanan.objects.filter(
            idSopir=sopir,
            status='Selesai'
        )
        
        # Apply date filters if provided and not empty
        if tgl_mulai:
            pesanan_selesai_queryset = pesanan_selesai_queryset.filter(
                tanggalPemesanan__date__gte=tgl_mulai
            )
        if tgl_akhir:
            pesanan_selesai_queryset = pesanan_selesai_queryset.filter(
                tanggalPemesanan__date__lte=tgl_akhir
            )
            
        pesanan_selesai = pesanan_selesai_queryset.count()
        
        row = [
            str(i),
            sopir.nama,
            sopir.noHp,
            sopir.username,
            nama_kendaraan,
            str(pesanan_selesai)
        ]
        data.append(row)
    
    # Create table with improved styling
    table = Table(data, colWidths=None)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    # Center the table horizontally
    table.hAlign = 'CENTER'
    
    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, (width - table.minWidth()) / 2, y_position - len(data) * 20)
    
    # Save PDF
    p.showPage()
    p.save()
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

def laporan_pemesanan_pendapatan(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="laporan_pemesanan_pendapatan.pdf"'
    
    # Create a PDF buffer
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Get filter parameters
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    status_pesanan = request.GET.get('status_pesanan')
    
    # Build queryset
    pemesanan_list = Pemesanan.objects.all()
    
    # Apply filters
    date_range = ""
    if tgl_mulai and tgl_akhir:
        date_range = f"{tgl_mulai} - {tgl_akhir}"
        pemesanan_list = pemesanan_list.filter(
            tanggalPemesanan__date__gte=tgl_mulai,
            tanggalPemesanan__date__lte=tgl_akhir
        )
    else:
        # Apply individual date filters if provided
        if tgl_mulai:
            pemesanan_list = pemesanan_list.filter(
                tanggalPemesanan__date__gte=tgl_mulai
            )
        if tgl_akhir:
            pemesanan_list = pemesanan_list.filter(
                tanggalPemesanan__date__lte=tgl_akhir
            )
    
    if status_pesanan:
        pemesanan_list = pemesanan_list.filter(status=status_pesanan)
    
    # Calculate total revenue
    total_pendapatan = pemesanan_list.aggregate(total=Sum('total'))['total'] or 0
    
    # Add header
    create_pdf_header(p, "Pemesanan & Pendapatan", date_range)
    
    # Add total revenue
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(A4[0]/2, 720, f"Total Pendapatan: {format_rupiah(total_pendapatan)}")
    
    # Prepare data for table
    data = [['No', 'Tanggal', 'Pelanggan', 'Alamat', 'Status', 'Total']]
    
    y_position = 680
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    
    for i, pemesanan in enumerate(pemesanan_list, 1):
        row = [
            str(i),
            pemesanan.tanggalPemesanan.strftime("%d/%m/%Y"),
            pemesanan.idPelanggan.nama,
            pemesanan.alamatPengiriman,
            pemesanan.status,
            format_rupiah(pemesanan.total)
        ]
        data.append(row)
    
    # Create table with improved styling
    table = Table(data, colWidths=None)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    # Center the table horizontally
    table.hAlign = 'CENTER'
    
    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, (width - table.minWidth()) / 2, y_position - len(data) * 20)
    
    # Save PDF
    p.showPage()
    p.save()
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

def laporan_feedback(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="laporan_feedback.pdf"'
    
    # Create a PDF buffer
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Get filter parameters
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    
    # Build queryset
    feedback_list = Feedback.objects.all().select_related('idPelanggan')
    
    # Apply date filters if provided and not empty
    date_range = ""
    if tgl_mulai and tgl_akhir:
        date_range = f"{tgl_mulai} - {tgl_akhir}"
        feedback_list = feedback_list.filter(
            tanggal__date__gte=tgl_mulai,
            tanggal__date__lte=tgl_akhir
        )
    else:
        # Apply individual date filters if provided
        if tgl_mulai:
            feedback_list = feedback_list.filter(
                tanggal__date__gte=tgl_mulai
            )
        if tgl_akhir:
            feedback_list = feedback_list.filter(
                tanggal__date__lte=tgl_akhir
            )
    
    # Add header
    create_pdf_header(p, "Feedback Pelanggan", date_range)
    
    # Prepare data for table
    data = [['No', 'Tanggal', 'Pelanggan', 'Feedback']]
    
    y_position = 700
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    
    for i, feedback in enumerate(feedback_list, 1):
        row = [
            str(i),
            feedback.tanggal.strftime("%d/%m/%Y"),
            feedback.idPelanggan.nama,
            feedback.isi[:50] + "..." if len(feedback.isi) > 50 else feedback.isi
        ]
        data.append(row)
    
    # Create table with improved styling
    table = Table(data, colWidths=None)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    # Center the table horizontally
    table.hAlign = 'CENTER'
    
    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, (width - table.minWidth()) / 2, y_position - len(data) * 20)
    
    # Save PDF
    p.showPage()
    p.save()
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

def sopir_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            sopir = Sopir.objects.get(username=username)
            if sopir.check_password(password):
                # Store sopir info in session
                request.session['sopir_id'] = sopir.idSopir
                request.session['sopir_nama'] = sopir.nama
                messages.success(request, f'Selamat datang, {sopir.nama}!')
                return redirect('sopir-dashboard')
            else:
                messages.error(request, 'Password salah.')
        except Sopir.DoesNotExist:
            messages.error(request, 'Username tidak ditemukan.')
    
    return render(request, 'sopir/login.html')

def sopir_logout(request):
    # Clear session data
    if 'sopir_id' in request.session:
        del request.session['sopir_id']
    if 'sopir_nama' in request.session:
        del request.session['sopir_nama']
    
    messages.info(request, 'Anda telah logout.')
    return redirect('sopir-login')

def sopir_dashboard(request):
    # Check if sopir is logged in
    if 'sopir_id' not in request.session:
        messages.error(request, 'Silakan login terlebih dahulu.')
        return redirect('sopir-login')
    
    # Get logged in sopir ID
    sopir_id = request.session['sopir_id']
    
    # Get orders assigned to this sopir with status 'Dikirim'
    pesanan_list = Pemesanan.objects.filter(
        status='Dikirim',
        idSopir_id=sopir_id
    ).select_related('idPelanggan').order_by('-tanggalPemesanan')
    
    context = {
        'pesanan_list': pesanan_list,
    }
    
    return render(request, 'sopir/dashboard.html', context)

def sopir_edit_pengiriman(request, pk):
    # Check if sopir is logged in
    if 'sopir_id' not in request.session:
        messages.error(request, 'Silakan login terlebih dahulu.')
        return redirect('sopir-login')
    
    # Get logged in sopir ID
    sopir_id = request.session['sopir_id']
    
    try:
        # Get the order, ensuring it belongs to the logged in sopir and has status 'Dikirim'
        pesanan = Pemesanan.objects.get(
            pk=pk,
            status='Dikirim',
            idSopir_id=sopir_id
        )
    except Pemesanan.DoesNotExist:
        messages.error(request, 'Pesanan tidak ditemukan atau tidak memiliki akses.')
        return redirect('sopir-dashboard')
    
    if request.method == 'POST':
        form = SopirEditPengirimanForm(request.POST, request.FILES, instance=pesanan)
        if form.is_valid():
            # Save the form with the status selected by the Sopir
            form.save()
            
            messages.success(request, 'Verifikasi pengiriman berhasil.')
            return redirect('sopir-dashboard')
    else:
        form = SopirEditPengirimanForm(instance=pesanan)
    
    context = {
        'form': form,
        'pesanan': pesanan,
    }
    
    return render(request, 'sopir/edit_pengiriman.html', context)

def sopir_account(request):
    # Check if sopir is logged in
    if 'sopir_id' not in request.session:
        messages.error(request, 'Silakan login terlebih dahulu.')
        return redirect('sopir-login')
    
    # Get logged in sopir ID
    sopir_id = request.session['sopir_id']
    
    try:
        # Get sopir data
        sopir = Sopir.objects.get(idSopir=sopir_id)
        # Get kendaraan assigned to this sopir
        kendaraan = Kendaraan.objects.filter(idSopir=sopir)
        
        context = {
            'sopir': sopir,
            'kendaraan_list': kendaraan,
        }
        
        return render(request, 'sopir/sopir_account.html', context)
    except Sopir.DoesNotExist:
        messages.error(request, 'Data sopir tidak ditemukan.')
        return redirect('sopir-dashboard')

# Utility functions for cart management
def get_keranjang(request):
    """Get cart from session or create empty cart"""
    keranjang = request.session.get('cart', {})
    return keranjang

def save_keranjang(request, keranjang):
    """Save cart to session"""
    request.session['cart'] = keranjang
    request.session.modified = True

# Pelanggan Views
def landing_page(request):
    """Landing page view"""
    if 'pelanggan_id' in request.session:
        return redirect('pelanggan_home')
    return render(request, 'pelanggan/landing.html')

def pelanggan_register(request):
    """Register new pelanggan"""
    if request.method == 'POST':
        form = PelangganRegisterForm(request.POST)
        if form.is_valid():
            # Check if username already exists
            username = form.cleaned_data['username']
            if Pelanggan.objects.filter(username=username).exists():
                messages.error(request, 'Username sudah digunakan!')
                return render(request, 'pelanggan/register.html', {'form': form})
            
            # Save pelanggan
            pelanggan = form.save()
            messages.success(request, 'Registrasi berhasil! Silakan login.')
            return redirect('pelanggan_login')
    else:
        form = PelangganRegisterForm()
    
    return render(request, 'pelanggan/register.html', {'form': form})

def pelanggan_login(request):
    """Login pelanggan"""
    if request.method == 'POST':
        form = PelangganLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            try:
                pelanggan = Pelanggan.objects.get(username=username)
                if pelanggan.check_password(password):
                    # Store pelanggan info in session
                    request.session['pelanggan_id'] = pelanggan.idPelanggan
                    request.session['pelanggan_nama'] = pelanggan.nama
                    messages.success(request, f'Selamat datang, {pelanggan.nama}!')
                    return redirect('pelanggan_home')
                else:
                    messages.error(request, 'Password salah.')
            except Pelanggan.DoesNotExist:
                messages.error(request, 'Username tidak ditemukan.')
    else:
        form = PelangganLoginForm()
    
    return render(request, 'pelanggan/login.html', {'form': form})

def pelanggan_logout(request):
    """Logout pelanggan"""
    # Clear session data
    if 'pelanggan_id' in request.session:
        del request.session['pelanggan_id']
    if 'pelanggan_nama' in request.session:
        del request.session['pelanggan_nama']
    if 'cart' in request.session:
        del request.session['cart']
    
    messages.info(request, 'Anda telah logout.')
    return redirect('landing')

@login_required(login_url='pelanggan_login')
def pelanggan_home(request):
    """Pelanggan home/dashboard after login"""
    # Get pelanggan from session
    pelanggan_id = request.session['pelanggan_id']
    pelanggan = Pelanggan.objects.get(idPelanggan=pelanggan_id)
    
    context = {
        'pelanggan': pelanggan,
    }
    
    return render(request, 'pelanggan/home.html', context)

@login_required(login_url='pelanggan_login')
def list_produk(request):
    """List all available products"""
    # Get products with stock > 0
    produk_list = Produk.objects.filter(stok__gt=0).order_by('namaProduk')
    
    # Pagination
    paginator = Paginator(produk_list, 12)  # Show 12 products per page
    page_number = request.GET.get('page')
    produk_page = paginator.get_page(page_number)
    
    context = {
        'produk_list': produk_page,
    }
    
    return render(request, 'pelanggan/produk_list.html', context)

@login_required(login_url='pelanggan_login')
def detail_produk(request, pk):
    """Show product detail"""
    try:
        produk = Produk.objects.get(idProduk=pk, stok__gt=0)
    except Produk.DoesNotExist:
        messages.error(request, 'Produk tidak ditemukan atau stok habis.')
        return redirect('list_produk')
    
    context = {
        'produk': produk,
    }
    
    return render(request, 'pelanggan/detail_produk.html', context)

@login_required(login_url='pelanggan_login')
def tambah_ke_keranjang(request, pk):
    """Add product to cart"""
    if request.method == 'POST':
        try:
            produk = Produk.objects.get(idProduk=pk, stok__gt=0)
        except Produk.DoesNotExist:
            messages.error(request, 'Produk tidak ditemukan atau stok habis.')
            return redirect('list_produk')
        
        # Get quantity from POST data
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            quantity = 1
        
        # Validate quantity
        if quantity <= 0:
            messages.error(request, 'Jumlah harus lebih dari 0.')
            return redirect('detail_produk', pk=pk)
        
        if quantity > produk.stok:
            messages.error(request, f'Stok tidak mencukupi. Stok tersedia: {produk.stok}')
            return redirect('detail_produk', pk=pk)
        
        # Get cart from session
        keranjang = get_keranjang(request)
        
        # Add product to cart
        product_id = str(produk.idProduk)
        if product_id in keranjang:
            # Update quantity if product already in cart
            keranjang[product_id]['quantity'] += quantity
            # Check if total quantity exceeds stock
            if keranjang[product_id]['quantity'] > produk.stok:
                keranjang[product_id]['quantity'] = produk.stok
                messages.warning(request, f'Jumlah di keranjang telah disesuaikan dengan stok tersedia: {produk.stok}')
        else:
            # Add new product to cart
            keranjang[product_id] = {
                'nama': produk.namaProduk,
                'harga': float(produk.hargaPerDus),
                'quantity': quantity,
                'stok': produk.stok
            }
        
        # Save cart to session
        save_keranjang(request, keranjang)
        
        messages.success(request, f'{produk.namaProduk} berhasil ditambahkan ke keranjang!')
        return redirect('view_keranjang')
    
    return redirect('list_produk')

@login_required(login_url='pelanggan_login')
def view_keranjang(request):
    """View cart contents"""
    # Get cart from session
    keranjang = get_keranjang(request)
    
    # Calculate totals
    total_items = 0
    total_price = 0
    cart_items = []
    
    for product_id, item in keranjang.items():
        subtotal = item['harga'] * item['quantity']
        total_items += item['quantity']
        total_price += subtotal
        
        cart_items.append({
            'id': product_id,
            'nama': item['nama'],
            'harga': item['harga'],
            'quantity': item['quantity'],
            'subtotal': subtotal,
            'stok': item['stok']
        })
    
    context = {
        'cart_items': cart_items,
        'total_items': total_items,
        'total_price': total_price,
    }
    
    return render(request, 'pelanggan/keranjang.html', context)

@login_required(login_url='pelanggan_login')
def update_keranjang(request, pk):
    """Update item quantity in cart"""
    if request.method == 'POST':
        try:
            produk = Produk.objects.get(idProduk=pk)
        except Produk.DoesNotExist:
            messages.error(request, 'Produk tidak ditemukan.')
            return redirect('view_keranjang')
        
        # Get new quantity from POST data
        try:
            quantity = int(request.POST.get('quantity', 1))
        except ValueError:
            quantity = 1
        
        # Validate quantity
        if quantity <= 0:
            return remove_from_keranjang(request, pk)
        
        if quantity > produk.stok:
            messages.error(request, f'Stok tidak mencukupi. Stok tersedia: {produk.stok}')
            quantity = produk.stok
        
        # Get cart from session
        keranjang = get_keranjang(request)
        
        # Update quantity
        product_id = str(produk.idProduk)
        if product_id in keranjang:
            keranjang[product_id]['quantity'] = quantity
            save_keranjang(request, keranjang)
            messages.success(request, f'Jumlah {produk.namaProduk} telah diperbarui.')
        else:
            messages.error(request, 'Produk tidak ditemukan di keranjang.')
    
    return redirect('view_keranjang')

@login_required(login_url='pelanggan_login')
def remove_from_keranjang(request, pk):
    """Remove item from cart"""
    # Get cart from session
    keranjang = get_keranjang(request)
    
    # Remove item
    product_id = str(pk)
    if product_id in keranjang:
        nama_produk = keranjang[product_id]['nama']
        del keranjang[product_id]
        save_keranjang(request, keranjang)
        messages.success(request, f'{nama_produk} telah dihapus dari keranjang.')
    else:
        messages.error(request, 'Produk tidak ditemukan di keranjang.')
    
    return redirect('view_keranjang')

@login_required(login_url='pelanggan_login')
def checkout_pemesanan(request):
    """Checkout process with transaction safety"""
    # Get cart from session
    keranjang = get_keranjang(request)
    
    # Check if cart is empty
    if not keranjang:
        messages.error(request, 'Keranjang belanja kosong.')
        return redirect('view_keranjang')
    
    # Calculate totals
    total_items = 0
    total_price = 0
    cart_items = []
    
    for product_id, item in keranjang.items():
        subtotal = item['harga'] * item['quantity']
        total_items += item['quantity']
        total_price += subtotal
        
        cart_items.append({
            'id': product_id,
            'nama': item['nama'],
            'harga': item['harga'],
            'quantity': item['quantity'],
            'subtotal': subtotal,
            'stok': item['stok']
        })
    
    if request.method == 'POST':
        form = PemesananCheckoutForm(request.POST, request.FILES)
        if form.is_valid():
            # Check if buktiBayar is required and provided
            bukti_bayar = request.FILES.get('buktiBayar')
            if not bukti_bayar:
                messages.error(request, 'Bukti pembayaran wajib diunggah.')
                return render(request, 'pelanggan/checkout.html', {
                    'form': form,
                    'cart_items': cart_items,
                    'total_items': total_items,
                    'total_price': total_price,
                })
            
            # Use atomic transaction to ensure data consistency
            with transaction.atomic():
                # Get pelanggan from session
                pelanggan_id = request.session['pelanggan_id']
                pelanggan = Pelanggan.objects.get(idPelanggan=pelanggan_id)
                
                # Create new pemesanan
                pemesanan = Pemesanan.objects.create(
                    idPelanggan=pelanggan,
                    alamatPengiriman=form.cleaned_data['alamatPengiriman'],
                    total=total_price,
                    buktiBayar=bukti_bayar,
                    status='Diproses'
                )
                
                # Create detail pemesanan for each item in cart
                for item in cart_items:
                    # Get produk
                    produk = Produk.objects.get(idProduk=item['id'])
                    
                    # Check stock availability
                    if item['quantity'] > produk.stok:
                        raise ValueError(f'Stok {produk.namaProduk} tidak mencukupi.')
                    
                    # Create detail pemesanan
                    DetailPemesanan.objects.create(
                        idPemesanan=pemesanan,
                        idProduk=produk,
                        jumlah=item['quantity'],
                        subTotal=item['subtotal']
                    )
                
                # Clear cart from session
                del request.session['cart']
                request.session.modified = True
                
                messages.success(request, 'Pesanan berhasil dibuat!')
                return redirect('riwayat_pesanan')
        else:
            messages.error(request, 'Terjadi kesalahan pada form. Silakan periksa kembali.')
    else:
        # Pre-fill address with pelanggan's address
        pelanggan_id = request.session['pelanggan_id']
        pelanggan = Pelanggan.objects.get(idPelanggan=pelanggan_id)
        form = PemesananCheckoutForm(initial={'alamatPengiriman': pelanggan.alamat})
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'total_items': total_items,
        'total_price': total_price,
    }
    
    return render(request, 'pelanggan/checkout.html', context)

@login_required(login_url='pelanggan_login')
def riwayat_pesanan(request):
    """View order history"""
    # Get pelanggan from session
    pelanggan_id = request.session['pelanggan_id']
    pelanggan = Pelanggan.objects.get(idPelanggan=pelanggan_id)
    
    # Get all orders for this pelanggan
    pesanan_list = Pemesanan.objects.filter(idPelanggan=pelanggan).order_by('-tanggalPemesanan')
    
    context = {
        'pesanan_list': pesanan_list,
    }
    
    return render(request, 'pelanggan/riwayat_pesanan.html', context)

@login_required(login_url='pelanggan_login')
def detail_pesanan(request, pk):
    """View order detail"""
    # Get pelanggan from session
    pelanggan_id = request.session['pelanggan_id']
    pelanggan = Pelanggan.objects.get(idPelanggan=pelanggan_id)
    
    try:
        # Get order that belongs to this pelanggan
        pesanan = Pemesanan.objects.get(idPemesanan=pk, idPelanggan=pelanggan)
    except Pemesanan.DoesNotExist:
        messages.error(request, 'Pesanan tidak ditemukan.')
        return redirect('riwayat_pesanan')
    
    # Get order details
    detail_list = DetailPemesanan.objects.filter(idPemesanan=pesanan)
    
    context = {
        'pesanan': pesanan,
        'detail_list': detail_list,
    }
    
    return render(request, 'pelanggan/detail_pesanan.html', context)

@login_required(login_url='pelanggan_login')
def pelanggan_account(request):
    """View and update pelanggan account"""
    # Get pelanggan from session
    pelanggan_id = request.session['pelanggan_id']
    pelanggan = Pelanggan.objects.get(idPelanggan=pelanggan_id)
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            # Update profile
            form = PelangganUpdateForm(request.POST, instance=pelanggan)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profil berhasil diperbarui.')
                return redirect('pelanggan_account')
            else:
                messages.error(request, 'Terjadi kesalahan pada form.')
        elif 'change_password' in request.POST:
            # Change password
            form = ChangePasswordForm(pelanggan, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Password berhasil diubah.')
                return redirect('pelanggan_account')
            else:
                messages.error(request, 'Terjadi kesalahan pada form.')
    else:
        form = PelangganUpdateForm(instance=pelanggan)
        password_form = ChangePasswordForm(pelanggan)
    
    context = {
        'pelanggan': pelanggan,
        'form': form,
        'password_form': ChangePasswordForm(pelanggan),
    }
    
    return render(request, 'pelanggan/akun.html', context)
