from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageTemplate, Frame
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .models import Pelanggan, Sopir, Kendaraan, Produk, StokMasuk, Pemesanan, DetailPemesanan, Feedback

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
    # Get filter parameters
    filter_tipe = request.GET.get('filter_tipe')
    batas_stok = request.GET.get('batas_stok', 10)
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    
    # Build queryset
    produk_list = Produk.objects.all()
    
    # Prepare date filter dictionary
    date_filter = {}
    if tgl_mulai:
        date_filter['detailpemesanan__idPemesanan__tanggalPemesanan__date__gte'] = tgl_mulai
    if tgl_akhir:
        date_filter['detailpemesanan__idPemesanan__tanggalPemesanan__date__lte'] = tgl_akhir
    
    # Apply product filters
    if filter_tipe == 'terlaris':
        # Get best selling products
        produk_list = produk_list.annotate(
            total_terjual=Sum('detailpemesanan__jumlah', filter=Q(**date_filter) if date_filter else None)
        ).order_by('-total_terjual')
    elif filter_tipe == 'stok_menipis':
        # Get products with low stock
        produk_list = produk_list.filter(stok__lte=batas_stok)
    
    # Calculate total sold for each product
    produk_data = []
    for produk in produk_list:
        # Prepare date filter for individual product query
        product_date_filter = {}
        if tgl_mulai:
            product_date_filter['idPemesanan__tanggalPemesanan__date__gte'] = tgl_mulai
        if tgl_akhir:
            product_date_filter['idPemesanan__tanggalPemesanan__date__lte'] = tgl_akhir
            
        # Calculate total sold for this product
        total_terjual_queryset = DetailPemesanan.objects.filter(idProduk=produk)
        if product_date_filter:
            total_terjual_queryset = total_terjual_queryset.filter(**product_date_filter)
        total_terjual = total_terjual_queryset.aggregate(total=Sum('jumlah'))['total'] or 0
        
        produk_data.append({
            'namaProduk': produk.namaProduk,
            'ukuranKemasan': produk.ukuranKemasan,
            'hargaPerDus': format_rupiah(produk.hargaPerDus),
            'stok': produk.stok,
            'total_terjual': total_terjual
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
    table = Table(data, colWidths=[0.5*inch, 1.5*inch, 1.2*inch, 2*inch, 1*inch, 1.3*inch])
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, y_position - len(data) * 20)
    
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
    
    # Create a PDF buffer
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Get filter parameters
    filter_tipe = request.GET.get('filter_tipe')
    batas_stok = request.GET.get('batas_stok', 10)
    tgl_mulai = request.GET.get('tgl_mulai')
    tgl_akhir = request.GET.get('tgl_akhir')
    
    # Build queryset
    produk_list = Produk.objects.all()
    
    # Apply filters
    date_range = ""
    if tgl_mulai and tgl_akhir:
        date_range = f"{tgl_mulai} - {tgl_akhir}"
    
    # Prepare date filter dictionary
    date_filter = {}
    if tgl_mulai:
        date_filter['detailpemesanan__idPemesanan__tanggalPemesanan__date__gte'] = tgl_mulai
    if tgl_akhir:
        date_filter['detailpemesanan__idPemesanan__tanggalPemesanan__date__lte'] = tgl_akhir
    
    # Apply product filters
    if filter_tipe == 'terlaris':
        # Get best selling products
        produk_list = produk_list.annotate(
            total_terjual=Sum('detailpemesanan__jumlah', filter=Q(**date_filter) if date_filter else None)
        ).order_by('-total_terjual')
    elif filter_tipe == 'stok_menipis':
        # Get products with low stock
        produk_list = produk_list.filter(stok__lte=batas_stok)
    
    # Add header
    create_pdf_header(p, "Produk & Stok", date_range)
    
    # Prepare data for table
    data = [['No', 'Nama Produk', 'Ukuran', 'Harga', 'Stok', 'Terjual']]
    
    y_position = 700
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    
    for i, produk in enumerate(produk_list, 1):
        # Prepare date filter for individual product query
        product_date_filter = {}
        if tgl_mulai:
            product_date_filter['idPemesanan__tanggalPemesanan__date__gte'] = tgl_mulai
        if tgl_akhir:
            product_date_filter['idPemesanan__tanggalPemesanan__date__lte'] = tgl_akhir
            
        # Calculate total sold for this product
        total_terjual_queryset = DetailPemesanan.objects.filter(idProduk=produk)
        if product_date_filter:
            total_terjual_queryset = total_terjual_queryset.filter(**product_date_filter)
        total_terjual = total_terjual_queryset.aggregate(total=Sum('jumlah'))['total'] or 0
        
        row = [
            str(i),
            produk.namaProduk,
            produk.ukuranKemasan,
            format_rupiah(produk.hargaPerDus),
            str(produk.stok),
            str(total_terjual)
        ]
        data.append(row)
    
    # Create table with improved styling
    table = Table(data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 1*inch, 0.8*inch, 0.8*inch])
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, y_position - len(data) * 20)
    
    # Save PDF
    p.showPage()
    p.save()
    
    # Get the value of the BytesIO buffer and write it to the response
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
    table = Table(data, colWidths=[0.5*inch, 1.5*inch, 1.2*inch, 1*inch, 1.5*inch, 1*inch])
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, y_position - len(data) * 20)
    
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
    table = Table(data, colWidths=[0.5*inch, 1*inch, 1.5*inch, 2*inch, 1*inch, 1.5*inch])
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, y_position - len(data) * 20)
    
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
    table = Table(data, colWidths=[0.5*inch, 1*inch, 1.5*inch, 4.5*inch])
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, y_position - len(data) * 20)
    
    # Save PDF
    p.showPage()
    p.save()
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response