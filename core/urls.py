from django.urls import path
from . import views

urlpatterns = [
    path('laporan/pelanggan/', views.laporan_pelanggan, name='laporan-pelanggan'),
    path('laporan/produk/', views.laporan_produk, name='laporan-produk'),
    path('laporan/sopir-kendaraan/', views.laporan_sopir_kendaraan, name='laporan-sopir-kendaraan'),
    path('laporan/pemesanan-pendapatan/', views.laporan_pemesanan_pendapatan, name='laporan-pemesanan-pendapatan'),
    path('laporan/feedback/', views.laporan_feedback, name='laporan-feedback'),
]