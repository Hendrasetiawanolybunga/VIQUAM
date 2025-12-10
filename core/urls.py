from django.urls import path
from . import views

urlpatterns = [
    path('laporan/pelanggan/', views.laporan_pelanggan, name='laporan-pelanggan'),
    path('laporan/produk/', views.laporan_produk, name='laporan-produk'),
    path('laporan/sopir-kendaraan/', views.laporan_sopir_kendaraan, name='laporan-sopir-kendaraan'),
    path('laporan/pemesanan-pendapatan/', views.laporan_pemesanan_pendapatan, name='laporan-pemesanan-pendapatan'),
    path('laporan/feedback/', views.laporan_feedback, name='laporan-feedback'),
    
    # Sopir URLs
    path('sopir/login/', views.sopir_login, name='sopir-login'),
    path('sopir/logout/', views.sopir_logout, name='sopir-logout'),
    path('sopir/dashboard/', views.sopir_dashboard, name='sopir-dashboard'),
    path('sopir/edit-pengiriman/<int:pk>/', views.sopir_edit_pengiriman, name='sopir-edit-pengiriman'),
    path('sopir/account/', views.sopir_account, name='sopir-account'),
    
    # Pelanggan URLs
    path('', views.landing_page, name='landing'),
    path('register/', views.pelanggan_register, name='pelanggan_register'),
    path('login/', views.pelanggan_login, name='pelanggan_login'),
    path('logout/', views.pelanggan_logout, name='pelanggan_logout'),
    path('home/', views.pelanggan_home, name='pelanggan_home'),
    path('produk/', views.list_produk, name='list_produk'),
    path('produk/<int:pk>/detail/', views.detail_produk, name='detail_produk'),
    path('keranjang/', views.view_keranjang, name='view_keranjang'),
    path('keranjang/add/<int:pk>/', views.tambah_ke_keranjang, name='tambah_ke_keranjang'),
    path('keranjang/update/<int:pk>/', views.update_keranjang, name='update_keranjang'),
    path('keranjang/remove/<int:pk>/', views.remove_from_keranjang, name='remove_from_keranjang'),
    path('checkout/', views.checkout_pemesanan, name='checkout_pemesanan'),
    path('riwayat/', views.riwayat_pesanan, name='riwayat_pesanan'),
    path('riwayat/<int:pk>/detail/', views.detail_pesanan, name='detail_pesanan'),
    path('akun/', views.pelanggan_account, name='pelanggan_account'),
]